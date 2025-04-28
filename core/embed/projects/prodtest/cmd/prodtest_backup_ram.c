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

#include <rtl/cli.h>
#include <sys/backup_ram.h>
#include <sys/systick.h>
#include <trezor_rtl.h>

static void prodtest_backup_ram_write(cli_t* cli) {
  uint32_t soc = 0;

  if (cli_arg_count(cli) == 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (cli_has_arg(cli, "soc_percent") &&
      !cli_arg_uint32(cli, "soc_percent", &soc)) {
    cli_error_arg(cli, "Expecting soc value to store to backup RAM.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  backup_ram_status_t status = backup_ram_init();
  if (status != BACKUP_RAM_OK) {
    if (status == BACKUP_RAM_OK_STORAGE_INITIALIZED) {
      cli_trace(cli, "Backup storage had to be initialized");
    } else {
      cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
      return;
    }
  }

  backup_ram_power_manager_data_t pm_data;

  pm_data.soc = ((float)soc / 100);
  pm_data.last_capture_timestamp = systick_cycles();

  status = backup_ram_store_power_manager_data(&pm_data);

  if (status != BACKUP_RAM_OK) {
    cli_error(cli, CLI_ERROR, "Failed to write backup RAM");
    backup_ram_deinit();
    return;
  }

  backup_ram_deinit();

  cli_ok(cli, "");
}

static void prodtest_backup_ram_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  backup_ram_status_t status = backup_ram_init();
  if (status != BACKUP_RAM_OK) {
    if (status == BACKUP_RAM_OK_STORAGE_INITIALIZED) {
      cli_trace(cli, "Backup storage had to be initialized");
    } else {
      cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
      return;
    }
  }

  backup_ram_power_manager_data_t pm_data;
  status = backup_ram_read_power_manager_data(&pm_data);

  if (status != BACKUP_RAM_OK) {
    cli_error(cli, CLI_ERROR, "Failed to read backup RAM");
    backup_ram_deinit();
    return;
  }

  backup_ram_deinit();

  cli_ok(cli, "SOC: %d\%", (int)(pm_data.soc * 100));
}

static void prodtest_backup_ram_erase(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  backup_ram_status_t status = backup_ram_init();
  if (status != BACKUP_RAM_OK) {
    if (status == BACKUP_RAM_OK_STORAGE_INITIALIZED) {
      cli_trace(cli, "Backup storage had to be initialized");
    } else {
      cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
      return;
    }
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

  backup_ram_status_t status = backup_ram_init();
  if (status != BACKUP_RAM_OK) {
    if (status == BACKUP_RAM_OK_STORAGE_INITIALIZED) {
      cli_trace(cli, "Backup storage had to be initialized");
    } else {
      cli_error(cli, CLI_ERROR, "Failed to initialize backup RAM");
      return;
    }
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
   .args = "<soc_percent>"
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