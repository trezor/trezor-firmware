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

#include <gfx/gfx_draw.h>
#include <io/display.h>
#include <rtl/cli.h>

static void prodtest_display_border(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  gfx_clear();

  cli_trace(cli, "Drawing display border...");

  gfx_rect_t r_out = gfx_rect_wh(0, 0, DISPLAY_RESX, DISPLAY_RESY);
  gfx_rect_t r_in = gfx_rect_wh(1, 1, DISPLAY_RESX - 2, DISPLAY_RESY - 2);

  gfx_draw_bar(r_out, COLOR_WHITE);
  gfx_draw_bar(r_in, COLOR_BLACK);

  display_refresh();

  cli_ok(cli, "");
}

static void prodtest_display_bars(cli_t* cli) {
  gfx_clear();

  const char* colors = cli_arg(cli, "colors");
  size_t color_count = strlen(colors);

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  bool invalid_color = false;

  cli_trace(cli, "Drawing %d vertical bars...", color_count);

  for (size_t i = 0; i < color_count; i++) {
    gfx_color_t c = COLOR_BLACK;  // black
    switch (colors[i]) {
      case 'R':
      case 'r':
        c = gfx_color_rgb(255, 0, 0);
        break;
      case 'G':
      case 'g':
        c = gfx_color_rgb(0, 255, 0);
        break;
      case 'B':
      case 'b':
        c = gfx_color_rgb(0, 0, 255);
        break;
      case 'W':
      case 'w':
        c = COLOR_WHITE;
        break;
      default:
        invalid_color = true;
        break;
    }

    int x1 = (DISPLAY_RESX * i) / color_count;
    int x2 = (DISPLAY_RESX * (i + 1)) / color_count;

    gfx_draw_bar(gfx_rect(x1, 0, x2, DISPLAY_RESY), c);
  }

  if (strlen(colors) == 0 || invalid_color) {
    cli_trace(cli, "Not valid color pattern (RGBW characters expected).");
  }

  display_refresh();

  cli_ok(cli, "");
}

static void prodtest_display_set_backlight(cli_t* cli) {
  uint32_t level = 0;

  if (!cli_arg_uint32(cli, "level", &level) || level > 255) {
    cli_error_arg(cli, "Expecting backlig level in range 0-255 (100%%).");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Updating display backlight level to %d...", level);
  display_set_backlight(level);

  cli_ok(cli, "");
}

// clang-format off

PRODTEST_CLI_CMD(
  .name = "display-border",
  .func = prodtest_display_border,
  .info = "Display a border around the screen",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "display-bars",
  .func = prodtest_display_bars,
  .info = "Display vertical bars in different colors",
  .args = "<colors>"
);

PRODTEST_CLI_CMD(
  .name = "display-set-backlight",
  .func = prodtest_display_set_backlight,
  .info = "Set the display backlight level",
  .args = "<level>"
);
