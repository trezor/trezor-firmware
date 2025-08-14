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

#ifdef USE_NRF

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/nrf.h>
#include <rtl/cli.h>
#include <util/flash_otp.h>

#include "common.h"
#include "prodtest_optiga.h"

static void prodtest_nrf_communication(cli_t* cli) {
  cli_trace(cli, "Testing SPI communication...");
  if (!nrf_test_spi_comm()) {
    cli_error(cli, CLI_ERROR, "SPI communication failed.");
    return;
  }

  cli_trace(cli, "Testing UART communication...");
  if (!nrf_test_uart_comm()) {
    cli_error(cli, CLI_ERROR, "UART communication failed.");
    return;
  }

  cli_trace(cli, "Testing reset..");
  if (!nrf_test_reset()) {
    cli_error(cli, CLI_ERROR, "Reset failed.");
    return;
  }

  cli_trace(cli, "Testing GPIO stay in bootloader...");
  if (!nrf_test_gpio_stay_in_bld()) {
    cli_error(cli, CLI_ERROR, "Stay in bootloader GPIO failed.");
    return;
  }

  cli_trace(cli, "Testing GPIO reserved...");
  if (!nrf_test_gpio_reserved()) {
    cli_error(cli, CLI_ERROR, "Reserved GPIO failed.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_nrf_version(cli_t* cli) {
  nrf_info_t info = {0};
  if (!nrf_get_info(&info)) {
    cli_error(cli, CLI_ERROR, "Could not read version.");
    return;
  }

  cli_ok(cli, "%d.%d.%d.%d", info.version_major, info.version_minor,
         info.version_patch, info.version_tweak);
}

static bool prodtest_nrf_update_finalize(uint8_t* data, size_t len) {
  return nrf_update(data, len);
}

static void prodtest_nrf_update(cli_t* cli) {
  binary_update(cli, prodtest_nrf_update_finalize);
}

static void prodtest_nrf_pair(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (OPTIGA_LOCKED_FALSE != get_optiga_locked_status(cli)) {
    cli_error(cli, CLI_ERROR,
              "Optiga is not unlocked. Pairing is not allowed.");
    return;
  }

  if (secfalse != flash_otp_is_locked(FLASH_OTP_BLOCK_DEVICE_SN)) {
    cli_error(
        cli, CLI_ERROR,
        "OTP Device serial number block is locked. Pairing is not allowed.");
  }

  if (nrf_test_pair()) {
    cli_ok(cli, "");
  } else {
    cli_error(cli, CLI_ERROR, "Pairing failed.");
  }
}

static void prodtest_nrf_verify_pairing(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (nrf_authenticate()) {
    cli_ok(cli, "");
  } else {
    cli_error(cli, CLI_ERROR, "Pairing verification failed.");
  }
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "nrf-communication",
  .func = prodtest_nrf_communication,
  .info = "Tests NRF communication and GPIOs",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nrf-version",
  .func = prodtest_nrf_version,
  .info = "Reads NRF firmware version",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "nrf-update",
  .func = prodtest_nrf_update,
  .info = "Update nRF firmware",
  .args = "<phase> <hex-data>"
  );

PRODTEST_CLI_CMD(
  .name = "nrf-pair",
  .func = prodtest_nrf_pair,
  .info = "Pair nRF chip",
  .args = ""
  );

PRODTEST_CLI_CMD(
  .name = "nrf-verify-pairing",
  .func = prodtest_nrf_verify_pairing,
  .info = "Verify nRF pairing",
  .args = ""
);

#endif
