#include "secret.h"
#include <string.h>
#include "common.h"
#include "flash.h"
#include "model.h"

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
  if (bootloader_locked_set != sectrue) {
    // Set bootloader_locked.
    verify_header();
  }

  return bootloader_locked;
}

void secret_write_header(void) {
  uint8_t header[SECRET_HEADER_LEN] = {0};
  memcpy(header, SECRET_HEADER_MAGIC, 4);
  secret_write(header, 0, SECRET_HEADER_LEN);
}

void secret_write(uint8_t* data, uint32_t offset, uint32_t len) {
  ensure(flash_unlock_write(), "secret write");
  for (int i = 0; i < len; i++) {
    ensure(flash_area_write_byte(&SECRET_AREA, offset + i, data[i]),
           "secret write");
  }
  ensure(flash_lock_write(), "secret write");
}

secbool secret_read(uint8_t* data, uint32_t offset, uint32_t len) {
  if (sectrue != verify_header()) {
    return secfalse;
  }

  memcpy(data, flash_area_get_address(&SECRET_AREA, offset, len), len);

  return sectrue;
}

secbool secret_wiped(void) {
  flash_area_get_address(&SECRET_AREA, 0, 1);

  flash_area_get_size(&SECRET_AREA);

  uint32_t size = flash_area_get_size(&SECRET_AREA);

  for (int i = 0; i < size; i += 4) {
    uint32_t* addr = (uint32_t*)flash_area_get_address(&SECRET_AREA, i, 4);
    if (*addr != 0xFFFFFFFF) {
      return secfalse;
    }
  }
  return sectrue;
}

void secret_erase(void) {
  ensure(flash_area_erase(&SECRET_AREA, NULL), "secret erase");
}
