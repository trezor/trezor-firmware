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
#ifdef USE_HW_REVISION
#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <util/hw_revision.h>

static void prodtest_hw_revision(cli_t* cli) {
  uint8_t rev = hw_revision_get();

  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_ok(cli, "%d", rev);
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "hw-revision",
  .func = prodtest_hw_revision,
  .info = "Read the HW revision",
  .args = ""
);

#endif
