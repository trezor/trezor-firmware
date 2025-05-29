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

#include <sec/rng.h>
#include <sec/secret.h>
#include <sec/secure_aes.h>
#include <sys/bootutils.h>
#include <sys/mpu.h>
#include <util/flash.h>
#include <util/flash_utils.h>
#include "memzero.h"

#ifdef SECURE_MODE

#define REG_BHK_OFFSET 0
#define REG_OPTIGA_KEY_OFFSET 8
#define REG_TROPIC_TRZ_PRIVKEY_OFFSET 16
#define REG_TROPIC_TRO_PUBKEY_OFFSET 24

secbool secret_verify_header(void) {
  uint8_t *addr = (uint8_t *)flash_area_get_address(
      &SECRET_AREA, 0, sizeof(SECRET_HEADER_MAGIC));

  if (addr == NULL) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);

  secbool header_present =
      memcmp(addr, SECRET_HEADER_MAGIC, sizeof(SECRET_HEADER_MAGIC)) == 0
          ? sectrue
          : secfalse;

  mpu_restore(mpu_mode);

  return header_present;
}

static secbool secret_ensure_initialized(void) {
  if (sectrue != secret_verify_header()) {
    ensure(erase_storage(NULL), "erase storage failed");
    secret_erase();
    secret_write_header();
    return secfalse;
  }
  return sectrue;
}

void secret_write_header(void) {
  uint8_t header[SECRET_HEADER_LEN] = {0};
  memcpy(header, SECRET_HEADER_MAGIC, 4);
  secret_write(header, 0, SECRET_HEADER_LEN);
}

void secret_write(const uint8_t *data, uint32_t offset, uint32_t len) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  ensure(flash_unlock_write(), "secret write");
  for (int i = 0; i < len / 16; i++) {
    ensure(flash_area_write_quadword(&SECRET_AREA, offset + (i * 16),
                                     (uint32_t *)&data[(i * 16)]),
           "secret write");
  }
  ensure(flash_lock_write(), "secret write");
  mpu_restore(mpu_mode);
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

static secbool secret_key_present(uint32_t offset) {
  uint8_t *secret =
      (uint8_t *)flash_area_get_address(&SECRET_AREA, offset, SECRET_KEY_LEN);

  if (secret == NULL) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);

  int secret_empty_bytes = 0;

  for (int i = 0; i < SECRET_KEY_LEN; i++) {
    // 0xFF being the default value of the flash memory (before any write)
    // 0x00 being the value of the flash memory after manual erase
    if (secret[i] == 0xFF || secret[i] == 0x00) {
      secret_empty_bytes++;
    }
  }

  mpu_restore(mpu_mode);

  return sectrue * (secret_empty_bytes != SECRET_KEY_LEN);
}

__attribute__((unused)) static secbool secret_key_writable(uint32_t offset) {
  const uint8_t *const secret =
      (uint8_t *)flash_area_get_address(&SECRET_AREA, offset, SECRET_KEY_LEN);

  if (secret == NULL) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);

  int secret_empty_bytes = 0;

  for (int i = 0; i < SECRET_KEY_LEN; i++) {
    // 0xFF being the default value of the flash memory (before any write)
    // 0x00 being the value of the flash memory after manual erase
    if (secret[i] == 0xFF) {
      secret_empty_bytes++;
    }
  }

  mpu_restore(mpu_mode);

  return sectrue * (secret_empty_bytes == SECRET_KEY_LEN);
}

__attribute__((unused)) static void secret_key_cache(uint8_t reg_offset,
                                                     uint32_t key_offset) {
  uint32_t secret[SECRET_KEY_LEN / sizeof(uint32_t)] = {0};

  secbool ok = secret_read((uint8_t *)secret, key_offset, SECRET_KEY_LEN);

  volatile uint32_t *reg = &TAMP->BKP0R;
  reg += reg_offset;
  if (sectrue == ok) {
    for (int i = 0; i < (SECRET_KEY_LEN / sizeof(uint32_t)); i++) {
      *reg = ((uint32_t *)secret)[i];
      reg++;
    }
  } else {
    for (int i = 0; i < (SECRET_KEY_LEN / sizeof(uint32_t)); i++) {
      *reg = 0;
      reg++;
    }
  }
  memzero(secret, sizeof(secret));
}

__attribute__((unused)) static secbool secret_key_set(
    const uint8_t secret[SECRET_KEY_LEN], uint8_t reg_offset,
    uint32_t key_offset) {
  uint8_t secret_enc[SECRET_KEY_LEN] = {0};
  if (sectrue != secure_aes_ecb_encrypt_hw(secret, sizeof(secret_enc),
                                           secret_enc,
                                           SECURE_AES_KEY_DHUK_SP)) {
    return secfalse;
  }
  secret_write(secret_enc, key_offset, SECRET_KEY_LEN);
  memzero(secret_enc, sizeof(secret_enc));
  secret_key_cache(reg_offset, key_offset);
  return sectrue;
}

