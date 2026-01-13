/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/secret.h>
#include <sec/secure_aes.h>
#include <sys/bootutils.h>
#include <sys/mpu.h>
#include <sys/rng.h>
#include <util/flash.h>
#include <util/flash_utils.h>
#include <util/rsod_special.h>
#include "memzero.h"

#ifdef SECURE_MODE

#define SECRET_HEADER_MAGIC "TRZS"
#define SECRET_HEADER_MAGIC_LEN (sizeof(SECRET_HEADER_MAGIC) - 1)

#define SECRET_BHK_REG_OFFSET 0

#define SECRET_NUM_MAX_SLOTS 3

#ifndef SECRET_KEY_SLOT_0_OFFSET
#define SECRET_KEY_SLOT_0_OFFSET 0
#define SECRET_KEY_SLOT_0_LEN 0
#endif

#ifndef SECRET_KEY_SLOT_1_OFFSET
#define SECRET_KEY_SLOT_1_OFFSET 0
#define SECRET_KEY_SLOT_1_LEN 0
#endif

#ifndef SECRET_KEY_SLOT_2_OFFSET
#define SECRET_KEY_SLOT_2_OFFSET 0
#define SECRET_KEY_SLOT_2_LEN 0
#endif

#define SECRET_KEY_MAX_LEN (24 * sizeof(uint32_t))

_Static_assert(SECRET_NUM_MAX_SLOTS >= SECRET_NUM_KEY_SLOTS);
_Static_assert(SECRET_KEY_SLOT_0_LEN + SECRET_KEY_SLOT_1_LEN +
                       SECRET_KEY_SLOT_2_LEN <=
                   SECRET_KEY_MAX_LEN,
               "secret key slots too large");
_Static_assert(SECRET_KEY_SLOT_0_LEN % 16 == 0,
               "secret key length must be multiple of 16 bytes");
_Static_assert(SECRET_KEY_SLOT_1_LEN % 16 == 0,
               "secret key length must be multiple of 16 bytes");
_Static_assert(SECRET_KEY_SLOT_2_LEN % 16 == 0,
               "secret key length must be multiple of 16 bytes");

static uint32_t secret_slot_offsets[SECRET_NUM_MAX_SLOTS] = {
    SECRET_KEY_SLOT_0_OFFSET,
    SECRET_KEY_SLOT_1_OFFSET,
    SECRET_KEY_SLOT_2_OFFSET,
};

static uint32_t secret_slot_lengths[SECRET_NUM_MAX_SLOTS] = {
    SECRET_KEY_SLOT_0_LEN,
    SECRET_KEY_SLOT_1_LEN,
    SECRET_KEY_SLOT_2_LEN,
};

static secbool secret_slot_public[SECRET_NUM_MAX_SLOTS] = {
#ifdef SECRET_KEY_SLOT_0_PUBLIC
    sectrue,
#else
    secfalse,
#endif
#ifdef SECRET_KEY_SLOT_1_PUBLIC
    sectrue,
#else
    secfalse,
#endif
#ifdef SECRET_KEY_SLOT_2_PUBLIC
    sectrue,
#else
    secfalse,
#endif
};

static secbool secret_verify_header(void) {
  uint8_t *addr = (uint8_t *)flash_area_get_address(
      &SECRET_AREA, SECRET_HEADER_OFFSET, SECRET_HEADER_LEN);

  if (addr == NULL) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);

  secbool header_present =
      memcmp(addr, SECRET_HEADER_MAGIC, SECRET_HEADER_MAGIC_LEN) == 0
          ? sectrue
          : secfalse;

  mpu_restore(mpu_mode);

  return header_present;
}

static void secret_erase(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  ensure(flash_area_erase(&SECRET_AREA, NULL), "secret erase");
  mpu_restore(mpu_mode);
}

static void secret_write_header(void) {
  uint8_t header[SECRET_HEADER_LEN] = {0};
  memcpy(header, SECRET_HEADER_MAGIC, SECRET_HEADER_MAGIC_LEN);
  ensure(secret_write(header, SECRET_HEADER_OFFSET, SECRET_HEADER_LEN),
         "secret write header failed");
}

