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

#ifdef USE_TOUCH

#include <trezor_rtl.h>

#include <gfx/fonts.h>
#include <gfx/gfx_draw.h>
#include <io/display.h>
#include <io/touch.h>
#include <rtl/cli.h>
#include <sys/systick.h>

const static gfx_text_attr_t bold = {
    .font = FONT_BOLD,
    .fg_color = COLOR_WHITE,
    .bg_color = COLOR_BLACK,
};

static bool ensure_touch_init(cli_t* cli) {
  cli_trace(cli, "Initializing the touch controller...");
  if (sectrue != touch_init()) {
    cli_error(cli, CLI_ERROR, "Cannot initialize touch controller.");
    return false;
  }
  return true;
}

static void prodtest_touch_version(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_touch_init(cli)) {
    return;
  }

  cli_trace(cli, "Reading the touch controller version...");
  uint8_t version = touch_get_version();

  cli_ok(cli, "%d", version);

  touch_deinit();
}

static bool touch_click_timeout(cli_t* cli, uint32_t* event, uint32_t timeout) {
  uint32_t deadline = ticks_timeout(timeout);
  uint32_t ev = 0;

  while (touch_get_event()) {
    if (ticks_expired(deadline) || cli_aborted(cli)) return false;
  }

  cli_trace(cli, "Waiting for a touch for %d ms...", timeout);

  while ((touch_get_event() & TOUCH_START) == 0) {
    if (ticks_expired(deadline) || cli_aborted(cli)) return false;
  }

  while (((ev = touch_get_event()) & TOUCH_END) == 0) {
    if (ticks_expired(deadline) || cli_aborted(cli)) return false;
  }

  while (touch_get_event()) {
    if (ticks_expired(deadline) || cli_aborted(cli)) return false;
  }

  *event = ev;
  return true;
}

static void prodtest_touch_test(cli_t* cli) {
  uint32_t position = 0;
  uint32_t timeout = 0;

  if (!cli_arg_uint32(cli, "position", &position)) {
    cli_error_arg(cli, "Expecting position (0, 1, 2 or 3).");
    return;
  }

  if (!cli_arg_uint32(cli, "timeout", &timeout)) {
    cli_error_arg(cli, "Expecting timeout in milliseconds.");
    return;
  }

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_touch_init(cli)) {
    return;
  }

  const int width = DISPLAY_RESX / 2;
  const int height = DISPLAY_RESY / 2;

  gfx_clear();
  switch (position) {
    case 1:
      gfx_draw_bar(gfx_rect_wh(0, 0, width, height), COLOR_WHITE);
      break;
    case 2:
      gfx_draw_bar(gfx_rect_wh(width, 0, width, height), COLOR_WHITE);
      break;
    case 3:
      gfx_draw_bar(gfx_rect_wh(width, height, width, height), COLOR_WHITE);
      break;
    default:
      gfx_draw_bar(gfx_rect_wh(0, height, width, height), COLOR_WHITE);
      break;
  }

  display_refresh();

  uint32_t event = 0;
  if (touch_click_timeout(cli, &event, timeout)) {
    uint16_t x = touch_unpack_x(event);
    uint16_t y = touch_unpack_y(event);
    cli_ok(cli, "%d %d", x, y);
  } else {
    if (!cli_aborted(cli)) {
      cli_error(cli, CLI_ERROR_TIMEOUT, "");
    }
  }

  touch_deinit();

  gfx_clear();
  display_refresh();
}

static void prodtest_touch_test_custom(cli_t* cli) {
  uint32_t x = 0;
  uint32_t y = 0;
  uint32_t width = 0;
  uint32_t height = 0;
  uint32_t timeout = 0;

  if (!cli_arg_uint32(cli, "x", &x)) {
    cli_error_arg(cli, "Expecting x coordinate.");
    return;
  }

  if (!cli_arg_uint32(cli, "y", &y)) {
    cli_error_arg(cli, "Expecting y coordinate.");
    return;
  }

  if (!cli_arg_uint32(cli, "width", &width)) {
    cli_error_arg(cli, "Expecting rectangle width.");
    return;
  }

  if (!cli_arg_uint32(cli, "height", &height)) {
    cli_error_arg(cli, "Expecting rectangle height.");
    return;
  }

  if (!cli_arg_uint32(cli, "timeout", &timeout)) {
    cli_error_arg(cli, "Expecting timeout in milliseconds.");
    return;
  }

  if (cli_arg_count(cli) > 5) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_touch_init(cli)) {
    return;
  }

  cli_trace(cli, "Drawing a rectangle at [%d, %d] with size [%d x %d]...", x, y,
            width, height);

  gfx_clear();
  gfx_draw_bar(gfx_rect_wh(x, y, width, height), COLOR_WHITE);
  display_refresh();

  uint32_t expire_time = ticks_timeout(timeout);

  cli_trace(cli, "Waiting for a touch for %d ms...", timeout);

  while (true) {
    if (ticks_expired(expire_time)) {
      cli_error(cli, CLI_ERROR_TIMEOUT, "");
      break;
    }

    if (cli_aborted(cli)) {
      break;
    }

    uint32_t touch_event = touch_get_event();
    if (touch_event != 0) {
      uint16_t touch_x = touch_unpack_x(touch_event);
      uint16_t touch_y = touch_unpack_y(touch_event);
      uint32_t ticks = systick_ms();

      if (touch_event & TOUCH_START) {
        cli_progress(cli, "start %d %d %d", touch_x, touch_y, ticks);
      }
      if (touch_event & TOUCH_MOVE) {
        cli_progress(cli, "move %d %d %d", touch_x, touch_y, ticks);
      }
      if (touch_event & TOUCH_END) {
        cli_progress(cli, "end %d %d %d", touch_x, touch_y, ticks);
        cli_ok(cli, "");
        break;
      }
    }
  }

  touch_deinit();

  gfx_clear();
  display_refresh();
}

