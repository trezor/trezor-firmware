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

#include <rtl/cli.h>
#include <util/flash_otp.h>

static void prodtest_otp_read(cli_t* cli, uint8_t block_num) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t block[FLASH_OTP_BLOCK_SIZE] = {0};

  cli_trace(cli, "Reading device OTP memory...");

  if (sectrue != flash_otp_read(block_num, 0, block, sizeof(block))) {
    cli_error(cli, CLI_ERROR, "Failed to read OTP memory.");
    return;
  }

  char block_hex[FLASH_OTP_BLOCK_SIZE * 2 + 1];

  if (!cstr_encode_hex(block_hex, sizeof(block_hex), block, sizeof(block))) {
    cli_error(cli, CLI_ERROR_FATAL, "Buffer too small.");
    return;
  }

  cli_trace(cli, "Bytes read: %s", block_hex);

  char block_text[FLASH_OTP_BLOCK_SIZE + 1] = {0};

  for (size_t i = 0; i < sizeof(block); i++) {
    if (block[i] == 0xFF) {
      break;
    }
    block_text[i] = block[i];
  }

  if (strlen(block_text) > 0) {
    cli_ok(cli, "%s", block_text);
  } else {
    cli_error(cli, CLI_ERROR_NODATA, "OTP block is empty.");
  }
}

static void prodtest_otp_write(cli_t* cli, uint8_t block_num) {
  const char* data = cli_arg(cli, "text");

  if (strlen(data) == 0 || strlen(data) > FLASH_OTP_BLOCK_SIZE - 1) {
    cli_error_arg(cli, "Expecting text (up to 31 characters).");
    return;
  }

#if PRODUCTION
  bool dry_run = false;
#else
  bool dry_run = true;
#endif

  if (cli_has_nth_arg(cli, 1)) {
    const char* option = cli_nth_arg(cli, 1);
    if (strcmp(option, "--execute") == 0) {
      dry_run = false;
    } else if (strcmp(option, "--dry-run") == 0) {
      dry_run = true;
    } else {
      cli_error_arg(cli, "Expecting '--execute' or '--dry-run'.");
      return;
    }
  }

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  if (dry_run) {
    cli_trace(cli, "");
    cli_trace(cli, "!!! It's a dry run, OTP will be left unchanged.");
    cli_trace(cli, "!!! Use '--execute' switch to write to OTP memory.");
    cli_trace(cli, "");
  }

  uint8_t block[FLASH_OTP_BLOCK_SIZE] = {0};
  memcpy(block, data, MIN(sizeof(block) - 1, strlen(data)));

  char block_hex[FLASH_OTP_BLOCK_SIZE * 2 + 1];
  if (!cstr_encode_hex(block_hex, sizeof(block_hex), block, sizeof(block))) {
    cli_error(cli, CLI_ERROR_FATAL, "Buffer too small.");
    return;
  }

  if (sectrue == flash_otp_is_locked(block_num)) {
    cli_error(cli, CLI_ERROR_LOCKED,
              "OTP block is locked and cannot be written again.");
    return;
  }

  cli_trace(cli, "Writing info into OTP memory...");
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

static void prodtest_otp_batch_read(cli_t* cli) {
  prodtest_otp_read(cli, FLASH_OTP_BLOCK_BATCH);
}

static void prodtest_otp_batch_write(cli_t* cli) {
  prodtest_otp_write(cli, FLASH_OTP_BLOCK_BATCH);
}

static void prodtest_otp_device_id_read(cli_t* cli) {
  prodtest_otp_read(cli, FLASH_OTP_BLOCK_DEVICE_ID);
}

static void prodtest_otp_device_id_write(cli_t* cli) {
  prodtest_otp_write(cli, FLASH_OTP_BLOCK_DEVICE_ID);
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "otp-batch-read",
  .func = prodtest_otp_batch_read,
  .info = "Read the device batch info from OTP memory",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "otp-batch-write",
  .func = prodtest_otp_batch_write,
  .info = "Write the device batch info into OTP memory",
  .args = "<text> [--execute | --dry-run]"
);

PRODTEST_CLI_CMD(
  .name = "otp-device-id-read",
  .func = prodtest_otp_device_id_read,
  .info = "Read the device ID from OTP memory",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "otp-device-id-write",
  .func = prodtest_otp_device_id_write,
  .info = "Write the device ID into OTP memory",
  .args = "<text> [--execute | --dry-run]"
);
