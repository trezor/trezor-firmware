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

#ifdef USE_SBU

#include <trezor_rtl.h>

#include <io/sbu.h>
#include <rtl/cli.h>

static void prodtest_sbu_set(cli_t* cli) {
  uint32_t sbu1 = 0;
  uint32_t sbu2 = 0;

  if (!cli_arg_uint32(cli, "sbu1", &sbu1) || sbu1 > 1) {
    cli_error_arg(cli, "Expecting logical level (0 or 1).");
    return;
  }

  if (!cli_arg_uint32(cli, "sbu2", &sbu2) || sbu2 > 1) {
    cli_error_arg(cli, "Expecting logical level (0 or 1).");
    return;
  }

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Setting SBU1 to %d and SBU2 to %d...", sbu1, sbu2);
  sbu_set(sectrue * sbu1, sectrue * sbu2);

  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "sbu-set",
  .func = prodtest_sbu_set,
  .info = "Set the SBU pins' levels",
  .args = "<sbu1> <sbu2>"
);

#endif  // USE_SBU
