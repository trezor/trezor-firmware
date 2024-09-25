#include "secret.h"
#include <string.h>
#include "common.h"
#include "display_draw.h"
#include "flash.h"
#include "model.h"
#include "mpu.h"

#ifdef KERNEL_MODE

static secbool bootloader_locked_set = secfalse;
static secbool bootloader_locked = secfalse;

secbool secret_verify_header(void) {
  uint8_t* addr = (uint8_t*)flash_area_get_address(&SECRET_AREA, 0,
                                                   sizeof(SECRET_HEADER_MAGIC));

  if (addr == NULL) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);

  bootloader_locked =
      memcmp(addr, SECRET_HEADER_MAGIC, sizeof(SECRET_HEADER_MAGIC)) == 0
          ? sectrue
          : secfalse;

  mpu_restore(mpu_mode);

  bootloader_locked_set = sectrue;
  return bootloader_locked;
}

secbool secret_bootloader_locked(void) {
  if (bootloader_locked_set != sectrue) {
    // Set bootloader_locked.
    secret_verify_header();
  }

  return bootloader_locked;
}

void secret_write_header(void) {
  uint8_t header[SECRET_HEADER_LEN] = {0};
  memcpy(header, SECRET_HEADER_MAGIC, 4);
  secret_write(header, 0, SECRET_HEADER_LEN);
}

void secret_write(const uint8_t* data, uint32_t offset, uint32_t len) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  ensure(flash_unlock_write(), "secret write");
  for (int i = 0; i < len; i++) {
    ensure(flash_area_write_byte(&SECRET_AREA, offset + i, data[i]),
           "secret write");
  }
  ensure(flash_lock_write(), "secret write");
  mpu_restore(mpu_mode);
}

secbool secret_read(uint8_t* data, uint32_t offset, uint32_t len) {
  if (sectrue != secret_verify_header()) {
    return secfalse;
  }

  uint8_t* addr = (uint8_t*)flash_area_get_address(&SECRET_AREA, offset, len);

  if (addr == NULL) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  memcpy(data, addr, len);
  mpu_restore(mpu_mode);

  return sectrue;
}

secbool secret_wiped(void) {
  uint32_t size = flash_area_get_size(&SECRET_AREA);
  secbool wiped = sectrue;

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);

  for (int i = 0; i < size; i += 4) {
    uint32_t* addr = (uint32_t*)flash_area_get_address(&SECRET_AREA, i, 4);
    if (addr == NULL) {
      wiped = secfalse;
      break;
    }
    if (*addr != 0xFFFFFFFF) {
      wiped = secfalse;
      break;
    }
  }

  mpu_restore(mpu_mode);

  return wiped;
}

void secret_erase(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  ensure(flash_area_erase(&SECRET_AREA, NULL), "secret erase");
  mpu_restore(mpu_mode);
}

secbool secret_optiga_set(const uint8_t secret[SECRET_OPTIGA_KEY_LEN]) {
  secret_erase();
  secret_write_header();
  secret_write(secret, SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN);
  return sectrue;
}

secbool secret_optiga_get(uint8_t dest[SECRET_OPTIGA_KEY_LEN]) {
  return secret_read(dest, SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN);
}

secbool secret_optiga_present(void) {
  return (sectrue != secret_wiped()) * sectrue;
}

secbool secret_optiga_writable(void) { return secret_wiped(); }

void secret_optiga_erase(void) { secret_erase(); }

void secret_prepare_fw(secbool allow_run_with_secret, secbool _trust_all) {
#ifdef USE_OPTIGA
  if (sectrue != allow_run_with_secret && sectrue != secret_wiped()) {
    // This function does not return
    show_install_restricted_screen();
  }
#endif
}

void secret_init(void) {}

#endif  // KERNEL_MODE
