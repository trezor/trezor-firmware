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

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sys/backup_ram.h>
#include <sys/systick.h>

static void prodtest_backup_ram_write(cli_t* cli) {
  uint32_t soc = 0;

  if (cli_arg_count(cli) == 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (cli_has_arg(cli, "soc") && !cli_arg_uint32(cli, "soc", &soc)) {
    cli_error_arg(cli, "Expecting soc value to store to backup RAM.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (backup_ram_init() != BACKUP_RAM_OK) {
    cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
    return;
  }

  fuel_gauge_backup_storage_t fg_state;

  fg_state.soc = (float)soc;
  fg_state.last_capture_timestamp = systick_cycles();

  backup_ram_store_fuel_gauge_state(&fg_state);

  backup_ram_deinit();

  cli_ok(cli, "");
}

static void prodtest_backup_ram_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (backup_ram_init() != BACKUP_RAM_OK) {
    cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
    return;
  }
  fuel_gauge_backup_storage_t fg_state;
  backup_ram_read_fuel_gauge_state(&fg_state);

  backup_ram_deinit();

  cli_ok(cli, "SOC: %d.%03d", (int)fg_state.soc,
         (int)(fg_state.soc * 1000) % 1000);
}

static void prodtest_backup_ram_erase(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (backup_ram_init() != BACKUP_RAM_OK) {
    cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
    return;
  }

  backup_ram_erase();

  backup_ram_deinit();

  cli_ok(cli, "");
}

static void prodtest_backup_ram_erase_unused(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (backup_ram_init() != BACKUP_RAM_OK) {
    cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
    return;
  }

  backup_ram_erase_unused();

  backup_ram_deinit();

  cli_ok(cli, "");
}

// clang-format off

 PRODTEST_CLI_CMD(
   .name = "backup-ram-write",
   .func = prodtest_backup_ram_write,
   .info = "Write fuel gauge state to backup RAM",
   .args = "<soc>"
 );

PRODTEST_CLI_CMD(
    .name = "backup-ram-read",
    .func = prodtest_backup_ram_read,
    .info = "Read fuel gauge state from backup RAM",
    .args = ""
);

PRODTEST_CLI_CMD(
    .name = "backup-ram-erase",
    .func = prodtest_backup_ram_erase,
    .info = "Erase all backup RAM",
    .args = ""
);

PRODTEST_CLI_CMD(
    .name = "backup-ram-erase-unused",
    .func = prodtest_backup_ram_erase_unused,
    .info = "Erase unused regions of backup RAM",
    .args = ""
);