static secbool secret_ensure_initialized(void) {
  if (sectrue != secret_verify_header()) {
    secret_erase();
    secret_write_header();
    return secfalse;
  }
  return sectrue;
}

secbool secret_write(const uint8_t *data, uint32_t offset, uint32_t len) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  ensure(flash_unlock_write(), "secret write");
  for (int i = 0; i < len / 16; i++) {
    if (sectrue != flash_area_write_quadword(&SECRET_AREA, offset + (i * 16),
                                             (uint32_t *)&data[(i * 16)])) {
      ensure(flash_lock_write(), "secret write");
      mpu_restore(mpu_mode);
      return secfalse;
    }
  }
  ensure(flash_lock_write(), "secret write");
  mpu_restore(mpu_mode);
  return sectrue;
}

secbool secret_read(uint8_t *data, uint32_t offset, uint32_t len) {
  if (sectrue != secret_verify_header()) {
    return secfalse;
  }
  uint8_t *addr = (uint8_t *)flash_area_get_address(&SECRET_AREA, offset, len);

  if (addr == NULL) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  memcpy(data, addr, len);
  mpu_restore(mpu_mode);

  return sectrue;
}

static void secret_disable_access(void) {
  FLASH->SECHDPCR |= FLASH_SECHDPCR_HDP1_ACCDIS_Msk;
  FLASH->SECHDPCR |= FLASH_SECHDPCR_HDP2_ACCDIS_Msk;
}

// Locks the BHK register. Once locked, the BHK register can't be accessed by
// the software. BHK is made available to the SAES peripheral
static void secret_bhk_lock(void) {
  TAMP_S->SECCFGR = 8 << TAMP_SECCFGR_BKPRWSEC_Pos | TAMP_SECCFGR_BHKLOCK;
}

// Verifies that access to the register has been disabled
static secbool secret_bhk_locked(void) {
  return ((TAMP_S->SECCFGR & TAMP_SECCFGR_BHKLOCK) == TAMP_SECCFGR_BHKLOCK) *
         sectrue;
}

static secbool secret_is_slot_valid(uint8_t slot) {
  return ((slot < SECRET_NUM_KEY_SLOTS) && (secret_slot_offsets[slot] != 0)) *
         sectrue;
}

static uint32_t secret_get_slot_offset(uint8_t slot) {
  if (slot >= SECRET_NUM_KEY_SLOTS) {
    return 0;
  }
  return secret_slot_offsets[slot];
}

static uint32_t secret_get_slot_len(uint8_t slot) {
  if (slot >= SECRET_NUM_KEY_SLOTS) {
    return 0;
  }
  return secret_slot_lengths[slot];
}

static size_t secret_get_reg_offset(uint8_t slot) {
  // SECRET_BHK_LEN is in bytes; each reg is 32 bits = 4 bytes
  size_t cumulative = SECRET_BHK_LEN / sizeof(uint32_t);

  for (uint8_t i = 0; i < slot; i++) {
    if (sectrue == secret_is_slot_valid(i)) {
      cumulative += (secret_slot_lengths[i] / sizeof(uint32_t));
    }
  }

  return cumulative;
}

static secbool secret_record_present(uint32_t offset, uint32_t len) {
  uint8_t *secret =
      (uint8_t *)flash_area_get_address(&SECRET_AREA, offset, len);

  if (secret == NULL) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);

  int secret_empty_bytes = 0;

  for (int i = 0; i < len; i++) {
    // 0xFF being the default value of the flash memory (before any write)
    // 0x00 being the value of the flash memory after manual erase
    if (secret[i] == 0xFF || secret[i] == 0x00) {
      secret_empty_bytes++;
    }
  }

  mpu_restore(mpu_mode);

  return sectrue * (secret_empty_bytes != len);
}

static secbool secret_key_present(uint8_t slot) {
  if (sectrue != secret_is_slot_valid(slot)) {
    return secfalse;
  }

  uint32_t offset = secret_get_slot_offset(slot);
  uint32_t len = secret_get_slot_len(slot);

  return secret_record_present(offset, len);
}

