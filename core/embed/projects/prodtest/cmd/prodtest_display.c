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

#include <rust_ui_prodtest.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <rtl/cli.h>

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

static void prodtest_display_gradient(cli_t* cli) {
  const char* color = cli_arg(cli, "color");

  uint32_t shades = 0;

  if (!cli_arg_uint32(cli, "shades", &shades) || shades < 1 ||
      shades > DISPLAY_RESX) {
    cli_error_arg(cli, "Expecting number of shades in range 1-%d.",
                  DISPLAY_RESX);
    return;
  }

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  if (strlen(color) != 1 || strchr("RGBWrgbw", color[0]) == NULL) {
    cli_error_arg(cli, "Expecting a single color letter (RGBW).");
    return;
  }

  cli_trace(cli, "Drawing %d shades of '%c'...", shades, color[0]);

  uint16_t col_width = DISPLAY_RESX / shades;

  for (uint32_t i = 0; i < shades; i++) {
    // Shade 0 is off (channel value 0), the last column is full intensity
    // (255); with a single shade requested, draw it at full intensity.
    uint8_t level = (shades > 1) ? (i * 255) / (shades - 1) : 255;

    uint8_t r = 0;
    uint8_t g = 0;
    uint8_t b = 0;

    switch (color[0]) {
      case 'r':
      case 'R':
        r = level;
        break;
      case 'g':
      case 'G':
        g = level;
        break;
      case 'b':
      case 'B':
        b = level;
        break;
      case 'w':
      case 'W':
        r = g = b = level;
        break;
    }

    uint16_t x0 = i * col_width;
    // The last column absorbs the remainder of the integer division so the
    // gradient always spans the full screen width.
    uint16_t width = (i == shades - 1) ? (DISPLAY_RESX - x0) : col_width;

    gfx_bitblt_t bb = {
        .dst_x = x0,
        .dst_y = 0,
        .width = width,
        .height = DISPLAY_RESY,
        .src_fg = gfx_color_rgb(r, g, b),
        .src_alpha = 255,
    };

    display_fill(&bb);
  }

  display_refresh();

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

// WIP: luminance measurement — not intended for main branch
static void prodtest_display_luminance(cli_t* cli) {
  const char* color = cli_arg(cli, "color");
  uint32_t level = 0;

  if (color[0] != 'B' && color[0] != 'W') {
    cli_error_arg(cli, "Expecting color 'B' (black) or 'W' (white).");
    return;
  }

  if (!cli_arg_uint32(cli, "level", &level) || level > 255) {
    cli_error_arg(cli, "Expecting backlight level in range 0-255 (100%%).");
    return;
  }

  if (cli_arg_count(cli) > 2) {
    cli_error_arg_count(cli);
    return;
  }

  if (color[0] == 'W') {
    screen_prodtest_bars("W", 1);
  } else {
    screen_prodtest_bars("", 0);
  }

  cli_trace(cli, "Setting backlight to %d...", level);
  display_set_backlight((uint8_t)level);

  cli_ok(cli, "");
}

// State for multi-chunk image receive
static size_t image_offset = 0;
static display_fb_info_t image_fb = {0};

bool prodtest_display_transfer_active(void) { return image_fb.ptr != NULL; }

// Receive raw RGB565 image data in chunks and display it.
//   display-image begin       -- start transfer, returns width/height/stride
//   display-image chunk <hex> -- append hex-encoded pixel bytes
//   display-image end         -- refresh display
//
// To set the backlight level for the image being shown, send a separate
// 'display-set-backlight <level>' command before 'display-image begin'
// (see prodtest_display_set_backlight()).
static void prodtest_display_image(cli_t* cli) {
  if (cli_arg_count(cli) < 1) {
    cli_error_arg_count(cli);
    return;
  }

  const char* phase = cli_arg(cli, "phase");

  if (0 == strcmp(phase, "begin")) {
    if (cli_arg_count(cli) > 1) {
      cli_error_arg_count(cli);
      return;
    }

    if (!display_get_frame_buffer(&image_fb)) {
      cli_error(cli, CLI_ERROR_FATAL, "Cannot get frame buffer");
      return;
    }

    image_offset = 0;
    cli_ok(cli, "width=%d height=%d stride=%d size=%u", DISPLAY_RESX,
           DISPLAY_RESY, (int)image_fb.stride, (unsigned)image_fb.size);

  } else if (0 == strcmp(phase, "chunk")) {
    if (cli_arg_count(cli) < 2) {
      cli_error_arg_count(cli);
      return;
    }

    if (image_fb.ptr == NULL) {
      cli_error(cli, CLI_ERROR_FATAL, "Transfer not started. Use 'begin' first.");
      return;
    }

    size_t chunk_len = 0;
    if (!cli_arg_hex(cli, "hex-data", (uint8_t*)image_fb.ptr + image_offset,
                     image_fb.size - image_offset, &chunk_len)) {
      cli_error_arg(cli, "Expecting hex-encoded pixel data.");
      return;
    }

    image_offset += chunk_len;
    cli_ok(cli, "%u %u", (unsigned)chunk_len, (unsigned)image_offset);

  } else if (0 == strcmp(phase, "end")) {
    if (cli_arg_count(cli) != 1) {
      cli_error_arg_count(cli);
      return;
    }

    display_refresh();
    cli_ok(cli, "displayed %u bytes", (unsigned)image_offset);

    image_offset = 0;
    image_fb.ptr = NULL;

  } else {
    cli_error(cli, CLI_ERROR_FATAL, "Unknown phase '%s' (begin|chunk|end)", phase);
  }
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
  .name = "display-set-backlight",
  .func = prodtest_display_set_backlight,
  .info = "Set the display backlight level",
  .args = "<level>"
);

PRODTEST_CLI_CMD(
  .name = "display-luminance",
  .func = prodtest_display_luminance,
  .info = "Show solid color screen and set backlight level for luminance measurement",
  .args = "<color> <level>"
);

PRODTEST_CLI_CMD(
  .name = "display-gradient",
  .func = prodtest_display_gradient,
  .info = "Display a color gradient (n shades) in vertical columns",
  .args = "<color> <shades>"
);

PRODTEST_CLI_CMD(
  .name = "display-image",
  .func = prodtest_display_image,
  .info = "Show a raw RGB565 image (begin|chunk <hex>|end)",
  .args = "<phase> [<hex-data>]"
);
