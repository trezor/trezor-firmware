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
#include <sys/mpu.h>
#include <util/flash.h>

#ifdef KERNEL_MODE

static uint8_t SECRET_TROPIC_TREZOR_PRIVKEY_BYTES[] = {
    0xf0, 0xc4, 0xaa, 0x04, 0x8f, 0x00, 0x13, 0xa0, 0x96, 0x84, 0xdf,
    0x05, 0xe8, 0xa2, 0x2e, 0xf7, 0x21, 0x38, 0x98, 0x28, 0x2b, 0xa9,
    0x43, 0x12, 0xf3, 0x13, 0xdf, 0x2d, 0xce, 0x8d, 0x41, 0x64};

static uint8_t SECRET_TROPIC_PUBKEY_BYTES[] = {
    0x31, 0xE9, 0x0A, 0xF1, 0x50, 0x45, 0x10, 0xEE, 0x4E, 0xFD, 0x79,
    0x13, 0x33, 0x41, 0x48, 0x15, 0x89, 0xA2, 0x89, 0x5C, 0xC5, 0xFB,
    0xB1, 0x3E, 0xD5, 0x71, 0x1C, 0x1E, 0x9B, 0x81, 0x98, 0x72};

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

secbool secret_tropic_get_trezor_privkey(uint8_t dest[SECRET_TROPIC_KEY_LEN]) {
  memcpy(dest, &SECRET_TROPIC_TREZOR_PRIVKEY_BYTES, SECRET_TROPIC_KEY_LEN);
  return sectrue;
}

secbool secret_tropic_get_tropic_pubkey(uint8_t dest[SECRET_TROPIC_KEY_LEN]) {
  memcpy(dest, &SECRET_TROPIC_PUBKEY_BYTES, SECRET_TROPIC_KEY_LEN);
  return sectrue;
}

void secret_prepare_fw(secbool allow_run_with_secret,
                       secbool allow_provisioning_access) {
  (void)allow_provisioning_access;
#ifdef USE_OPTIGA
  if (sectrue != allow_run_with_secret && sectrue != secret_wiped()) {
    // This function does not return
    show_install_restricted_screen();
  }
#endif
}

void secret_init(void) {}

#endif  // KERNEL_MODE
