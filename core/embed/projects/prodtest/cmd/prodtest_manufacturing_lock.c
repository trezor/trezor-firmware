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

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sec/unit_properties.h>
#include <sys/flash_otp.h>

#include "prodtest_error_codes.h"

static void prodtest_manufacturing_lock_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  unit_properties_t props = {0};
  unit_properties_get(&props);

  if (props.locked) {
    cli_ok(cli, "locked");
  } else {
    cli_ok(cli, "unlocked");
  }
}

#ifdef FLASH_OTP_BLOCK_MANUFACTURING_LOCK

static void prodtest_manufacturing_lock_write(cli_t* cli) {
#if PRODUCTION
  bool dry_run = false;
#else
  bool dry_run = true;
#endif

  int arg_idx = 0;
  while (arg_idx < cli_arg_count(cli)) {
    const char* arg = cli_nth_arg(cli, arg_idx++);
    if (strcmp(arg, "--execute") == 0) {
      dry_run = false;
    } else if (strcmp(arg, "--dry-run") == 0) {
      dry_run = true;
    } else {
      cli_error_arg(cli, "Unknown argument: %s", arg);
      return;
    }
  }

  if (sectrue == flash_otp_is_locked(FLASH_OTP_BLOCK_MANUFACTURING_LOCK)) {
    cli_error(cli, PRODTEST_ERR_MANUF_LOCK_ALREADY_SET,
              "Manufacturing lock is already set.");
    return;
  }

  if (dry_run) {
    cli_trace(cli, "");
    cli_trace(cli, "!!! It's a dry run, OTP will be left unchanged.");
    cli_trace(cli, "!!! Use '--execute' switch to write to OTP memory.");
    cli_trace(cli, "");
  }

  // Write a non-0xFF value to mark the block as used
  uint8_t block[FLASH_OTP_BLOCK_SIZE];
  memset(block, 0x00, sizeof(block));
  block[0] = 0x01;  // Manufacturing lock marker

  cli_trace(cli, "Writing manufacturing lock into OTP memory...");

  if (!dry_run) {
    if (sectrue != flash_otp_write(FLASH_OTP_BLOCK_MANUFACTURING_LOCK, 0, block,
                                   sizeof(block))) {
      cli_error(cli, PRODTEST_ERR_MANUF_LOCK_OTP_WRITE,
                "Failed to write OTP block.");
      return;
    }

    cli_trace(cli, "Locking OTP block...");

    if (sectrue != flash_otp_lock(FLASH_OTP_BLOCK_MANUFACTURING_LOCK)) {
      cli_error(cli, PRODTEST_ERR_MANUF_LOCK_OTP_LOCK,
                "Failed to lock the OTP block.");
      return;
    }
  }

  // reset cached properties
  unit_properties_deinit();
  unit_properties_init();

  cli_ok(cli, "");
}

#endif

// clang-format off

PRODTEST_CLI_CMD(
  .name = "manufacturing-lock-read",
  .func = prodtest_manufacturing_lock_read,
  .info = "Read the manufacturing lock status from OTP memory",
  .args = ""
);

#ifdef FLASH_OTP_BLOCK_MANUFACTURING_LOCK

PRODTEST_CLI_CMD(
  .name = "manufacturing-lock-write",
  .func = prodtest_manufacturing_lock_write,
  .info = "Write the manufacturing lock into OTP memory, exiting manufacturing mode",
  .args = "[--execute | --dry-run]"
);

#endif  // FLASH_OTP_BLOCK_MANUFACTURING_LOCK
