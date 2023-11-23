#include "secret.h"
#include <stdbool.h>
#include <string.h>
#include "common.h"
#include "flash.h"
#include "model.h"
#include "rng.h"

static secbool bootloader_locked_set = secfalse;
static secbool bootloader_locked = secfalse;

static secbool verify_header(void) {
  uint8_t header[SECRET_HEADER_LEN] = {0};

  memcpy(header, flash_area_get_address(&SECRET_AREA, 0, SECRET_HEADER_LEN),
         SECRET_HEADER_LEN);

  bootloader_locked =
      memcmp(header, SECRET_HEADER_MAGIC, 4) == 0 ? sectrue : secfalse;
  bootloader_locked_set = sectrue;
  return bootloader_locked;
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
  if (sectrue != verify_header()) {
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

void secret_bhk_provision(void) {
  uint32_t secret[SECRET_BHK_LEN / sizeof(uint32_t)] = {0};
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
}

void secret_bhk_regenerate(void) {
  ensure(flash_area_erase(&BHK_AREA, NULL), "Failed regenerating BHK");
  ensure(flash_unlock_write(), "Failed regenerating BHK");
  for (int i = 0; i < 2; i++) {
    uint32_t val[4] = {0};
    for (int j = 0; j < 4; j++) {
      val[j] = rng_get();
    }
    ensure(flash_area_write_quadword(&BHK_AREA, i * 4 * sizeof(uint32_t), val),
           "Failed regenerating BHK");
  }
  ensure(flash_lock_write(), "Failed regenerating BHK");
}

secbool secret_optiga_present(void) {
  uint8_t *optiga_secret = (uint8_t *)flash_area_get_address(
      &SECRET_AREA, SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN);

  int optiga_secret_empty_bytes = 0;

  for (int i = 0; i < SECRET_OPTIGA_KEY_LEN; i++) {
    if (optiga_secret[i] == 0xFF) {
      optiga_secret_empty_bytes++;
    }
  }
  return sectrue * (optiga_secret_empty_bytes != SECRET_OPTIGA_KEY_LEN);
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
}

secbool secret_optiga_extract(uint8_t *dest) {
  bool all_zero = true;
  volatile uint32_t *reg1 = &TAMP->BKP8R;
  for (int i = 0; i < 8; i++) {
    uint32_t val = *reg1++;

    if (val != 0) {
      all_zero = false;
    }

    for (int j = 0; j < 4; j++) {
      dest[i * 4 + j] = (val >> (j * 8)) & 0xFF;
    }
  }

  return all_zero ? secfalse : sectrue;
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
