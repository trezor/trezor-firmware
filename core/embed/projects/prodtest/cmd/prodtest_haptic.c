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
#include <sys/systick.h>

static void prodtest_haptic_test(cli_t* cli) {
  uint32_t duration_ms = 0;  // ms

  ts_t status;

  if (!cli_arg_uint32(cli, "duration", &duration_ms)) {
    cli_error_arg(cli, "Expecting time in milliseconds.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  status = haptic_init();
  if (ts_error(status)) {
    cli_error(cli, CLI_ERROR, "Haptic driver initialization failed.");
    return;
  }

  cli_trace(cli, "Running haptic feedback test for %d ms...", duration_ms);

  status = haptic_play_custom(100, duration_ms);
  if (ts_error(status)) {
    cli_error(cli, CLI_ERROR, "Haptic feedback test failed.");
    return;
  }

  cli_ok(cli, "");
}

static void prodtest_haptic_test_prc(cli_t* cli) {
  uint32_t haptic_amp_perc = 0;

  if (cli_arg_count(cli) != 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (!cli_arg_uint32(cli, "amplitude", &haptic_amp_perc)) {
    cli_error_arg(cli, "Expecting amplitude percentage (0-100).");
    return;
  }

  if (haptic_amp_perc > 100) {
    cli_error_arg(cli, "Amplitude percentage must be in range 0-100.");
    return;
  }

  cli_trace(cli, "Starting haptic feedback test with amplitude %d%%...",
            haptic_amp_perc);

  while (true) {
    if (cli_aborted(cli)) {
      cli_ok(cli, "Haptic drive test aborted.");
      return;
    }

    haptic_play_custom(haptic_amp_perc, 100);

    systick_delay_ms(50);
  }
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "haptic-test",
  .func = prodtest_haptic_test,
  .info = "Test the haptic feedback actuator",
  .args = "<duration>"
);

PRODTEST_CLI_CMD(
  .name = "haptic-test-prc",
  .func = prodtest_haptic_test_prc,
  .info = "Test the haptic feedback actuator with given amplitude percentage",
  .args = "<amplitude>"
)

#endif  // USE_HAPTIC
