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

// State for multi-chunk image receive
static size_t image_offset = 0;
static display_fb_info_t image_fb = {0};

bool prodtest_display_transfer_active(void) { return image_fb.ptr != NULL; }

// Receive raw RGB565 image data in chunks and display it.
//   display-image begin           -- start transfer, returns width/height/stride
//   display-image chunk <hex>     -- append hex-encoded pixel bytes
//   display-image end             -- refresh display
static void prodtest_display_image(cli_t* cli) {
  if (cli_arg_count(cli) < 1) {
    cli_error_arg_count(cli);
    return;
  }

  const char* phase = cli_arg(cli, "phase");

  if (0 == strcmp(phase, "begin")) {
    if (cli_arg_count(cli) != 1) {
      cli_error_arg_count(cli);
      return;
    }

    if (!display_get_frame_buffer(&image_fb)) {
      cli_error(cli, CLI_ERROR, "Cannot get frame buffer");
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
      cli_error(cli, CLI_ERROR, "Transfer not started. Use 'begin' first.");
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
    cli_error(cli, CLI_ERROR, "Unknown phase '%s' (begin|chunk|end)", phase);
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
  .name = "display-image",
  .func = prodtest_display_image,
  .info = "Show a raw RGB565 image (begin|chunk <hex>|end)",
  .args = "<phase> [<hex-data>]"
);
