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

#ifdef USE_POWER_MANAGER

#include <trezor_rtl.h>

#include <io/power_manager.h>
#include <rtl/cli.h>
#include <sys/systick.h>

#include <stdlib.h>
#include "../stwlc38/stwlc38.h"

static void prodtest_wpc_info(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  stwlc38_chip_info_t chip_info;
  pm_status_t status_pm;

  // Deinit power manager to not interfere with STWLC38
  pm_deinit();

  if (!stwlc38_init()) {
    cli_error(cli, CLI_ERROR, "Failed to initialize STWLC38.");
    return;
  }

  cli_trace(cli, "Reading STWLC38 info...");
  if (!stwlc38_read_chip_info(&chip_info)) {
    cli_error(cli, CLI_ERROR, "Cannot read STWLC38 info.");
    goto cleanup;
  }

  char device_id[sizeof(chip_info.device_id) * 2 + 1];

  if (!cstr_encode_hex(device_id, sizeof(device_id), chip_info.device_id,
                       sizeof(chip_info.device_id))) {
    cli_error(cli, CLI_ERROR_FATAL, "Buffer too small.");
    goto cleanup;
  }

  cli_trace(cli, "chip_id    0x%X", chip_info.chip_id);
  cli_trace(cli, "chip_rev   0x%X", chip_info.chip_rev);
  cli_trace(cli, "cust_id    0x%X", chip_info.cust_id);
  cli_trace(cli, "rom_id     0x%X", chip_info.rom_id);

  if (chip_info.patch_id == 0) {
    cli_trace(cli, "patch_id   0x%X (This value may be visible after reset)",
              chip_info.patch_id);
  } else {
    cli_trace(cli, "patch_id   0x%X", chip_info.patch_id);
  }
  cli_trace(cli, "cfg_id     0x%X", chip_info.cfg_id);
  cli_trace(cli, "pe_id      0x%X", chip_info.pe_id);
  cli_trace(cli, "op_mode    0x%X", chip_info.op_mode);
  cli_trace(cli, "device_id  0x%s", device_id);
  cli_trace(cli, "");
  cli_trace(cli, "sys_err              0x%X", chip_info.sys_err);
  cli_trace(cli, "  core_hard_fault:   0x%X", chip_info.core_hard_fault);
  cli_trace(cli, "  nvm_ip_err:        0x%X", chip_info.nvm_ip_err);
  cli_trace(cli, "  nvm_boot_err:      0x%X", chip_info.nvm_boot_err);
  cli_trace(cli, "  nvm_pe_error:      0x%X", chip_info.nvm_pe_error);
  cli_trace(cli, "  nvm_config_err:    0x%X", chip_info.nvm_config_err);
  cli_trace(cli, "  nvm_patch_err:     0x%X", chip_info.nvm_patch_err);
  cli_trace(cli, "  nvm_prod_info_err: 0x%X", chip_info.nvm_prod_info_err);

  cli_ok(cli, "0x%X 0x%X 0x%X 0x%X 0x%X 0x%X 0x%X 0x%X 0x%s 0x%X",
         chip_info.chip_id, chip_info.chip_rev, chip_info.cust_id,
         chip_info.rom_id, chip_info.patch_id, chip_info.cfg_id,
         chip_info.pe_id, chip_info.op_mode, device_id, chip_info.sys_err);

  stwlc38_deinit();

cleanup:

  // initlize power manager again
  status_pm = pm_init(true);
  if (status_pm != PM_OK) {
    cli_error(cli, CLI_ERROR, "Failed to reinitialize power manager.");
    return;
  }
}

static void prodtest_wpc_update(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  pm_status_t status_pm;

  // Deinit power manager to not interfere with STWLC38
  pm_deinit();

  if (!stwlc38_init()) {
    cli_error(cli, CLI_ERROR, "Failed to initialize STWLC38.");
    return;
  }

  cli_trace(cli, "Updating STWLC38...");

  stwlc38_chip_info_t chip_info;
  if (!stwlc38_read_chip_info(&chip_info)) {
    cli_error(cli, CLI_ERROR, "Cannot read STWLC38 info.");
    goto cleanup;
  }

  if (chip_info.chip_rev == STWLC38_CUT_1_2) {
    cli_trace(cli, "STWLC38 chip revision 1.2");
  } else if (chip_info.chip_rev == STWLC38_CUT_1_3) {
    cli_trace(cli, "STWLC38 chip revision 1.3");
  } else {
    cli_error(cli, CLI_ERROR, "Unknown chip revision, update aborted.");
    goto cleanup;
  }

  // Update STWLC38 firmware and configuration
  uint32_t update_time = systick_ms();
  bool status = stwlc38_patch_and_config();
  update_time = systick_ms() - update_time;

  if (status == false) {
    cli_error(cli, CLI_ERROR, "Failed to update STWLC38.");
    goto cleanup;
  }

  cli_trace(cli, "WPC update completed {%d ms}", update_time);

  stwlc38_deinit();

  cli_ok(cli, "");

cleanup:

  // initlize power manager again
  status_pm = pm_init(true);
  if (status_pm != PM_OK) {
    cli_error(cli, CLI_ERROR, "Failed to reinitialize power manager.");
    return;
  }
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "wpc-info",
  .func = prodtest_wpc_info,
  .info = "Retrieve WPC chip information",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "wpc-update",
  .func = prodtest_wpc_update,
  .info = "Update WPC firmware & configuration",
  .args = ""
);

#endif // USE_POWER_MANAGER
