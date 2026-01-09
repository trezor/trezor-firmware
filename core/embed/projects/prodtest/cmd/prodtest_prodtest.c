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

#include <rust_ui_prodtest.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <util/fwutils.h>

#ifdef USE_BLE
#include "prodtest_ble.h"
#endif

#include "prodtest.h"

#include <version.h>

#define MEM_BUFFER_SIZE (8 * 1024)
static uint8_t mem_buffer[MEM_BUFFER_SIZE];
static size_t mem_buffer_len = 0;

static void prodtest_prodtest_intro(cli_t* cli) {
  cli_trace(cli, "Welcome to Trezor %s Production Test Firmware v%d.%d.%d.%d.",
            MODEL_NAME, VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH,
            VERSION_BUILD);
  cli_trace(cli, "");
  cli_trace(cli, "Type 'help' to view all available commands.");
  cli_trace(cli, "");
}

static void prodtest_prodtest_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_ok(cli, "%d.%d.%d.%d", VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH,
         VERSION_BUILD);
}

static void prodtest_prodtest_wipe(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

#ifdef USE_BLE
  cli_trace(cli, "Erasing BLE bonds...");
  if (!prodtest_ble_erase_bonds(cli)) {
    cli_error(cli, CLI_ERROR, "Failed to erase BLE bonds.");
    return;
  }
#endif

  cli_trace(cli, "Invalidating the production test firmware header...");
  firmware_invalidate_header();

  const char msg[] = "WIPED";
  screen_prodtest_show_text(msg, strlen(msg));

  cli_ok(cli, "");
}

static void prodtest_homescreen(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  prodtest_show_homescreen();

  cli_ok(cli, "");
}

static void prodtest_mem_write(cli_t* cli) {
  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (!cli_arg_hex(cli, "hexdata", mem_buffer, MEM_BUFFER_SIZE,
                   &mem_buffer_len)) {
    cli_error(cli, CLI_ERROR_INVALID_ARG, "Failed to parse hex data.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_mem_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_ok_hexdata(cli, mem_buffer, mem_buffer_len);
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "$intro",
  .func = prodtest_prodtest_intro,
  .info = "",
  .args = "",
);

PRODTEST_CLI_CMD(
  .name = "prodtest-version",
  .func = prodtest_prodtest_version,
  .info = "Retrieve the production test firmware version",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "prodtest-wipe",
  .func = prodtest_prodtest_wipe,
  .info = "Wipe the production test firmware",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "prodtest-homescreen",
  .func = prodtest_homescreen,
  .info = "Shows prodtest homescreen",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "prodtest-mem-write",
  .func = prodtest_mem_write,
  .info = "Write data into RAM buffer",
  .args = "<hexdata>"
);

PRODTEST_CLI_CMD(
  .name = "prodtest-mem-read",
  .func = prodtest_mem_read,
  .info = "Read data from RAM buffer",
  .args = ""
);
