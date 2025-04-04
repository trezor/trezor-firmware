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

#ifdef USE_POWERCTL

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sys/systick.h>

#include <stdlib.h>
#include "../../../sys/powerctl/stwlc38/stwlc38.h"

static void prodtest_wpc_init(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Initializing the WPC driver...");

  stwlc38_deinit();

  if (!stwlc38_init()) {
    cli_error(cli, CLI_ERROR, "Failed to initialize STWLC38.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_wpc_enable(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Enabling STWLC38...");

  if (!stwlc38_enable(true)) {
    cli_error(cli, CLI_ERROR, "Failed to enable STWLC38.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_wpc_disable(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Disabling STWLC38...");

  if (!stwlc38_enable(false)) {
    cli_error(cli, CLI_ERROR, "Failed to disable STWLC38.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_wpc_vout_enable(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Enabling STWLC38 output...");

  if (!stwlc38_enable_vout(true)) {
    cli_error(cli, CLI_ERROR, "Failed to enable STWLC38 output.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_wpc_vout_disable(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Disabling STWLC38 output...");

  if (!stwlc38_enable_vout(false)) {
    cli_error(cli, CLI_ERROR, "Failed to disable STWLC38 output.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_wpc_report(cli_t* cli) {
  uint32_t count = 1;
  uint32_t period = 1000;

  if (cli_has_arg(cli, "count") && !cli_arg_uint32(cli, "count", &count)) {
    cli_error_arg(cli, "Expecting count of measurements.");
    return;
  }

  if (cli_has_arg(cli, "timeout") && !cli_arg_uint32(cli, "timeout", &period)) {
    cli_error_arg(cli, "Expecting period in milliseconds.");
    return;
  }

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(
      cli,
      "      time       ready vout_ready vrect vout icur tmeas opfreq ntc");

  uint32_t ticks = hal_ticks_ms();

  while (count-- > 0) {
    stwlc38_report_t report;

    if (!stwlc38_get_report(&report)) {
      cli_error(cli, CLI_ERROR, "Failed to get STWLC38 report.");
      return;
    }

    cli_progress(cli, "%09d %d %d %d.%03d %d.%03d %d.%03d %d.%03d %d %d.%03d",
                 ticks, report.ready ? 1 : 0, report.vout_ready ? 1 : 0,
                 (int)report.vrect, (int)abs(report.vrect * 1000) % 1000,
                 (int)report.vout, (int)(report.vout * 1000) % 1000,
                 (int)report.icur, (int)abs(report.icur * 1000) % 1000,
                 (int)report.tmeas, (int)abs(report.tmeas * 1000) % 1000,
                 report.opfreq, (int)report.ntc,
                 (int)abs(report.ntc * 1000) % 1000);

    if (count > 0) {
      do {
        if (cli_aborted(cli)) {
          return;
        }
      } while (!ticks_expired(ticks + period));
      ticks += period;
    }
  }

  cli_ok(cli, "");
}

static void prodtest_wpc_info(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  stwlc38_chip_info_t chip_info;

  cli_trace(cli, "Reading STWLC38 info...");
  if (!stwlc38_read_chip_info(&chip_info)) {
    cli_error(cli, CLI_ERROR, "Cannot read STWLC38 info.");
    return;
  }

  char device_id[sizeof(chip_info.device_id) * 2 + 1];

  if (!cstr_encode_hex(device_id, sizeof(device_id), chip_info.device_id,
                       sizeof(chip_info.device_id))) {
    cli_error(cli, CLI_ERROR_FATAL, "Buffer too small.");
    return;
  }

  cli_trace(cli, "chip_id    0x%d ", chip_info.chip_id);
  cli_trace(cli, "chip_rev   0x%d ", chip_info.chip_rev);
  cli_trace(cli, "cust_id    0x%d ", chip_info.cust_id);
  cli_trace(cli, "rom_id     0x%X ", chip_info.rom_id);
  cli_trace(cli, "patch_id   0x%X ", chip_info.patch_id);
  cli_trace(cli, "cfg_id     0x%X ", chip_info.cfg_id);
  cli_trace(cli, "pe_id      0x%X ", chip_info.pe_id);
  cli_trace(cli, "op_mode    0x%X ", chip_info.op_mode);
  cli_trace(cli, "device_id  %s", device_id);
  cli_trace(cli, "");
  cli_trace(cli, "sys_err              0x%X ", chip_info.sys_err);
  cli_trace(cli, "  core_hard_fault:   0x%X ", chip_info.core_hard_fault);
  cli_trace(cli, "  nvm_ip_err:        0x%X ", chip_info.nvm_ip_err);
  cli_trace(cli, "  nvm_boot_err:      0x%X ", chip_info.nvm_boot_err);
  cli_trace(cli, "  nvm_pe_error:      0x%X ", chip_info.nvm_pe_error);
  cli_trace(cli, "  nvm_config_err:    0x%X ", chip_info.nvm_config_err);
  cli_trace(cli, "  nvm_patch_err:     0x%X ", chip_info.nvm_patch_err);
  cli_trace(cli, "  nvm_prod_info_err: 0x%X ", chip_info.nvm_prod_info_err);

  cli_ok(cli, "");
}

static void prodtest_wpc_update(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Updating STWLC38...");

  stwlc38_chip_info_t chip_info;
  if (!stwlc38_read_chip_info(&chip_info)) {
    cli_error(cli, CLI_ERROR, "Cannot read STWLC38 info.");
    return;
  }

  if (chip_info.chip_rev == STWLC38_CUT_1_2) {
    cli_trace(cli, "STWLC38 chip revision 1.2");
  } else if (chip_info.chip_rev == STWLC38_CUT_1_3) {
    cli_trace(cli, "STWLC38 chip revision 1.3");
  } else {
    cli_error(cli, CLI_ERROR, "Unknown chip revision, update aborted.");
    return;
  }

  // Update STWLC38 firmware and configuration
  uint32_t update_time = systick_ms();
  bool status = stwlc38_patch_and_config();
  update_time = systick_ms() - update_time;

  if (status == false) {
    cli_error(cli, CLI_ERROR, "Failed to update STWLC38.");
    return;
  }

  cli_trace(cli, "WPC update completed {%d ms}", update_time);
  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "wpc-init",
  .func = prodtest_wpc_init,
  .info = "Initialize the WPC driver",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "wpc-enable",
  .func = prodtest_wpc_enable,
  .info = "Enable the WPC chip",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "wpc-disable",
  .func = prodtest_wpc_disable,
  .info = "Disable the WPC chip",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "wpc-out-enable",
  .func = prodtest_wpc_vout_enable,
  .info = "Enable WPC output",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "wpc-out-disable",
  .func = prodtest_wpc_vout_disable,
  .info = "Disable WPC output",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "wpc-report",
  .func = prodtest_wpc_report,
  .info = "Retrieve WPC report",
  .args = "[<count>] [<timeout>]"
);

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

#endif // USE_POWERCTL
