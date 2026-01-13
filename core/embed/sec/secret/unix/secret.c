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

#ifdef KERNEL_MODE

#ifdef LOCKABLE_BOOTLOADER
static secbool bootloader_locked = secfalse;
#endif

#ifndef SECRET_NUM_KEY_SLOTS
#define SECRET_NUM_KEY_SLOTS 0
#endif

#ifdef SECRET_KEY_SLOT_0_LEN
static uint8_t secret_key_slot0[SECRET_KEY_SLOT_0_LEN] = {0};
#endif
#ifdef SECRET_KEY_SLOT_1_LEN
static uint8_t secret_key_slot1[SECRET_KEY_SLOT_1_LEN] = {0};
#endif
#ifdef SECRET_KEY_SLOT_2_LEN
static uint8_t secret_key_slot2[SECRET_KEY_SLOT_2_LEN] = {0};
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
      memzero(slot_ptr, secret_get_slot_len(i));
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

  memcpy(dest, slot_ptr, len);
  return sectrue;
}

static secbool secret_key_present(uint8_t slot) {
  if (slot >= SECRET_NUM_KEY_SLOTS) {
    return secfalse;
  }

  uint8_t* slot_ptr = secret_get_slot_ptr(slot);
  if (slot_ptr == NULL) {
    return secfalse;
  }

  for (size_t i = 0; i < secret_get_slot_len(slot); i++) {
    if (slot_ptr[i] != 0) {
      return sectrue;
    }
  }
  return secfalse;
}

secbool secret_key_writable(uint8_t slot) {
  return secret_key_present(slot) == secfalse;
}

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

#endif  // KERNEL_MODE
