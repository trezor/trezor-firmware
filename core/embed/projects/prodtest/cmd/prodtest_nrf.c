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

#ifdef USE_BLE

#include <trezor_rtl.h>

#include <io/nrf.h>
#include <rtl/cli.h>

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

  cli_trace(cli, "Testing reboot to bootloader...");
  if (!nrf_test_reboot_to_bootloader()) {
    cli_error(cli, CLI_ERROR, "Reboot to bootloader failed.");
    return;
  }

  cli_trace(cli, "Testing GPIO TRZ ready...");
  if (!nrf_test_gpio_trz_ready()) {
    cli_error(cli, CLI_ERROR, "TRZ ready GPIO failed.");
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

#endif