__attribute__((unused)) static secbool secret_key_get(
    uint8_t dest[SECRET_KEY_LEN], uint8_t reg_offset) {
  uint32_t secret[SECRET_KEY_LEN / sizeof(uint32_t)] = {0};

  bool all_zero = true;
  volatile uint32_t *reg = &TAMP->BKP0R;
  for (int i = 0; i < (SECRET_KEY_LEN / sizeof(uint32_t)); i++) {
    secret[i] = reg[i + reg_offset];

    if (secret[i] != 0) {
      all_zero = false;
    }
  }

  if (all_zero) {
    return secfalse;
  }

  secbool res = secure_aes_ecb_decrypt_hw((uint8_t *)secret, SECRET_KEY_LEN,
                                          dest, SECURE_AES_KEY_DHUK_SP);

  memzero(secret, sizeof(secret));
  return res;
}

// Deletes the secret from the register
__attribute__((unused)) static void secret_key_uncache(uint8_t reg_offset) {
  volatile uint32_t *reg = &TAMP->BKP0R;
  for (int i = 0; i < 8; i++) {
    reg[i + reg_offset] = 0;
  }
}

// Provision the secret BHK from the secret storage to the BHK register
// which makes the BHK usable for encryption by the firmware, without having
// read access to it.
static void secret_bhk_load(void) {
  if (sectrue == secret_bhk_locked()) {
    reboot_device();
  }

  uint32_t secret[SECRET_KEY_LEN / sizeof(uint32_t)] = {0};

  if (sectrue != secret_key_present(SECRET_BHK_OFFSET)) {
    secret_bhk_regenerate();
  }

  secbool ok =
      secret_read((uint8_t *)secret, SECRET_BHK_OFFSET, SECRET_KEY_LEN);

  volatile uint32_t *reg1 = &TAMP->BKP0R;
  if (sectrue == ok) {
    for (int i = 0; i < (SECRET_KEY_LEN / sizeof(uint32_t)); i++) {
      *reg1 = ((uint32_t *)secret)[i];
      reg1++;
    }
  } else {
    for (int i = 0; i < (SECRET_KEY_LEN / sizeof(uint32_t)); i++) {
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

#ifdef USE_OPTIGA
// Checks that the optiga pairing secret is present in the secret storage.
// This functions only works when software has access to the secret storage,
// i.e. in bootloader. Access to secret storage is restricted by calling
// secret_hide.
secbool secret_optiga_present(void) {
  return secret_key_present(SECRET_OPTIGA_KEY_OFFSET);
}

secbool secret_optiga_writable(void) {
  return secret_key_writable(SECRET_OPTIGA_KEY_OFFSET);
}

secbool secret_optiga_set(const uint8_t secret[SECRET_KEY_LEN]) {
  return secret_key_set(secret, REG_OPTIGA_KEY_OFFSET,
                        SECRET_OPTIGA_KEY_OFFSET);
}

secbool secret_optiga_get(uint8_t dest[SECRET_KEY_LEN]) {
  return secret_key_get(dest, REG_OPTIGA_KEY_OFFSET);
}

// Backs up the optiga pairing secret from the secret storage to the backup
// register
static void secret_optiga_cache(void) {
  if (sectrue == secret_optiga_present()) {
    secret_key_cache(REG_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_OFFSET);
  }
}

// Deletes the optiga pairing secret from the register
static void secret_optiga_uncache(void) { secret_key_uncache(8); }

static void secret_optiga_erase(void) {
  uint8_t value[SECRET_KEY_LEN] = {0};
  secret_write(value, SECRET_OPTIGA_KEY_OFFSET, SECRET_KEY_LEN);
}

#endif

#ifdef USE_TROPIC
secbool secret_tropic_get_trezor_privkey(uint8_t dest[SECRET_KEY_LEN]) {
  return secret_key_get(dest, REG_TROPIC_TRZ_PRIVKEY_OFFSET);
}

secbool secret_tropic_get_tropic_pubkey(uint8_t dest[SECRET_KEY_LEN]) {
  return secret_key_get(dest, REG_TROPIC_TRO_PUBKEY_OFFSET);
}

secbool secret_tropic_set(const uint8_t privkey[SECRET_KEY_LEN],
                          const uint8_t pubkey[SECRET_KEY_LEN]) {
  secbool res1 = secret_key_set(privkey, REG_TROPIC_TRZ_PRIVKEY_OFFSET,
                                SECRET_TROPIC_TRZ_PRIVKEY_OFFSET);

  if (sectrue != res1) {
    return secfalse;
  }

  secbool res2 = secret_key_set(pubkey, REG_TROPIC_TRO_PUBKEY_OFFSET,
                                SECRET_TROPIC_TRO_PUBKEY_OFFSET);

  return res2;
}

secbool secret_tropic_present(void) {
  secbool res1 = secret_key_present(SECRET_TROPIC_TRZ_PRIVKEY_OFFSET);

  secbool res2 = secret_key_present(SECRET_TROPIC_TRO_PUBKEY_OFFSET);

  return secbool_and(res1, res2);
}

secbool secret_tropic_present_any(void) {
  secbool res1 = secret_key_present(SECRET_TROPIC_TRZ_PRIVKEY_OFFSET);

  secbool res2 = secret_key_present(SECRET_TROPIC_TRO_PUBKEY_OFFSET);

  return secbool_or(res1, res2);
}

secbool secret_tropic_writable(void) {
  secbool res1 = secret_key_writable(SECRET_TROPIC_TRZ_PRIVKEY_OFFSET);

  secbool res2 = secret_key_writable(SECRET_TROPIC_TRO_PUBKEY_OFFSET);

  return secbool_or(res1, res2);
}

static void secret_tropic_erase(void) {
  uint8_t value[SECRET_KEY_LEN] = {0};
  secret_write(value, SECRET_TROPIC_TRZ_PRIVKEY_OFFSET, SECRET_KEY_LEN);
  secret_write(value, SECRET_TROPIC_TRO_PUBKEY_OFFSET, SECRET_KEY_LEN);
}

// Backs up the tropic pairing secret from the secret storage to the backup
// register
static void secret_tropic_cache(void) {
  if (sectrue == secret_tropic_present()) {
    secret_key_cache(REG_TROPIC_TRZ_PRIVKEY_OFFSET,
                     SECRET_TROPIC_TRZ_PRIVKEY_OFFSET);
    secret_key_cache(REG_TROPIC_TRO_PUBKEY_OFFSET,
                     SECRET_TROPIC_TRO_PUBKEY_OFFSET);
  }
}

// Deletes the tropic pairing secret from the register
static void secret_tropic_uncache(void) {
  secret_key_uncache(REG_TROPIC_TRZ_PRIVKEY_OFFSET);
  secret_key_uncache(REG_TROPIC_TRO_PUBKEY_OFFSET);
}

#endif

void secret_erase(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  ensure(flash_area_erase(&SECRET_AREA, NULL), "secret erase");
  mpu_restore(mpu_mode);
}

static void secret_se_uncache(void) {
#ifdef USE_OPTIGA
  secret_optiga_uncache();
#endif
#ifdef USE_TROPIC
  secret_tropic_uncache();
#endif
}

static void secret_se_cache(void) {
#ifdef USE_OPTIGA
  secret_optiga_cache();
#endif
#ifdef USE_TROPIC
  secret_tropic_cache();
#endif
}

static secbool secret_se_present(void) {
#ifdef USE_OPTIGA
  secbool res1 = secret_optiga_present();
#else
  secbool res1 = sectrue;
#endif

#ifdef USE_TROPIC
  secbool res2 = secret_tropic_present();
#else
  secbool res2 = sectrue;
#endif

  return secbool_and(res1, res2);
}

__attribute__((unused)) static secbool secret_se_present_any(void) {
#ifdef USE_OPTIGA
  secbool res1 = secret_optiga_present();
#else
  secbool res1 = secfalse;
#endif

#ifdef USE_TROPIC
  secbool res2 = secret_tropic_present_any();
#else
  secbool res2 = secfalse;
#endif

  return secbool_or(res1, res2);
}

static secbool secret_se_writable(void) {
#ifdef USE_OPTIGA
  secbool res1 = secret_optiga_writable();
#else
  secbool res1 = secfalse;
#endif

#ifdef USE_TROPIC
  secbool res2 = secret_tropic_writable();
#else
  secbool res2 = secfalse;
#endif

  return secbool_or(res1, res2);
}

#ifdef LOCKABLE_BOOTLOADER
secbool secret_bootloader_locked(void) {
#if defined BOOTLOADER || defined BOARDLOADER
  return secret_se_present_any();
#else
  const volatile uint32_t *reg1 = &TAMP->BKP8R;
  for (int i = 0; i < 24; i++) {
    if (reg1[i] != 0) {
      return sectrue;
    }
  }
  return secfalse;
#endif
}

void secret_unlock_bootloader(void) {
#ifdef USE_OPTIGA
  secret_optiga_erase();
#endif
#ifdef USE_TROPIC
  secret_tropic_erase();
#endif
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

  secret_bhk_load();
  secret_bhk_lock();
  secret_se_uncache();
  secbool se_secret_present = secret_se_present();
  secbool se_secret_writable = secret_se_writable();
  if (sectrue == allow_provisioning_access && sectrue == se_secret_writable &&
      secfalse == se_secret_present) {
    // SE Secret is not present and the secret sector is writable.
    // This means the U5 chip is unprovisioned.
    // Allow trusted firmware (prodtest presumably) to access the secret sector,
    // early return here.
    return;
  }
  if (sectrue == allow_run_with_secret && sectrue == se_secret_present) {
    // Firmware is trusted, and the SE secret is present, make it available.
    secret_se_cache();
  }
  // Disable access unconditionally.
  secret_disable_access();
  if (sectrue != allow_run_with_secret && sectrue == se_secret_present) {
    // Untrusted firmware, locked bootloader. Show the restricted screen.
    show_install_restricted_screen();
  }
}

void secret_init(void) {
  if (secret_bhk_locked() == sectrue) {
    reboot_device();
  }

  secret_ensure_initialized();
}

#endif  // SECURE_MODE
