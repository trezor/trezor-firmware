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
  uint8_t header[sizeof(SECRET_HEADER_MAGIC)] = {0};

  memcpy(header,
         flash_area_get_address(&SECRET_AREA, 0, sizeof(SECRET_HEADER_MAGIC)),
         sizeof(SECRET_HEADER_MAGIC));

  bootloader_locked =
      memcmp(header, SECRET_HEADER_MAGIC, sizeof(SECRET_HEADER_MAGIC)) == 0
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
  return TAMP->BKP8R != 0 * sectrue;
#else
  return sectrue;
#endif
}

void secret_write_header(void) {
  uint8_t header[SECRET_HEADER_LEN] = {0};
  memcpy(header, SECRET_HEADER_MAGIC, 4);
  secret_write(header, 0, SECRET_HEADER_LEN);
}

void secret_write(uint8_t *data, uint32_t offset, uint32_t len) {
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

  memcpy(data, flash_area_get_address(&SECRET_AREA, offset, len), len);

  return sectrue;
}

void secret_hide(void) {
  FLASH->SECHDPCR |= FLASH_SECHDPCR_HDP1_ACCDIS_Msk;
  FLASH->SECHDPCR |= FLASH_SECHDPCR_HDP2_ACCDIS_Msk;
}

void secret_bhk_lock(void) {
  TAMP_S->SECCFGR = 8 << TAMP_SECCFGR_BKPRWSEC_Pos | TAMP_SECCFGR_BHKLOCK;
}

secbool secret_bhk_locked(void) {
  return ((TAMP_S->SECCFGR & TAMP_SECCFGR_BHKLOCK) == TAMP_SECCFGR_BHKLOCK) *
         sectrue;
}

static secbool secret_present(uint32_t offset, uint32_t len) {
  uint8_t *optiga_secret =
      (uint8_t *)flash_area_get_address(&SECRET_AREA, offset, len);

  int optiga_secret_empty_bytes = 0;

  for (int i = 0; i < len; i++) {
    if (optiga_secret[i] == 0xFF) {
      optiga_secret_empty_bytes++;
    }
  }
  return sectrue * (optiga_secret_empty_bytes != len);
}

void secret_bhk_provision(void) {
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

secbool secret_optiga_present(void) {
  return secret_present(SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN);
}

void secret_optiga_backup(void) {
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

secbool secret_optiga_extract(uint8_t *dest) {
  uint8_t secret[SECRET_OPTIGA_KEY_LEN] = {0};
  uint8_t *secret_ptr = (uint8_t *)secret;

  bool all_zero = true;
  volatile uint32_t *reg1 = &TAMP->BKP8R;
  for (int i = 0; i < 8; i++) {
    uint32_t val = *reg1++;

    if (val != 0) {
      all_zero = false;
    }

    for (int j = 0; j < 4; j++) {
      secret_ptr[i * 4 + j] = (val >> (j * 8)) & 0xFF;
    }
  }

  if (all_zero) {
    return secfalse;
  }

  secbool res = secure_aes_ecb_decrypt_hw(secret, SECRET_OPTIGA_KEY_LEN, dest,
                                          SECURE_AES_KEY_DHUK);

  memzero(secret, sizeof(secret));
  return res;
}

void secret_optiga_hide(void) {
  volatile uint32_t *reg1 = &TAMP->BKP8R;
  for (int i = 0; i < 8; i++) {
    *reg1 = 0;
    reg1++;
  }
}

void secret_erase(void) {
  ensure(flash_area_erase(&SECRET_AREA, NULL), "secret erase");
}
