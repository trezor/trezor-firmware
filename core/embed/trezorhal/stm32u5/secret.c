#include "secret.h"
#include <stdbool.h>
#include <string.h>
#include "common.h"
#include "flash.h"
#include "memzero.h"
#include "model.h"
#include "rng.h"
#include "secure_aes.h"

static secbool bootloader_locked = secfalse;

secbool secret_verify_header(void) {
  uint8_t *addr = (uint8_t *)flash_area_get_address(
      &SECRET_AREA, 0, sizeof(SECRET_HEADER_MAGIC));

  if (addr == NULL) {
    return secfalse;
  }

  bootloader_locked =
      memcmp(addr, SECRET_HEADER_MAGIC, sizeof(SECRET_HEADER_MAGIC)) == 0
          ? sectrue
          : secfalse;
  return bootloader_locked;
}

secbool secret_ensure_initialized(void) {
  if (sectrue != secret_verify_header()) {
    ensure(flash_area_erase_bulk(STORAGE_AREAS, STORAGE_AREAS_COUNT, NULL),
           "erase storage failed");
    secret_erase();
    secret_write_header();
    return secfalse;
  }
  return sectrue;
}

secbool secret_bootloader_locked(void) {
#ifdef FIRMWARE
  return (TAMP->BKP8R != 0) * sectrue;
#else
  return sectrue;
#endif
}

void secret_write_header(void) {
  uint8_t header[SECRET_HEADER_LEN] = {0};
  memcpy(header, SECRET_HEADER_MAGIC, 4);
  secret_write(header, 0, SECRET_HEADER_LEN);
}

void secret_write(const uint8_t *data, uint32_t offset, uint32_t len) {
  ensure(flash_unlock_write(), "secret write");
  for (int i = 0; i < len / 16; i++) {
    ensure(flash_area_write_quadword(&SECRET_AREA, offset + (i * 16),
                                     (uint32_t *)&data[(i * 16)]),
           "secret write");
  }
  ensure(flash_lock_write(), "secret write");
}

secbool secret_read(uint8_t *data, uint32_t offset, uint32_t len) {
  if (sectrue != secret_verify_header()) {
    return secfalse;
  }
  uint8_t *addr = (uint8_t *)flash_area_get_address(&SECRET_AREA, offset, len);

  if (addr == NULL) {
    return secfalse;
  }
  memcpy(data, addr, len);

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

static secbool secret_present(uint32_t offset, uint32_t len) {
  uint8_t *secret =
      (uint8_t *)flash_area_get_address(&SECRET_AREA, offset, len);

  if (secret == NULL) {
    return secfalse;
  }

  int secret_empty_bytes = 0;

  for (int i = 0; i < len; i++) {
    if (secret[i] == 0xFF) {
      secret_empty_bytes++;
    }
  }
  return sectrue * (secret_empty_bytes != len);
}

// Provision the secret BHK from the secret storage to the BHK register
// which makes the BHK usable for encryption by the firmware, without having
// read access to it.
static void secret_bhk_load(void) {
  if (sectrue == secret_bhk_locked()) {
    delete_secrets();
    NVIC_SystemReset();
  }

  uint32_t secret[SECRET_BHK_LEN / sizeof(uint32_t)] = {0};

  if (sectrue != secret_present(SECRET_BHK_OFFSET, SECRET_BHK_LEN)) {
    secret_bhk_regenerate();
  }

  secbool ok =
      secret_read((uint8_t *)secret, SECRET_BHK_OFFSET, SECRET_BHK_LEN);

  volatile uint32_t *reg1 = &TAMP->BKP0R;
  if (sectrue == ok) {
    for (int i = 0; i < 8; i++) {
      *reg1 = ((uint32_t *)secret)[i];
      reg1++;
    }
  } else {
    for (int i = 0; i < 8; i++) {
      *reg1 = 0;
      reg1++;
    }
  }

  memzero(secret, sizeof(secret));
}

void secret_bhk_regenerate(void) {
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
  ensure(flash_lock_write(), "Failed regenerating BHK");
}

#ifdef USE_OPTIGA
// Checks that the optiga pairing secret is present in the secret storage.
// This functions only works when software has access to the secret storage,
// i.e. in bootloader. Access to secret storage is restricted by calling
// secret_hide.
static secbool secret_optiga_present(void) {
  return secret_present(SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN);
}

// Backs up the optiga pairing secret from the secret storage to the backup
// register
static void secret_optiga_cache(void) {
  uint32_t secret[SECRET_OPTIGA_KEY_LEN / sizeof(uint32_t)] = {0};
  secbool ok = secret_read((uint8_t *)secret, SECRET_OPTIGA_KEY_OFFSET,
                           SECRET_OPTIGA_KEY_LEN);

  volatile uint32_t *reg1 = &TAMP->BKP8R;
  if (sectrue == ok) {
    for (int i = 0; i < 8; i++) {
      *reg1 = ((uint32_t *)secret)[i];
      reg1++;
    }
  } else {
    for (int i = 0; i < 8; i++) {
      *reg1 = 0;
      reg1++;
    }
  }
  memzero(secret, sizeof(secret));
}

secbool secret_optiga_set(const uint8_t secret[SECRET_OPTIGA_KEY_LEN]) {
  uint8_t secret_enc[SECRET_OPTIGA_KEY_LEN] = {0};
  if (sectrue != secure_aes_ecb_encrypt_hw(secret, sizeof(secret_enc),
                                           secret_enc, SECURE_AES_KEY_DHUK)) {
    return secfalse;
  }
  secret_write(secret_enc, SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN);
  memzero(secret_enc, sizeof(secret_enc));
  secret_optiga_cache();
  return sectrue;
}

secbool secret_optiga_get(uint8_t dest[SECRET_OPTIGA_KEY_LEN]) {
  uint32_t secret[SECRET_OPTIGA_KEY_LEN / sizeof(uint32_t)] = {0};

  bool all_zero = true;
  volatile uint32_t *reg1 = &TAMP->BKP8R;
  for (int i = 0; i < 8; i++) {
    secret[i] = reg1[i];

    if (secret[i] != 0) {
      all_zero = false;
    }
  }

  if (all_zero) {
    return secfalse;
  }

  secbool res = secure_aes_ecb_decrypt_hw(
      (uint8_t *)secret, SECRET_OPTIGA_KEY_LEN, dest, SECURE_AES_KEY_DHUK);

  memzero(secret, sizeof(secret));
  return res;
}

// Deletes the optiga pairing secret from the register
static void secret_optiga_uncache(void) {
  volatile uint32_t *reg1 = &TAMP->BKP8R;
  for (int i = 0; i < 8; i++) {
    reg1[i] = 0;
  }
}
#endif

void secret_erase(void) {
  ensure(flash_area_erase(&SECRET_AREA, NULL), "secret erase");
}

void secret_prepare_fw(secbool allow_run_with_secret, secbool trust_all) {
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
#ifdef USE_OPTIGA
  secret_optiga_uncache();
  if (sectrue == allow_run_with_secret) {
    if (secfalse != secret_optiga_present()) {
      secret_optiga_cache();
      secret_disable_access();
    }
  } else {
    secret_disable_access();
  }
#else
  secret_disable_access();
#endif

  if (sectrue != trust_all) {
    secret_disable_access();
  }
}
