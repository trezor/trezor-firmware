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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <rust_ui_prodtest.h>

#include <io/display.h>
#include <rtl/cli.h>
#include <sys/systick.h>

#include "prodtest.h"

static void prodtest_display_border(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Drawing display border...");

  screen_prodtest_border();

  cli_ok(cli, "");
}

static void prodtest_display_text(cli_t* cli) {
  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  const char* text = cli_arg(cli, "text");

  screen_prodtest_show_text(text, strlen(text));

  cli_ok(cli, "");
}

static void prodtest_display_bars(cli_t* cli) {
  const char* colors = cli_arg(cli, "colors");
  size_t color_count = strlen(colors);

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  bool invalid_color = false;

  cli_trace(cli, "Drawing %d vertical bars...", color_count);

  screen_prodtest_bars(colors, color_count);

  for (size_t i = 0; i < color_count; i++) {
    if (strchr("RGBWrgbw", colors[i]) == NULL) {
      invalid_color = true;
      break;
    }
  }

  if (strlen(colors) == 0 || invalid_color) {
    cli_trace(cli, "Not valid color pattern (RGBW characters expected).");
  }

  display_refresh();

  cli_ok(cli, "");
}

static void prodtest_display_shapes(cli_t* cli) {
  uint32_t angle = 30;

  if (cli_has_arg(cli, "angle") &&
      (!cli_arg_uint32(cli, "angle", &angle) || angle >= 360)) {
    cli_error_arg(cli, "Expecting angle in range 0-359 degrees.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Drawing shapes rotated by %d degrees...", angle);

  uint64_t start = systick_us();
  uint32_t shapes = screen_prodtest_shapes((int16_t)angle);
  uint32_t elapsed = (uint32_t)(systick_us() - start);

  cli_trace(cli, "Frame time %d us, shapes %d us", elapsed, shapes);
  cli_ok(cli, "");
}

static void prodtest_display_shapes_spin(cli_t* cli) {
  uint32_t step = 2;

  if (cli_has_arg(cli, "step") &&
      (!cli_arg_uint32(cli, "step", &step) || step < 1 || step > 90)) {
    cli_error_arg(cli, "Expecting step in range 1-90 degrees.");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Spinning shapes by %d degree steps...", step);

  uint32_t frames = 0;
  uint32_t total = 0;
  uint32_t min = UINT32_MAX;
  uint32_t max = 0;
  uint32_t shapes_total = 0;
  uint32_t shapes_max = 0;

  for (uint32_t angle = 0; angle < 360; angle += step) {
    uint64_t start = systick_us();
    uint32_t shapes = screen_prodtest_shapes((int16_t)angle);
    uint32_t elapsed = (uint32_t)(systick_us() - start);

    frames++;
    total += elapsed;
    min = MIN(min, elapsed);
    max = MAX(max, elapsed);
    shapes_total += shapes;
    shapes_max = MAX(shapes_max, shapes);
  }

  cli_trace(cli, "%d frames, frame time avg %d us, min %d us, max %d us",
            frames, total / frames, min, max);
  cli_trace(cli, "shapes only avg %d us, max %d us", shapes_total / frames,
            shapes_max);
  cli_ok(cli, "");
}

static void prodtest_display_stripes(cli_t* cli) {
  uint32_t count = 240;

  if (cli_has_arg(cli, "frames") &&
      (!cli_arg_uint32(cli, "frames", &count) || count < 1 || count > 10000)) {
    cli_error_arg(cli, "Expecting frames in range 1-10000.");
    return;
  }

  uint32_t speed = 4;

  if (cli_has_arg(cli, "speed") &&
      (!cli_arg_uint32(cli, "speed", &speed) || speed < 1 || speed > 60)) {
    cli_error_arg(cli, "Expecting speed in range 1-60 pixels per frame.");
    return;
  }

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Animating stripes for %d frames at %d px/frame...", count,
            speed);

  uint32_t total = 0;
  uint32_t min = UINT32_MAX;
  uint32_t max = 0;
  uint32_t shapes_total = 0;
  uint32_t shapes_max = 0;

  for (uint32_t frame = 0; frame < count; frame++) {
    uint64_t start = systick_us();
    uint32_t shapes = screen_prodtest_stripes((uint16_t)(frame * speed % 240));
    uint32_t elapsed = (uint32_t)(systick_us() - start);

    total += elapsed;
    min = MIN(min, elapsed);
    max = MAX(max, elapsed);
    shapes_total += shapes;
    shapes_max = MAX(shapes_max, shapes);
  }

  cli_trace(cli, "%d frames, frame time avg %d us, min %d us, max %d us", count,
            total / count, min, max);
  cli_trace(cli, "stripes only avg %d us, max %d us", shapes_total / count,
            shapes_max);
  cli_ok(cli, "");
}

static void prodtest_display_shapes_bench(cli_t* cli) {
  if (cli_arg_count(cli) > 0) {
    cli_error_arg_count(cli);
    return;
  }

  static const char* const labels[] = {
      "background clear wait [us]",
      "draw_pixel [ns]",
      "blend_pixel [ns]",
      "fill_rect 1x1 back to back [ns]",
      "fill_rect 1x1 + pixel [ns]",
      "fill_rect 142x1 + pixel [ns]",
      "fill_rect 142x16 + pixel [ns]",
      "distance evaluation [ns]",
      "filled shape [us]",
      "outlined shape [us]",
      "bordered shape [us]",
      "sharp shape [us]",
      "draw_pixel into RAM [ns]",
      "blend_pixel into RAM [ns]",
  };

  uint32_t results[ARRAY_LENGTH(labels)] = {0};
  screen_prodtest_shapes_bench(results);

#ifndef TREZOR_EMULATOR
  cli_trace(cli, "CPU clock [MHz]: %d", SystemCoreClock / 1000000);
#endif

  for (size_t i = 0; i < ARRAY_LENGTH(labels); i++) {
    cli_trace(cli, "%s: %d", labels[i], results[i]);
  }

  cli_ok(cli, "");
}

static void prodtest_display_set_backlight(cli_t* cli) {
  uint32_t level = 0;

  if (!cli_arg_uint32(cli, "level", &level) || level > 255) {
    cli_error_arg(cli, "Expecting backlight level in range 0-255 (100%%).");
    return;
  }

  if (cli_arg_count(cli) > 1) {
    cli_error_arg_count(cli);
    return;
  }

  cli_trace(cli, "Updating display backlight level to %d...", level);
  display_set_backlight(level);
  prodtest_show_homescreen();

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
  .name = "display-text",
  .func = prodtest_display_text,
  .info = "Display text on the screen",
  .args = "<text>"
);

PRODTEST_CLI_CMD(
  .name = "display-bars",
  .func = prodtest_display_bars,
  .info = "Display vertical bars in different colors",
  .args = "<colors>"
);

PRODTEST_CLI_CMD(
  .name = "display-shapes",
  .func = prodtest_display_shapes,
  .info = "Display rotated rounded rectangles",
  .args = "[<angle>]"
);

PRODTEST_CLI_CMD(
  .name = "display-shapes-spin",
  .func = prodtest_display_shapes_spin,
  .info = "Rotate shapes through 360 degrees and report frame times",
  .args = "[<step>]"
);

PRODTEST_CLI_CMD(
  .name = "display-stripes",
  .func = prodtest_display_stripes,
  .info = "Animate rounded stripes over the screen, report frame times",
  .args = "[<frames>] [<speed>]"
);

PRODTEST_CLI_CMD(
  .name = "display-shapes-bench",
  .func = prodtest_display_shapes_bench,
  .info = "Measure the drawing primitives used by the shapes",
  .args = ""
);

PRODTEST_CLI_CMD(
  .name = "display-set-backlight",
  .func = prodtest_display_set_backlight,
  .info = "Set the display backlight level",
  .args = "<level>"
);
