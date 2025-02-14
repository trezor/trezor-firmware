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

#ifdef USE_TROPIC

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sec/tropic.h>

static void prodtest_tropic_get_riscv_fw_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t version[TROPIC_RISCV_FW_SIZE];
  if (!tropic_get_riscv_fw_version(version, sizeof(version))) {
    cli_error(cli, CLI_ERROR, "Unable to get RISCV FW version");
  }

  // Respond with an OK message and version
  cli_ok_hexdata(cli, &version, sizeof(version));
}

static void prodtest_tropic_get_spect_fw_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t version[TROPIC_SPECT_FW_SIZE];
  if (!tropic_get_spect_fw_version(version, sizeof(version))) {
    cli_error(cli, CLI_ERROR, "Unable to get SPECT FW version");
  }

  // Respond with an OK message and version
  cli_ok_hexdata(cli, &version, sizeof(version));
}

static void prodtest_tropic_get_chip_id(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  uint8_t chip_id[TROPIC_CHIP_ID_SIZE];
  if (!tropic_get_chip_id(chip_id, sizeof(chip_id))) {
    cli_error(cli, CLI_ERROR, "Unable to get CHIP ID");
  }

  // Respond with an OK message and chip ID
  cli_ok_hexdata(cli, &chip_id, sizeof(chip_id));
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "tropic-get-riscv-fw-version",
  .func = prodtest_tropic_get_riscv_fw_version,
  .info = "Get RISCV FW version",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-get-spect-fw-version",
  .func = prodtest_tropic_get_spect_fw_version,
  .info = "Get SPECT FW version",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "tropic-get-chip-id",
  .func = prodtest_tropic_get_chip_id,
  .info = "Get Tropic CHIP ID",
  .args = ""
);




#endif