secbool secret_key_writable(uint8_t slot) {
  if (sectrue != secret_is_slot_valid(slot)) {
    return secfalse;
  }

  uint32_t offset = secret_get_slot_offset(slot);
  uint32_t len = secret_get_slot_len(slot);

  const uint8_t *const secret =
      (uint8_t *)flash_area_get_address(&SECRET_AREA, offset, len);

  if (secret == NULL) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);

  int secret_empty_bytes = 0;

  for (int i = 0; i < len; i++) {
    // 0xFF being the default value of the flash memory (before any write)
    // 0x00 being the value of the flash memory after manual erase
    if (secret[i] == 0xFF) {
      secret_empty_bytes++;
    }
  }

  mpu_restore(mpu_mode);

  return sectrue * (secret_empty_bytes == len);
}

static void secret_key_cache(uint8_t slot) {
  uint32_t offset = secret_get_slot_offset(slot);
  uint32_t len = secret_get_slot_len(slot);
  size_t reg_offset = secret_get_reg_offset(slot);

  uint32_t secret[SECRET_KEY_MAX_LEN] = {0};

  secbool ok = secret_read((uint8_t *)secret, offset, len);

  volatile uint32_t *reg = &TAMP->BKP0R;
  reg += reg_offset;
  if (sectrue == ok) {
    for (int i = 0; i < (len / sizeof(uint32_t)); i++) {
      *reg = secret[i];
      reg++;
    }
  } else {
    for (int i = 0; i < (len / sizeof(uint32_t)); i++) {
      *reg = 0;
      reg++;
    }
  }
  memzero(secret, sizeof(secret));
}

secbool secret_key_set(uint8_t slot, const uint8_t *key, size_t len) {
  if (sectrue != secret_is_slot_valid(slot)) {
    return secfalse;
  }

  uint32_t offset = secret_get_slot_offset(slot);
  uint32_t slot_len = secret_get_slot_len(slot);

  if (slot_len != len) {
    return secfalse;
  }

  uint8_t secret_enc[SECRET_KEY_MAX_LEN] = {0};
  if (sectrue !=
      secure_aes_ecb_encrypt_hw(key, len, secret_enc, SECURE_AES_KEY_DHUK_SP)) {
    return secfalse;
  }
  if (sectrue != secret_write(secret_enc, offset, len)) {
    memzero(secret_enc, sizeof(secret_enc));
    return secfalse;
  }
  memzero(secret_enc, sizeof(secret_enc));
  secret_key_cache(slot);
  return sectrue;
}

secbool secret_key_get(uint8_t slot, uint8_t *dest, size_t len) {
  if (sectrue != secret_is_slot_valid(slot)) {
    return secfalse;
  }

  uint32_t slot_len = secret_get_slot_len(slot);
  size_t reg_offset = secret_get_reg_offset(slot);

  if (slot_len != len) {
    return secfalse;
  }

  uint32_t secret[SECRET_KEY_MAX_LEN] = {0};

  bool all_zero = true;
  volatile uint32_t *reg = &TAMP->BKP0R;
  for (int i = 0; i < (len / sizeof(uint32_t)); i++) {
    secret[i] = reg[i + reg_offset];

    if (secret[i] != 0) {
      all_zero = false;
    }
  }

  if (all_zero) {
    return secfalse;
  }

  secbool res = secure_aes_ecb_decrypt_hw((uint8_t *)secret, len, dest,
                                          SECURE_AES_KEY_DHUK_SP);

  memzero(secret, sizeof(secret));
  return res;
}

// Deletes the secret from the register
__attribute__((unused)) static void secret_key_uncache(uint8_t slot) {
  size_t reg_offset = secret_get_reg_offset(slot);
  uint32_t slot_len = secret_get_slot_len(slot);

  volatile uint32_t *reg = &TAMP->BKP0R;
  for (int i = 0; i < slot_len / sizeof(uint32_t); i++) {
    reg[i + reg_offset] = 0;
  }
}

static void secret_key_erase(uint8_t slot) {
  uint8_t value[SECRET_KEY_MAX_LEN] = {0};

  uint32_t offset = secret_get_slot_offset(slot);
  uint32_t slot_len = secret_get_slot_len(slot);

  ensure(secret_write(value, offset, slot_len), "secret erase failed");
}

