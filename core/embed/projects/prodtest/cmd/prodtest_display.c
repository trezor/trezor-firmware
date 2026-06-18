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
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <rtl/cli.h>
#include <sys/systick.h>

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#include "prodtest.h"
#include "prodtest_display_images.h"

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

// Returns true if input received, false on timeout or abort.
static bool slideshow_wait_advance(cli_t* cli, uint32_t timeout_ms) {
  uint32_t deadline = ticks_timeout(timeout_ms);

#ifdef USE_TOUCH
  // Drain stale events before waiting for fresh input.
  while (touch_get_event() != 0) {
    if (cli_aborted(cli)) return false;
  }
#endif

  for (;;) {
    if (timeout_ms != 0 && ticks_expired(deadline)) return false;
    if (cli_aborted(cli)) return false;

    // Poll for terminal input. The USB VCP interrupt may not fire during a
    // command handler, so we read directly instead of relying on cli_abort.
    {
      char buf[1];
      if (cli->read(cli->callback_context, buf, sizeof(buf)) > 0) {
        cli_abort(cli);
        return false;
      }
    }

#ifdef USE_TOUCH
    if (touch_get_event() & TOUCH_START) return true;
#endif

#ifdef USE_BUTTON
    {
      button_event_t btn = {0};
      if (button_get_event(&btn) && btn.event_type == BTN_EVENT_DOWN) {
        return true;
      }
    }
#endif
  }
}

static void slideshow_display_image(display_fb_info_t* fb,
                                     const prodtest_image_t* img) {
  int w = img->width < DISPLAY_RESX ? img->width : DISPLAY_RESX;
  int h = img->height < DISPLAY_RESY ? img->height : DISPLAY_RESY;
  for (int y = 0; y < h; y++) {
    const uint8_t* src_row = img->data + (size_t)y * img->width * 2;
    uint8_t* dst_row = (uint8_t*)fb->ptr + (size_t)y * fb->stride;
    memcpy(dst_row, src_row, (size_t)w * 2);
  }
}

static void prodtest_display_slideshow(cli_t* cli) {
  uint32_t timeout_ms = 0;
  uint32_t backlight = 0;
  bool loop = false;
  bool timeout_set = false;
  bool backlight_set = false;

  for (int arg_idx = 0; arg_idx < (int)cli_arg_count(cli); arg_idx++) {
    const char* arg = cli_nth_arg(cli, arg_idx);
    if (strcmp(arg, "--loop") == 0) {
      loop = true;
    } else if (strcmp(arg, "--backlight") == 0) {
      arg_idx++;
      if (arg_idx >= (int)cli_arg_count(cli) ||
          !cstr_parse_uint32(cli_nth_arg(cli, arg_idx), 10, &backlight) ||
          backlight > 255) {
        cli_error_arg(cli, "Expecting backlight level (0-255) after --backlight.");
        return;
      }
      backlight_set = true;
    } else if (!timeout_set) {
      if (!cstr_parse_uint32(arg, 10, &timeout_ms)) {
        cli_error_arg(cli, "Expecting per-image timeout in ms (0 = wait for input).");
        return;
      }
      timeout_set = true;
    } else {
      cli_error_arg(cli, "Unknown argument: %s.", arg);
      return;
    }
  }

  if (backlight_set) {
    display_set_backlight(backlight);
  }

  bool first_display = true;
  bool done = false;

  if (loop) {
    cli_trace(cli, "Send any input from the terminal to exit the loop.");
  }

  do {
    for (int i = 0; i < PRODTEST_IMAGES_COUNT; i++) {
      if (!first_display) {
        // Overwrite previous list block in place. "\033[NA" moves cursor up N
        // rows, "\r" goes to col 0, "\033[J" clears to end of screen (including
        // the "# " artifact on this trace line). The trailing "\r\n" from
        // cli_trace then lands the cursor at the blank-line row.
        cli_trace(cli, "\033[%dA\r\033[J", PRODTEST_IMAGES_COUNT + 2);
      }
      first_display = false;

      cli_trace(cli, "");
      for (int j = 0; j < PRODTEST_IMAGES_COUNT; j++) {
        if (j == i) {
          cli_trace(cli, " >> %2d. %s  [current]", j + 1, PRODTEST_IMAGES[j].name);
        } else {
          cli_trace(cli, "    %2d. %s", j + 1, PRODTEST_IMAGES[j].name);
        }
      }

      display_fb_info_t fb = {0};
      if (!display_get_frame_buffer(&fb)) {
        cli_error(cli, CLI_ERROR, "Cannot get frame buffer.");
        return;
      }

      slideshow_display_image(&fb, &PRODTEST_IMAGES[i]);
      display_refresh();

      if (!slideshow_wait_advance(cli, timeout_ms)) {
        if (cli_aborted(cli)) {
          // Terminal input is a clean exit in all modes.
          done = true;
          break;
        }
      }
    }
  } while (loop && !done);

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

PRODTEST_CLI_CMD(
  .name = "display-slideshow",
  .func = prodtest_display_slideshow,
  .info = "Show display test images one by one (advance on touch/button)",
  .args = "[<timeout_ms>] [--loop] [--backlight <level>]"
);
