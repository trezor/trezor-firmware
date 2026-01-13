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
#include <rtl/printf.h>
#include <sec/secret.h>
#include <sys/flash_otp.h>

#include <stdlib.h>
#include "prodtest_optiga.h"

#ifdef USE_TROPIC
#include "prodtest_tropic.h"
#endif

static void prodtest_otp_variant_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t block[FLASH_OTP_BLOCK_SIZE] = {0};
  uint8_t block_rework[FLASH_OTP_BLOCK_SIZE] = {0};

  cli_trace(cli, "Reading device OTP memory...");

  if (sectrue !=
      flash_otp_read(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0, block, sizeof(block))) {
    cli_error(cli, CLI_ERROR, "Failed to read OTP memory.");
    return;
  }

  if (sectrue != flash_otp_read(FLASH_OTP_BLOCK_DEVICE_VARIANT_REWORK, 0,
                                block_rework, sizeof(block_rework))) {
    cli_error(cli, CLI_ERROR, "Failed to read OTP memory.");
    return;
  }

  if (block_rework[0] != 0xFF) {
    cli_trace(cli, "Rework block present, using it instead of the original.");
    memcpy(block, block_rework, sizeof(block));
  }

  char block_hex[FLASH_OTP_BLOCK_SIZE * 2 + 1];

  if (!cstr_encode_hex(block_hex, sizeof(block_hex), block, sizeof(block))) {
    cli_error(cli, CLI_ERROR_FATAL, "Buffer too small.");
    return;
  }

  cli_trace(cli, "Bytes read: %s", block_hex);

  char block_text[FLASH_OTP_BLOCK_SIZE * 4 + 1] = {0};
  size_t buffer_size = sizeof(block_text);

  // Make a list of integers separated by spaces
  char* dst = block_text;
  for (int i = 0; i < sizeof(block); i++) {
    if (i != 0) {
      *dst++ = ' ';
    }
    snprintf_(dst, buffer_size, "%d", block[i]);
    dst += strlen(dst);
    buffer_size -= strlen(dst);
  }

  cli_ok(cli, "%s", block_text);
}

static void prodtest_otp_variant_write(cli_t* cli) {
  uint8_t block[FLASH_OTP_BLOCK_SIZE] = {0};

#if PRODUCTION
  bool dry_run = false;
#else
  bool dry_run = true;
#endif
  bool rework = false;

  int arg_idx = 0;
  int val_count = 0;

  block[val_count++] = 0x01;  // Always 1

  while (arg_idx < cli_arg_count(cli)) {
    const char* arg = cli_nth_arg(cli, arg_idx++);
    uint32_t val = 0;

    if (strcmp(arg, "--execute") == 0) {
      dry_run = false;
    } else if (strcmp(arg, "--rework") == 0) {
      dry_run = false;
      rework = true;
    } else if (strcmp(arg, "--dry-run") == 0) {
      dry_run = true;
    } else if (!cstr_parse_uint32(arg, 0, &val) || val > 255) {
      cli_error_arg(cli, "Expecting values in range 0-255.");
      return;
    } else if (val_count >= sizeof(block)) {
      cli_error_arg(cli, "Too many values, %d is the maximum.",
                    sizeof(block) - 1);
      return;
    } else {
      block[val_count++] = val;
    }
  }

  if (val_count == 0) {
    cli_error_arg(cli, "Expecting at least one value.");
    return;
  }

  if (dry_run) {
    cli_trace(cli, "");
    cli_trace(cli, "!!! It's a dry run, OTP will be left unchanged.");
    cli_trace(cli, "!!! Use '--execute' switch to write to OTP memory.");
    cli_trace(cli, "");
  }

#ifdef SECRET_LOCK_SLOT_OFFSET
  if (sectrue != secret_is_locked()) {
    cli_error(cli, CLI_ERROR, "Secrets not locked");
    return;
  }
#endif

#ifdef USE_OPTIGA
  optiga_locked_status optiga_status = get_optiga_locked_status(cli);

  if (optiga_status == OPTIGA_LOCKED_FALSE) {
    cli_error(cli, CLI_ERROR, "Optiga not locked");
    return;
  }

  if (optiga_status != OPTIGA_LOCKED_TRUE) {
    // Error reported by get_optiga_locked_status().
    return;
  }
#endif

#ifdef USE_TROPIC
  tropic_locked_status tropic_status = get_tropic_locked_status(cli);

  if (tropic_status == TROPIC_LOCKED_FALSE) {
    cli_error(cli, CLI_ERROR, "Tropic not locked");
    return;
  }

  if (tropic_status != TROPIC_LOCKED_TRUE) {
    // Error reported by get_optiga_locked_status().
    return;
  }
#endif

  uint8_t block_num = FLASH_OTP_BLOCK_DEVICE_VARIANT;

  if (rework) {
    block_num = FLASH_OTP_BLOCK_DEVICE_VARIANT_REWORK;

    if (sectrue == flash_otp_is_locked(block_num)) {
      cli_error(cli, CLI_ERROR_LOCKED,
                "OTP rework block is locked and cannot be written again.");
      return;
    }

    if (sectrue != flash_otp_is_locked(FLASH_OTP_BLOCK_DEVICE_VARIANT)) {
      cli_error(cli, CLI_ERROR_LOCKED,
                "Variant first block in not locked, rework not allowed.");
      return;
    }

    uint8_t block_read[FLASH_OTP_BLOCK_SIZE] = {0};
    if (sectrue != flash_otp_read(FLASH_OTP_BLOCK_DEVICE_VARIANT, 0, block_read,
                                  sizeof(block_read))) {
      cli_error(cli, CLI_ERROR, "Failed to read OTP memory.");
      return;
    }
    if (memcmp(block_read, block, sizeof(block_read)) == 0) {
      cli_error(cli, CLI_ERROR, "Rework not needed, already up to date.");
      return;
    }
  }

  if (sectrue == flash_otp_is_locked(block_num)) {
    cli_error(cli, CLI_ERROR_LOCKED,
              "OTP block is locked and cannot be written again.");
    return;
  }

  char block_hex[FLASH_OTP_BLOCK_SIZE * 2 + 1];
  if (!cstr_encode_hex(block_hex, sizeof(block_hex), block, sizeof(block))) {
    cli_error(cli, CLI_ERROR_FATAL, "Buffer too small.");
    return;
  }

  cli_trace(cli, "Writing device batch info into OTP memory...");
  cli_trace(cli, "Bytes written: %s", block_hex);

  if (!dry_run) {
    if (sectrue != flash_otp_write(block_num, 0, block, sizeof(block))) {
      cli_error(cli, CLI_ERROR, "Failed to write OTP block.");
      return;
    }
  }

  cli_trace(cli, "Locking OTP block...");

  if (!dry_run) {
    if (sectrue != flash_otp_lock(block_num)) {
      cli_error(cli, CLI_ERROR, "Failed to lock the OTP block.");
      return;
    }
  }

  // Respond with an OK message
  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "otp-variant-read",
  .func = prodtest_otp_variant_read,
  .info = "Read the device variant info from OTP memory",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "otp-variant-write",
  .func = prodtest_otp_variant_write,
  .info = "Write the device variant info into OTP memory",
  .args = "<values...> [--execute | --dry-run | --rework]"
);
