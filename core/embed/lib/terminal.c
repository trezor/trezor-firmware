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

#include TREZOR_BOARD

#include <stdarg.h>
#include <stdint.h>
#include <string.h>

#include "display.h"
#include "fonts/fonts.h"
#include "gfx_draw.h"
#include "mini_printf.h"
#include "terminal.h"

#define TERMINAL_COLS (DISPLAY_RESX / 6)
#define TERMINAL_ROWS (DISPLAY_RESY / 8)

static char terminal_fb[TERMINAL_ROWS][TERMINAL_COLS];
static uint16_t terminal_fgcolor = COLOR_WHITE;
static uint16_t terminal_bgcolor = COLOR_BLACK;

// set colors for display_print function
void term_set_color(uint16_t fgcolor, uint16_t bgcolor) {
  terminal_fgcolor = fgcolor;
  terminal_bgcolor = bgcolor;
}

#ifdef NEW_RENDERING

// Font_Bitmap contains 96 (0x20 - 0x7F) 5x7 glyphs
// Each glyph consists of 5 bytes (each byte represents one column)
//
// This function converts the glyph into the format compatible
// with `display_copy_mono1p()` functions.
static uint64_t term_glyph_bits(char ch) {
  union {
    uint64_t u64;
    uint8_t bytes[8];
  } result = {0};

  if (ch > 32 && (uint8_t)ch < 128) {
    const uint8_t *b = &Font_Bitmap[(ch - ' ') * 5];

    for (int y = 0; y < 7; y++) {
      uint8_t mask = 1 << y;
      result.bytes[y] |= ((b[0] & mask) ? 128 : 0) + ((b[1] & mask) ? 64 : 0) +
                         ((b[2] & mask) ? 32 : 0) + ((b[3] & mask) ? 16 : 0) +
                         ((b[4] & mask) ? 8 : 0);
    }
  }
  return result.u64;
}

// Redraws specified rows to the display
static void term_redraw_rows(int start_row, int row_count) {
  uint64_t glyph_bits = 0;
  gfx_bitblt_t bb = {
      .height = 8,
      .width = 6,
      .dst_row = NULL,
      .dst_x = 0,
      .dst_y = 0,
      .dst_stride = 0,

      .src_row = &glyph_bits,
      .src_x = 0,
      .src_y = 0,
      .src_stride = 8,
      .src_fg = gfx_color16_to_color(terminal_fgcolor),
      .src_bg = gfx_color16_to_color(terminal_bgcolor),
  };

  for (int y = start_row; y < start_row + row_count; y++) {
    bb.dst_y = y * 8;
    for (int x = 0; x < TERMINAL_COLS; x++) {
      glyph_bits = term_glyph_bits(terminal_fb[y][x]);
      bb.dst_x = x * 6;
      display_copy_mono1p(&bb);
    }
  }
}
#endif  // NEW_RENDERING

// display text using bitmap font
void term_print(const char *text, int textlen) {
  static uint8_t row = 0, col = 0;

  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }

  // print characters to internal buffer (terminal_fb)
  for (int i = 0; i < textlen; i++) {
    switch (text[i]) {
      case '\r':
        break;
      case '\n':
        row++;
        col = 0;
        break;
      default:
        terminal_fb[row][col] = text[i];
        col++;
        break;
    }

    if (col >= TERMINAL_COLS) {
      col = 0;
      row++;
    }

    if (row >= TERMINAL_ROWS) {
      for (int j = 0; j < TERMINAL_ROWS - 1; j++) {
        memcpy(terminal_fb[j], terminal_fb[j + 1], TERMINAL_COLS);
      }
      memset(terminal_fb[TERMINAL_ROWS - 1], 0, TERMINAL_COLS);
      row = TERMINAL_ROWS - 1;
    }
  }

#ifdef NEW_RENDERING
  term_redraw_rows(0, TERMINAL_ROWS);
  display_refresh();
#else  // NEW RENDERING
  // render buffer to display
  display_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
  for (int i = 0; i < DISPLAY_RESX * DISPLAY_RESY; i++) {
    int x = (i % DISPLAY_RESX);
    int y = (i / DISPLAY_RESX);
    const int j = y % 8;
    y /= 8;
    const int k = x % 6;
    x /= 6;
    char c = 0;
    if (x < TERMINAL_COLS && y < TERMINAL_ROWS) {
      c = terminal_fb[y][x] & 0x7F;
      // char invert = terminal_fb[y][x] & 0x80;
    } else {
      c = ' ';
    }
    if (c < ' ') {
      c = ' ';
    }
    const uint8_t *g = Font_Bitmap + (5 * (c - ' '));
    if (k < 5 && (g[k] & (1 << j))) {
      PIXELDATA(gfx_color16_to_color(terminal_fgcolor));
    } else {
      PIXELDATA(gfx_color16_to_color(terminal_bgcolor));
    }
  }
  display_pixeldata_dirty();
  display_refresh();
#endif
}

// variadic term_print
void term_printf(const char *fmt, ...) {
  if (!strchr(fmt, '%')) {
    term_print(fmt, strlen(fmt));
  } else {
    va_list va;
    va_start(va, fmt);
    char buf[256] = {0};
    int len = mini_vsnprintf(buf, sizeof(buf), fmt, va);
    term_print(buf, len);
    va_end(va);
  }
}
