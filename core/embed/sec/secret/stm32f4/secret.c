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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/secret.h>
#include <sys/flash.h>
#include <sys/flash_utils.h>
#include <sys/mpu.h>
#include <util/rsod_special.h>

#ifdef KERNEL_MODE

#ifdef SECRET_NUM_KEY_SLOTS

#define SECRET_HEADER_MAGIC "TRZS"
#define SECRET_HEADER_MAGIC_LEN (sizeof(SECRET_HEADER_MAGIC) - 1)

#define SECRET_NUM_MAX_SLOTS 1

_Static_assert(SECRET_NUM_MAX_SLOTS >= SECRET_NUM_KEY_SLOTS,
               "Exceeded max slots");
_Static_assert(SECRET_KEY_SLOT_0_LEN == 32, "Invalid key slot length");

static secbool bootloader_locked_set = secfalse;
static secbool bootloader_locked = secfalse;

secbool secret_verify_header(void) {
  uint8_t* addr = (uint8_t*)flash_area_get_address(
      &SECRET_AREA, SECRET_HEADER_OFFSET, SECRET_HEADER_LEN);

  if (addr == NULL) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);

  bootloader_locked =
      memcmp(addr, SECRET_HEADER_MAGIC, SECRET_HEADER_MAGIC_LEN) == 0
          ? sectrue
          : secfalse;

  mpu_restore(mpu_mode);

  bootloader_locked_set = sectrue;
  return bootloader_locked;
}

static void secret_erase(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  ensure(flash_area_erase(&SECRET_AREA, NULL), "secret erase");
  mpu_restore(mpu_mode);
}

#ifdef LOCKABLE_BOOTLOADER
secbool secret_bootloader_locked(void) {
  if (bootloader_locked_set != sectrue) {
    // Set bootloader_locked.
    secret_verify_header();
  }

  return bootloader_locked;
}

void secret_unlock_bootloader(void) { secret_erase(); }
#endif

void secret_write_header(void) {
  uint8_t header[SECRET_HEADER_LEN] = {0};
  memcpy(header, SECRET_HEADER_MAGIC, SECRET_HEADER_MAGIC_LEN);
  ensure(secret_write(header, SECRET_HEADER_OFFSET, SECRET_HEADER_LEN),
         "secret write header failed");
}

secbool secret_write(const uint8_t* data, uint32_t offset, uint32_t len) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_SECRET);
  ensure(flash_unlock_write(), "secret write");
  for (int i = 0; i < len; i++) {
    if (sectrue != flash_area_write_byte(&SECRET_AREA, offset + i, data[i])) {
      ensure(flash_lock_write(), "secret write");
      mpu_restore(mpu_mode);
      return secfalse;
    }
  }
  ensure(flash_lock_write(), "secret write");
  mpu_restore(mpu_mode);

  return sectrue;
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

static secbool secret_wiped(void) {
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

secbool secret_key_set(uint8_t slot, const uint8_t* key, size_t len) {
  if (slot >= SECRET_NUM_KEY_SLOTS) {
    return secfalse;
  }

  if (len != SECRET_KEY_SLOT_0_LEN) {
    return secfalse;
  }

  uint32_t offset = SECRET_KEY_SLOT_0_OFFSET;

  secret_erase();
  secret_write_header();
  return secret_write(key, offset, len);
}

secbool secret_key_get(uint8_t slot, uint8_t* dest, size_t len) {
  if (slot >= SECRET_NUM_KEY_SLOTS) {
    return secfalse;
  }

  if (len != SECRET_KEY_SLOT_0_LEN) {
    return secfalse;
  }

  uint32_t offset = SECRET_KEY_SLOT_0_OFFSET;

  return secret_read(dest, offset, len);
}

secbool secret_key_writable(uint8_t slot) {
  if (slot >= SECRET_NUM_KEY_SLOTS) {
    return secfalse;
  }

  return secret_wiped();
}

#endif

void secret_prepare_fw(secbool allow_run_with_secret,
                       secbool allow_provisioning_access) {
  (void)allow_provisioning_access;
#ifdef LOCKABLE_BOOTLOADER
  if (sectrue != allow_run_with_secret && sectrue != secret_wiped()) {
    // This function does not return
    show_install_restricted_screen();
  }
#endif
}

void secret_init(void) {}

void secret_safety_erase(void) {
  // On STM32F4, secret keys are not used, so the entire
  // storage must be erased.
  ensure(erase_storage(NULL), NULL);
}

#endif  // KERNEL_MODE
