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

#ifdef USE_HAPTIC

#include <trezor_rtl.h>

#include <io/haptic.h>
#include <rtl/cli.h>

static void prodtest_haptic_test(cli_t* cli) {
  uint32_t duration = 0;  // ms

  if (!cli_arg_uint32(cli, "duration", &duration)) {
    cli_error_arg(cli, "Expecting time in milliseconds.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (!haptic_init()) {
    cli_error(cli, CLI_ERROR, "Haptic driver initialization failed.");
    return;
  }

  haptic_play(HAPTIC_BUTTON_PRESS);

  cli_trace(cli, "Running haptic feedback test for %d ms...", duration);
  if (!haptic_test(duration)) {
    cli_error(cli, CLI_ERROR, "Haptic feedback test failed.");
    return;
  }

  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "haptic-test",
  .func = prodtest_haptic_test,
  .info = "Test the haptic feedback actuator",
  .args = "<duration>"
);

#endif  // USE_HAPTIC