static void prodtest_touch_test_idle(cli_t* cli) {
  uint32_t timeout = 0;

  if (!cli_arg_uint32(cli, "timeout", &timeout)) {
    cli_error_arg(cli, "Expecting timeout in milliseconds.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  gfx_clear();
  gfx_offset_t pos = gfx_offset(DISPLAY_RESX / 2, DISPLAY_RESY / 2);
  gfx_draw_text(pos, "DON'T TOUCH", -1, &bold, GFX_ALIGN_CENTER);
  display_refresh();

  if (!ensure_touch_init(cli)) {
    return;
  }

  cli_trace(cli, "Don't touch the screen for %d ms...", timeout);

  uint32_t deadline = ticks_timeout(timeout);
  bool activity = false;

  while (!ticks_expired(deadline) && !activity && !cli_aborted(cli)) {
    activity = (sectrue == touch_activity());
  };

  if (cli_aborted(cli)) {
    goto cleanup;
  }

  if (activity) {
    cli_error(cli, CLI_ERROR, "Unexpected activity detected.");
    goto cleanup;
  }

  cli_ok(cli, "");

cleanup:
  touch_deinit();
  gfx_clear();
  display_refresh();
}

static void prodtest_touch_test_power(cli_t* cli) {
  uint32_t timeout = 0;

  if (!cli_arg_uint32(cli, "timeout", &timeout)) {
    cli_error_arg(cli, "Expecting timeout in milliseconds.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  gfx_clear();
  gfx_offset_t pos = gfx_offset(DISPLAY_RESX / 2, DISPLAY_RESY / 2);
  gfx_draw_text(pos, "MEASURING", -1, &bold, GFX_ALIGN_CENTER);
  display_refresh();

  cli_trace(cli, "Setting touch controller power for %d ms...", timeout);

  touch_power_set(true);

  uint32_t deadline = ticks_timeout(timeout);
  while (!ticks_expired(deadline)) {
    systick_delay_ms(1);
    if (cli_aborted(cli)) {
      goto cleanup;
    }
  }

  cli_ok(cli, "");

cleanup:
  touch_power_set(false);
  gfx_clear();
  display_refresh();
}

static void prodtest_touch_test_sensitivity(cli_t* cli) {
  uint32_t sensitivity = 0;

  if (!cli_arg_uint32(cli, "sensitivity", &sensitivity) || sensitivity > 255) {
    cli_error_arg(cli, "Expecting sensitivity level in range 0-255.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  if (!ensure_touch_init(cli)) {
    return;
  }

  cli_trace(cli, "Setting touch controller sensitivity to %d...", sensitivity);
  touch_set_sensitivity(sensitivity);

  cli_trace(cli, "Running touch controller test...");
  cli_trace(cli, "Press CTRL+C for exit.");

  gfx_clear();
  display_refresh();

  for (;;) {
    uint32_t evt = touch_get_event();
    if (evt & TOUCH_START || evt & TOUCH_MOVE) {
      int x = touch_unpack_x(evt);
      int y = touch_unpack_y(evt);
      gfx_clear();
      gfx_draw_bar(gfx_rect_wh(x - 48, y - 48, 96, 96), COLOR_WHITE);
      display_refresh();
    } else if (evt & TOUCH_END) {
      gfx_clear();
      display_refresh();
    }
    if (cli_aborted(cli)) {
      break;
    }
  }

  touch_deinit();

  gfx_clear();
  display_refresh();
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "touch-version",
  .func = prodtest_touch_version,
  .info = "Retrieve the touch controller version",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "touch-test",
  .func = prodtest_touch_test,
  .info = "Test the touch controller",
  .args = "<position> <timeout>"
);

PRODTEST_CLI_CMD(
  .name = "touch-test-custom",
  .func = prodtest_touch_test_custom,
  .info = "Test the touch controller with custom parameters",
  .args = "<x> <y> <width> <height> <timeout>"
);

PRODTEST_CLI_CMD(
  .name = "touch-test-idle",
  .func = prodtest_touch_test_idle,
  .info = "Test the touch controller in idle mode",
  .args = "<timeout>"
);

PRODTEST_CLI_CMD(
  .name = "touch-test-power",
  .func = prodtest_touch_test_power,
  .info = "Test the touch controller's power consumption",
  .args = "<timeout>"
)

PRODTEST_CLI_CMD(
  .name = "touch-test-sensitivity",
  .func = prodtest_touch_test_sensitivity,
  .info = "Test the touch controller sensitivity",
  .args = "<sensitivity>"
)

#endif  // USE_TOUCH
