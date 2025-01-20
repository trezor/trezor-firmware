
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

#include <util/cli.h>

#include <io/display.h>
#include <io/touch.h>
#include <sys/systick.h>

static void clicmd_touch_test_custom(cli_t* cli) {
  int x = 0;
  int y = 0;
  int width = 0;
  int height = 0;
  int timeout = 0;

  if (!slice_parse_int32(args_get(0), &x) || x < 0) {
    cli_write(cli, CLI_ERROR_PARAM, "x");
    return;
  }

  if (!slice_parse_int32(args_get(1), &y) || y < 0) {
    cli_write(cli, CLI_ERROR_PARAM, "y");
    return;
  }

  if (!slice_parse_int32(args_get(2), &width)) {
    cli_write(cli, CLI_ERROR_PARAM, "width");
    return;
  }

  if (!slice_parse_int32(args_get(3), &height)) {
    cli_write(cli, CLI_ERROR_PARAM, "height");
    return;
  }

  if (!slice_parse_int32(args_get(4), &timeout)) {
    cli_write(cli, CLI_ERROR_PARAM, "timeout");
    return;
  }

  if (!touch_init()) {
    cli_trace("Cannot initialize touch driver");
    cli_write(cli, CLI_ERROR, "setup");
    return;
  }

  gfx_clear();
  gfx_draw_bar(gfx_rect_wh(x, y, width, height), COLOR_WHITE);
  display_refresh();

  uint32_t expire_time = ticks_timeout(timeout);

  while (true) {
    if (ticks_elapsed(expire_time)) {
      cli_error(cli, CLI_ERROR, "timeout");
      break;
    }

    if (cli_aborted(cli)) {
      break;
    }

    uint32_t touch_event = touch_get_event();
    if (touch_event != 0) {
      uint16_t touch_x = touch_unpack_x(touch_event);
      uint16_t touch_y = touch_unpack_y(touch_event);
      uint32_t ticks = systick_get_ms();

      if (touch_event & TOUCH_START) {
        cli_write(cli, CLI_PROGRESS, "start %d %d %d", touch_x, touch_y, ticks);
      }
      if (touch_event & TOUCH_MOVE) {
        cli_write(cli, CLI_PROGRESS, "move %d %d %d", touch_x, touch_y, ticks);
      }
      if (touch_event & TOUCH_END) {
        cli_write(cli, CLI_PROGRESS, "end %d %d %d", touch_x, touch_y, ticks);
        cli_write(cli, CLI_OK, "");
        break;
      }
    }
  }

  touch_deinit();

  gfx_clear();
  display_refresh();
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "touch-test-custom", 
  .func = clicmd_touch_test_custom,
  .info = "Test touch driver with custom parameters"
);
