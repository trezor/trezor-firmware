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
#include <util/board_capabilities.h>

static void prodtest_boardloader_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Parsing boardloader capabilities...");
  parse_boardloader_capabilities();

  const boardloader_version_t* v = get_boardloader_version();
  cli_ok(cli, "%d.%d.%d", v->version_major, v->version_minor, v->version_patch);
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "boardloader-version",
  .func = prodtest_boardloader_version,
  .info = "Retrieve the boardloader version",
  .args = ""
);
