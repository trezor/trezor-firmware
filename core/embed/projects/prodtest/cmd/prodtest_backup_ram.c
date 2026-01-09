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

#ifdef USE_BACKUP_RAM

#include <trezor_rtl.h>

#include <io/power_manager.h>
#include <rtl/cli.h>
#include <sec/backup_ram.h>
#include <sys/systick.h>

static void prodtest_backup_ram_list(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!backup_ram_init()) {
    cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
    return;
  }

  int key_count = 0;
  uint16_t key = 0;

  while ((key = backup_ram_search(key)) != BACKUP_RAM_INVALID_KEY) {
    size_t data_size = 0;
    if (backup_ram_read(key, NULL, 0, &data_size)) {
      cli_trace(cli, "Key #%d: %d bytes", key, data_size);
    } else {
      cli_error(cli, CLI_ERROR, "Failed to read key #%d info", key);
      return;
    }
    key++;
    key_count++;
  }

  if (key_count == 0) {
    cli_trace(cli, "No keys found");
  }

  cli_ok(cli, "");
}

static void prodtest_backup_ram_erase(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!backup_ram_init()) {
    cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
    return;
  }

  backup_ram_erase();

  cli_ok(cli, "");
}

#if !PRODUCTION

static void prodtest_backup_ram_read(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t key = 0;
  if (!cli_arg_uint32(cli, "key", &key) || key >= 0xFFFF) {
    cli_error_arg(cli, "Expecting key argument in range 0-65534");
    return;
  }

  if (!backup_ram_init()) {
    cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
    return;
  }

  if (!backup_ram_read(key, NULL, 0, NULL)) {
    cli_error(cli, CLI_ERROR, "Key #%d not found", key);
    return;
  }

  uint8_t data[BACKUP_RAM_MAX_KEY_DATA_SIZE];
  size_t data_size = 0;
  if (!backup_ram_read(key, data, sizeof(data), &data_size)) {
    cli_error(cli, CLI_ERROR, "Failed to read the key #%d", key);
    return;
  }

  cli_trace(cli, "Key #%d: %d bytes", key, data_size);

  size_t offset = 0;
  while (offset < data_size) {
    size_t block_size = MIN(16, data_size - offset);
    char block_hex[16 * 2 + 1];
    if (!cstr_encode_hex(block_hex, sizeof(block_hex), &data[offset],
                         block_size)) {
      cli_error(cli, CLI_ERROR_FATAL, "Buffer too small.");
      return;
    }
    cli_trace(cli, "%04x: %s", offset, block_hex);
    offset += block_size;
  }

  cli_ok_hexdata(cli, data, data_size);
}

static void prodtest_backup_ram_write(cli_t* cli) {
  if (cli_arg_count(cli) > 3) {
    cli_error_arg_count(cli);
    return;
  }

  uint32_t key = 0;
  uint32_t type = 0;

  if (!cli_arg_uint32(cli, "key", &key) || key >= 0xFFFF) {
    cli_error_arg(cli, "Expecting key argument in range 0-65534");
    return;
  }

  if (!cli_arg_uint32(cli, "type", &type) || type > 1) {
    cli_error_arg(cli, "Expecting type argument in range 0-1");
    return;
  }

  size_t len = 0;
  uint8_t data[BACKUP_RAM_MAX_KEY_DATA_SIZE];

  if (cli_has_arg(cli, "hex-data")) {
    if (!cli_arg_hex(cli, "hex-data", data, sizeof(data), &len)) {
      if (len == sizeof(data)) {
        cli_error(cli, CLI_ERROR, "Data too long.");
      } else {
        cli_error(cli, CLI_ERROR, "Hexadecimal decoding error.");
      }
      return;
    }
  }

  if (!backup_ram_init()) {
    cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
    return;
  }

  if (!backup_ram_write(key, type, data, len)) {
    cli_error(cli, CLI_ERROR, "Failed to write key #%d", key);
    return;
  }

  if (len == 0) {
    cli_trace(cli, "Key #%d removed", key);
  } else {
    cli_trace(cli, "Key #%d written: %d bytes", key, len);
  }

  cli_ok(cli, "");
}

#endif  // !PRODUCTION

// clang-format off

PRODTEST_CLI_CMD(
   .name = "backup-ram-list",
   .func = prodtest_backup_ram_list,
   .info = "List all key in backup RAM",
   .args = ""
);

PRODTEST_CLI_CMD(
    .name = "backup-ram-erase",
    .func = prodtest_backup_ram_erase,
    .info = "Erase all backup RAM",
    .args = ""
);

#if !PRODUCTION

PRODTEST_CLI_CMD(
   .name = "backup-ram-read",
   .func = prodtest_backup_ram_read,
   .info = "Read from backup RAM",
   .args = "<key>",
);

PRODTEST_CLI_CMD(
   .name = "backup-ram-write",
   .func = prodtest_backup_ram_write,
   .info = "Write to backup RAM",
   .args = "<key> <type> [<hex-data>]",
);

#endif // !PRODUCTION

#endif // #ifdef USE_BACKUP_RAM