// Provision the secret BHK from the secret storage to the BHK register
// which makes the BHK usable for encryption by the firmware, without having
// read access to it.
static void secret_bhk_load(void) {
  if (sectrue == secret_bhk_locked()) {
    reboot_device();
  }

  uint32_t secret[SECRET_BHK_LEN / sizeof(uint32_t)] = {0};

  if (sectrue != secret_record_present(SECRET_BHK_OFFSET, SECRET_BHK_LEN)) {
    secret_bhk_regenerate();
  }

  secbool ok =
      secret_read((uint8_t *)secret, SECRET_BHK_OFFSET, SECRET_BHK_LEN);

  volatile uint32_t *reg1 = &TAMP->BKP0R;
  if (sectrue == ok) {
    for (int i = 0; i < (SECRET_BHK_LEN / sizeof(uint32_t)); i++) {
      *reg1 = ((uint32_t *)secret)[i];
      reg1++;
    }
  } else {
    for (int i = 0; i < (SECRET_BHK_LEN / sizeof(uint32_t)); i++) {
      *reg1 = 0;
      reg1++;
    }
  }

  memzero(secret, sizeof(secret));
}

void secret_bhk_regenerate(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);

  ensure(flash_area_erase(&BHK_AREA, NULL), "Failed regenerating BHK");
  ensure(flash_unlock_write(), "Failed regenerating BHK");
  for (int i = 0; i < 2; i++) {
    uint32_t val[4] = {0};
    for (int j = 0; j < 4; j++) {
      val[j] = rng_get();
    }
    secbool res =
        flash_area_write_quadword(&BHK_AREA, i * 4 * sizeof(uint32_t), val);
    memzero(val, sizeof(val));
    ensure(res, "Failed regenerating BHK");
  }

  mpu_restore(mpu_mode);

  ensure(flash_lock_write(), "Failed regenerating BHK");
}

static void secret_keys_uncache(void) {
  for (uint8_t i = 0; i < SECRET_NUM_KEY_SLOTS; i++) {
    if (sectrue == secret_is_slot_valid(i)) {
      secret_key_uncache(i);
    }
  }
}

static void secret_keys_cache(void) {
  for (uint8_t i = 0; i < SECRET_NUM_KEY_SLOTS; i++) {
    if (sectrue == secret_is_slot_valid(i) &&
        sectrue == secret_key_present(i)) {
      secret_key_cache(i);
    }
  }
}

static void secret_keys_cache_public(void) {
  for (uint8_t i = 0; i < SECRET_NUM_KEY_SLOTS; i++) {
    if ((sectrue == secret_is_slot_valid(i)) &&
        (sectrue == secret_key_present(i)) &&
        (sectrue == secret_slot_public[i])) {
      secret_key_cache(i);
    }
  }
}

// return sectrue if all the key slots are valid and contain a key
static secbool secret_keys_present(void) {
  secbool result = sectrue;

  for (uint8_t i = 0; i < SECRET_NUM_KEY_SLOTS; i++) {
    if (sectrue == secret_is_slot_valid(i)) {
      result = secbool_and(result, secret_key_present(i));
    }
  }

  return result;
}

#if defined BOOTLOADER || defined BOARDLOADER
// return sectrue if any non-public key slot is valid and contains a key
static secbool secret_keys_present_any(void) {
  secbool result = secfalse;

  for (uint8_t i = 0; i < SECRET_NUM_KEY_SLOTS; i++) {
    if (sectrue == secret_is_slot_valid(i) &&
        sectrue != secret_slot_public[i]) {
      result = secbool_or(result, secret_key_present(i));
    }
  }

  return result;
}
#endif

// return sectrue if at least one key slot is writable
__attribute__((unused)) static secbool secret_keys_writable(void) {
  secbool result = secfalse;

  for (uint8_t i = 0; i < SECRET_NUM_KEY_SLOTS; i++) {
    if (sectrue == secret_is_slot_valid(i)) {
      result = secbool_or(result, secret_key_writable(i));
    }
  }

  return result;
}

