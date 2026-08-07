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

#include <memzero.h>

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/rsod_special.h>
#include <sec/secret.h>
#include "rtl/secbool.h"

#ifdef KERNEL_MODE

#ifdef LOCKABLE_BOOTLOADER
static secbool bootloader_locked = secfalse;
#endif

#ifndef SECRET_NUM_KEY_SLOTS
#define SECRET_NUM_KEY_SLOTS 0
#endif

#ifdef SECRET_KEY_SLOT_0_LEN
static uint8_t secret_key_slot0[SECRET_KEY_SLOT_0_LEN] = {
    0xb8, 0x8d, 0x6c, 0x53, 0x28, 0x46, 0x5f, 0x3d, 0x58, 0x05, 0xc5,
    0xf4, 0x68, 0x8a, 0xd7, 0xf8, 0x08, 0xc0, 0x8e, 0x11, 0x68, 0xf0,
    0x47, 0x93, 0x58, 0xfd, 0xbb, 0xb8, 0xf8, 0x2b, 0xe0, 0xce};
_Static_assert(SECRET_KEY_SLOT_0_LEN == 32);
#endif
#ifdef SECRET_KEY_SLOT_1_LEN
static uint8_t secret_key_slot1[SECRET_KEY_SLOT_1_LEN] = {
    0x98, 0xf3, 0xff, 0x58, 0xe8, 0xa3, 0xc5, 0xe2, 0x38, 0x51, 0x7a,
    0x77, 0x28, 0xf0, 0x4d, 0xd7, 0x08, 0x2e, 0x5d, 0x1b, 0xe8, 0xea,
    0x61, 0x46, 0xb8, 0x28, 0x50, 0xdf, 0x58, 0xe1, 0x12, 0xd4};
_Static_assert(SECRET_KEY_SLOT_1_LEN == 32);
#endif
#ifdef SECRET_KEY_SLOT_2_LEN
static uint8_t secret_key_slot2[SECRET_KEY_SLOT_2_LEN] = {
    0x31, 0xe9, 0x0a, 0xf1, 0x50, 0x45, 0x10, 0xee, 0x4e, 0xfd, 0x79,
    0x13, 0x33, 0x41, 0x48, 0x15, 0x89, 0xa2, 0x89, 0x5c, 0xc5, 0xfb,
    0xb1, 0x3e, 0xd5, 0x71, 0x1c, 0x1e, 0x9b, 0x81, 0x98, 0x72};
_Static_assert(SECRET_KEY_SLOT_2_LEN == 32);
#endif

#ifdef SECRET_LOCK_SLOT_OFFSET
static secbool secret_sector_locked = secfalse;
#endif

size_t secret_get_slot_len(uint8_t slot) {
  switch (slot) {
#ifdef SECRET_KEY_SLOT_0_LEN
    case 0:
      return SECRET_KEY_SLOT_0_LEN;
#endif
#ifdef SECRET_KEY_SLOT_1_LEN
    case 1:
      return SECRET_KEY_SLOT_1_LEN;
#endif
#ifdef SECRET_KEY_SLOT_2_LEN
    case 2:
      return SECRET_KEY_SLOT_2_LEN;
#endif
    default:
      break;
  }
  return 0;
}

uint8_t* secret_get_slot_ptr(uint8_t slot) {
  switch (slot) {
#ifdef SECRET_KEY_SLOT_0_LEN
    case 0:
      return secret_key_slot0;
#endif
#ifdef SECRET_KEY_SLOT_1_LEN
    case 1:
      return secret_key_slot1;
#endif
#ifdef SECRET_KEY_SLOT_2_LEN
    case 2:
      return secret_key_slot2;
#endif
    default:
      break;
  }
  return NULL;
}

void secret_erase(void) {
  for (uint8_t i = 0; i < SECRET_NUM_KEY_SLOTS; i++) {
    uint8_t* slot_ptr = secret_get_slot_ptr(i);
    if (slot_ptr != NULL) {
      memset(slot_ptr, 0xff, secret_get_slot_len(i));
    }
  }
}

#ifdef LOCKABLE_BOOTLOADER
secbool secret_bootloader_locked(void) { return bootloader_locked; }

void secret_unlock_bootloader(void) {
  secret_erase();
  bootloader_locked = secfalse;
}

void secret_lock_bootloader(void) { bootloader_locked = sectrue; }
#endif

