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

#ifdef USE_TAMPER

#include <trezor_rtl.h>

#include <rtl/cli.h>
#include <sys/tamper.h>

static void prodtest_tamper_read(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  bool init_ok = tamper_init();

  if (!init_ok) {
    cli_error(cli, CLI_ERROR, "Cannot initialize tamper driver.");
    return;
  }

  uint8_t val = tamper_external_read();

  cli_ok(cli, "%d", val);
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "tamper-read",
  .func = prodtest_tamper_read,
  .info = "Read current status of external tamper inputs",
  .args = ""
);


#endif