#ifdef LOCKABLE_BOOTLOADER
secbool secret_bootloader_locked(void) {
#if defined BOOTLOADER || defined BOARDLOADER
  return secret_keys_present_any();
#else
  // in firmware, we determine bootloader state by checking if bootloader
  //  has provided any non-public key
  for (int i = 0; i < SECRET_NUM_KEY_SLOTS; i++) {
    uint32_t val[SECRET_KEY_MAX_LEN] = {0};
    size_t len = secret_get_slot_len(i);
    if (secfalse == secret_slot_public[i] &&
        sectrue == secret_key_get(i, (uint8_t *)val, len)) {
      memzero(val, sizeof(val));
      return sectrue;
    }
  }
  return secfalse;
#endif
}

void secret_unlock_bootloader(void) {
  for (uint8_t i = 0; i < SECRET_NUM_KEY_SLOTS; i++) {
    if (sectrue == secret_is_slot_valid(i) &&
        sectrue != secret_slot_public[i]) {
      secret_key_erase(i);
    }
  }
}

#endif

#ifdef SECRET_LOCK_SLOT_OFFSET

secbool secret_lock(void) {
  uint8_t lock_data[SECRET_LOCK_SLOT_LEN] = {0};
  secbool result =
      secret_write(lock_data, SECRET_LOCK_SLOT_OFFSET, sizeof(lock_data));

  if (sectrue == result) {
    secret_disable_access();
  }

  return result;
}

secbool secret_is_locked(void) {
  uint8_t *header_data =
      (uint8_t *)flash_area_get_address(&SECRET_AREA, 0, SECRET_HEADER_LEN);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  uint16_t zero_count = 0;
  for (int i = 0; i < SECRET_HEADER_LEN; i++) {
    // 0 is returned when the secret sector is inaccessible
    if (header_data[i] == 0) {
      zero_count++;
    }
  }
  mpu_restore(mpu_mode);

  if (zero_count == SECRET_HEADER_LEN) {
    return sectrue;
  }

  uint8_t lock_data[SECRET_LOCK_SLOT_LEN] = {0};
  secret_read(lock_data, SECRET_LOCK_SLOT_OFFSET, SECRET_LOCK_SLOT_LEN);

  for (int i = 0; i < SECRET_LOCK_SLOT_LEN; i++) {
    // 0xFF being the default value of the flash memory (before any write)
    if (lock_data[i] != 0xFF) {
      return sectrue;
    }
  }

  return secfalse;
}
#endif

void secret_prepare_fw(secbool allow_run_with_secret,
                       secbool allow_provisioning_access) {
  /**
   * The BHK is copied to the backup registers, which are accessible by the SAES
   * peripheral. The BHK register is locked, so the BHK can't be accessed by the
   * software.
   *
   * When optiga is paired, pairing secret is copied to the backup registers
   * and access to the secret storage is disabled. Otherwise, access to the
   * secret storage kept to allow optiga pairing in prodtest.
   *
   * Access to the secret storage is disabled for non-official firmware in
   * all-cases.
   */

  if (sectrue != allow_run_with_secret &&
      secfalse != secret_bootloader_locked()) {
    // Untrusted firmware, locked bootloader. Show the restricted screen.
    show_install_restricted_screen();
  }

  secret_bhk_load();
  secret_bhk_lock();
  secret_keys_uncache();
  secbool secret_present = secret_keys_present();

#ifdef SECRET_LOCK_SLOT_OFFSET
  secbool secret_locked = secret_is_locked();
#else
  // Without the lock record, we determine the lock status by the presence of
  // keys. When none of the keys is writable, or all keys are present, it means
  // the sector is locked.
  secbool secret_writable = secret_keys_writable();
  secbool secret_locked =
      secbool_or(secbool_not(secret_writable), secret_present);
#endif

  if (sectrue == allow_provisioning_access && secfalse == secret_locked) {
    // U5 chip is unprovisioned.
    // Allow trusted firmware (prodtest presumably) to access the secret sector,
    // early return here.
    secret_keys_cache();
    return;
  }
  if (sectrue == allow_run_with_secret && sectrue == secret_present) {
    // Firmware is trusted, and the secret keys are present, make it available.
    secret_keys_cache();
  } else {
    // Make only public keys available.
    secret_keys_cache_public();
  }
  // Disable access unconditionally.
  secret_disable_access();
}

void secret_init(void) { secret_ensure_initialized(); }

void secret_safety_erase(void) {
  secret_init();
  secret_bhk_regenerate();
}

#endif  // SECURE_MODE