secbool secret_key_set(uint8_t slot, const uint8_t* key, size_t len) {
  if (slot >= SECRET_NUM_KEY_SLOTS) {
    return secfalse;
  }

  if (len != secret_get_slot_len(slot)) {
    return secfalse;
  }

  uint8_t* slot_ptr = secret_get_slot_ptr(slot);
  if (slot_ptr == NULL) {
    return secfalse;
  }

  memcpy(slot_ptr, key, len);
  return sectrue;
}

secbool secret_key_get(uint8_t slot, uint8_t* dest, size_t len) {
  if (slot >= SECRET_NUM_KEY_SLOTS) {
    return secfalse;
  }

  if (len != secret_get_slot_len(slot)) {
    return secfalse;
  }

  uint8_t* slot_ptr = secret_get_slot_ptr(slot);
  if (slot_ptr == NULL) {
    return secfalse;
  }

  bool is_valid = false;
  for (int i = 0; i < len; i++) {
    if (slot_ptr[i] != 0xFF && slot_ptr[i] != 0x00) {
      is_valid = true;
      break;
    }
  }

  if (!is_valid) {
    return secfalse;
  }

  memcpy(dest, slot_ptr, len);
  return sectrue;
}

secbool secret_key_writable(uint8_t slot) {
  if (slot >= SECRET_NUM_KEY_SLOTS) {
    return secfalse;
  }

  uint8_t* slot_ptr = secret_get_slot_ptr(slot);
  if (slot_ptr == NULL) {
    return secfalse;
  }

  size_t len = secret_get_slot_len(slot);
  if (len == 0) {
    return secfalse;
  }

  for (int i = 0; i < len; i++) {
    if (slot_ptr[i] != 0xFF) {
      return secfalse;
    }
  }

  return sectrue;
}

void secret_reset(void) {}

void secret_prepare_fw(secbool allow_run_with_secret,
                       secbool allow_provisioning_access) {
  (void)allow_provisioning_access;
#ifdef LOCKABLE_BOOTLOADER
  if (sectrue != allow_run_with_secret && sectrue != bootloader_locked) {
    // This function does not return
    show_install_restricted_screen();
  }
#endif
}

void secret_init(void) {}

#ifdef SECRET_LOCK_SLOT_OFFSET

secbool secret_is_locked(void) { return secret_sector_locked; }

secbool secret_lock(void) {
  secret_sector_locked = sectrue;
  return sectrue;
}

#endif

void secret_bhk_regenerate(void) {}

#endif  // KERNEL_MODE

#ifdef USE_MCU_ATTESTATION

#include <sec/mcu_attestation.h>

#if defined(TREZOR_PRODTEST)
#define MCU_DEVICE_CERT {0}
#define MCU_DEVICE_CERT_SIZE 0
#elif defined(TREZOR_MODEL_T3W1)
#include "certs/T3W1.h"
#else
#error "MCU attestation is only supported for T3W1 model."
#endif

#ifndef MCU_DEVICE_CERT_SIZE
#define MCU_DEVICE_CERT_SIZE sizeof((uint8_t[])MCU_DEVICE_CERT)
#endif

static uint8_t mcu_device_cert[MCU_ATTESTATION_MAX_CERT_SIZE] = MCU_DEVICE_CERT;
static size_t mcu_device_cert_size = MCU_DEVICE_CERT_SIZE;

secbool secret_mcu_device_cert_write(const uint8_t* cert, size_t cert_size) {
#ifdef TREZOR_PRODTEST
  if (cert_size > MCU_ATTESTATION_MAX_CERT_SIZE) {
    return secfalse;
  }
  memcpy(mcu_device_cert, cert, cert_size);
  mcu_device_cert_size = cert_size;
  return sectrue;
#else
  (void)cert;
  (void)cert_size;
  return secfalse;
#endif
}

secbool secret_mcu_device_cert_size(size_t* cert_size) {
  *cert_size = mcu_device_cert_size;
  return sectrue;
}

secbool secret_mcu_device_cert_read(uint8_t* cert, size_t max_cert_size,
                                    size_t* cert_size) {
  if (mcu_device_cert_size > max_cert_size) {
    return secfalse;
  }
  *cert_size = mcu_device_cert_size;
  memcpy(cert, mcu_device_cert, *cert_size);
  return sectrue;
}

#endif  // USE_MCU_ATTESTATION
