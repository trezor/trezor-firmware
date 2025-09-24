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

#pragma once

#include <trezor_types.h>

// Secure monitor call arguments
typedef struct {
  // Up to 6 arguments can be passed
  uint32_t arg[6];
} smcall_args_t;

// Secure monitor call identifiers
typedef enum {

  SMCALL_BOOTARGS_SET = 1,
  SMCALL_BOOTARGS_GET_ARGS,

  SMCALL_BOOT_IMAGE_CHECK,
  SMCALL_BOOT_IMAGE_REPLACE,

  SMCALL_REBOOT_DEVICE,
  SMCALL_REBOOT_TO_BOOTLOADER,
  SMCALL_REBOOT_AND_UPGRADE,
  SMCALL_REBOOT_TO_OFF,
  SMCALL_REBOOT_WITH_RSOD,

  SMCALL_SUSPEND_CPU,
  SMCALL_SUSPEND_SECURE_DRIVERS,
  SMCALL_RESUME_SECURE_DRIVERS,

  SMCALL_GET_BOARD_NAME,
  SMCALL_GET_BOARDLOADER_VERSION,

  SMCALL_UNIT_PROPERTIES_GET,

  SMCALL_SECRET_BOOTLOADER_LOCKED,
  SMCALL_SECRET_VALIDATE_NRF_PAIRING,

  SMCALL_WAIT_RANDOM,
  SMCALL_RANDOM_DELAYS_REFRESH_RDI,

  SMCALL_OPTIGA_SIGN,
  SMCALL_OPTIGA_CERT_SIZE,
  SMCALL_OPTIGA_READ_CERT,
  SMCALL_OPTIGA_READ_SEC,
  SMCALL_OPTIGA_SET_SEC_MAX,

  SMCALL_STORAGE_SETUP,
  SMCALL_STORAGE_WIPE,
  SMCALL_STORAGE_IS_UNLOCKED,
  SMCALL_STORAGE_LOCK,
  SMCALL_STORAGE_UNLOCK,
  SMCALL_STORAGE_HAS_PIN,
  SMCALL_STORAGE_PIN_FAILS_INCREASE,
  SMCALL_STORAGE_GET_PIN_REM,
  SMCALL_STORAGE_CHANGE_PIN,
  SMCALL_STORAGE_ENSURE_NOT_WIPE_CODE,
  SMCALL_STORAGE_HAS_WIPE_CODE,
  SMCALL_STORAGE_CHANGE_WIPE_CODE,
  SMCALL_STORAGE_HAS,
  SMCALL_STORAGE_GET,
  SMCALL_STORAGE_SET,
  SMCALL_STORAGE_DELETE,
  SMCALL_STORAGE_SET_COUNTER,
  SMCALL_STORAGE_NEXT_COUNTER,

  SMCALL_RNG_FILL_BUFFER,
  SMCALL_RNG_FILL_BUFFER_STRONG,

  SMCALL_FIRMWARE_GET_VENDOR,
  SMCALL_FIRMWARE_HASH_START,
  SMCALL_FIRMWARE_HASH_CONTINUE,

  SMCALL_TROPIC_PING,
  SMCALL_TROPIC_ECC_KEY_GENERATE,
  SMCALL_TROPIC_ECC_SIGN,
  SMCALL_TROPIC_DATA_READ,

  SMCALL_BACKUP_RAM_SEARCH,
  SMCALL_BACKUP_RAM_READ,
  SMCALL_BACKUP_RAM_WRITE,

} smcall_number_t;
