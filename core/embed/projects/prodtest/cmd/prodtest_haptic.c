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
#include <io/touch.h>
#include <rtl/cli.h>
#include <rust_ui_prodtest.h>

#include "prodtest.h"

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

static void prodtest_haptic_btn_press_selector(cli_t* cli) {
  if (cli_arg_count(cli) != 0) {
    cli_error_arg_count(cli);
    return;
  }

  screen_prodtest_haptic_test(false, 0, 0);

  uint16_t x;
  uint16_t y;

  for (;;) {
    uint32_t evt = touch_get_event();

    x = touch_unpack_x(evt);
    y = touch_unpack_y(evt);

    if (evt & TOUCH_START) {
      screen_prodtest_haptic_test(true, x, y);
    } else if (evt & TOUCH_END) {
      screen_prodtest_haptic_test(false, x, y);
    }

    if (cli_aborted(cli)) {
      break;
    }
  }

  prodtest_show_homescreen();

  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "haptic-test",
  .func = prodtest_haptic_test,
  .info = "Test the haptic feedback actuator",
  .args = "<duration>"
);

PRODTEST_CLI_CMD(
  .name = "haptic-btn-press-selector",
  .func = prodtest_haptic_btn_press_selector,
  .info = "Play haptic feedback on each button press - selector",
  .args = ""
);

#endif  // USE_HAPTIC
