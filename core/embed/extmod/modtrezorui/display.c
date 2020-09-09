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

#define _GNU_SOURCE

#include "qr-code-generator/qrcodegen.h"

#include "uzlib.h"

#include "common.h"
#include "display.h"

#include "font_bitmap.h"

#if TREZOR_MODEL == T

#ifdef TREZOR_FONT_NORMAL_ENABLE
#include "font_roboto_regular_20.h"
#define FONT_NORMAL_DATA Font_Roboto_Regular_20
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
#include "font_roboto_bold_20.h"
#define FONT_BOLD_DATA Font_Roboto_Bold_20
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
#include "font_robotomono_regular_20.h"
#define FONT_MONO_DATA Font_RobotoMono_Regular_20
#endif

#elif TREZOR_MODEL == 1

#ifdef TREZOR_FONT_NORMAL_ENABLE
#include "font_pixeloperator_regular_8.h"
#define FONT_NORMAL_DATA Font_PixelOperator_Regular_8
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
#include "font_pixeloperator_bold_8.h"
#define FONT_BOLD_DATA Font_PixelOperator_Bold_8
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
#include "font_pixeloperatormono_regular_8.h"
#define FONT_MONO_DATA Font_PixelOperatorMono_Regular_8
#endif

#else
#error Unknown Trezor model
#endif

#include <stdarg.h>
#include <string.h>

#include "memzero.h"

static int DISPLAY_BACKLIGHT = -1;
static int DISPLAY_ORIENTATION = -1;

static struct { int x, y; } DISPLAY_OFFSET;

#ifdef TREZOR_EMULATOR
#include "display-unix.h"
#else
#if TREZOR_MODEL == T
#include "display-stm32_T.h"
#elif TREZOR_MODEL == 1
#include "display-stm32_1.h"
#else
#error Unknown Trezor model
#endif
#endif

// common display functions

static inline uint16_t interpolate_color(uint16_t color0, uint16_t color1,
                                         uint8_t step) {
  uint8_t cr = 0, cg = 0, cb = 0;
  cr = (((color0 & 0xF800) >> 11) * step +
        ((color1 & 0xF800) >> 11) * (15 - step)) /
       15;
  cg = (((color0 & 0x07E0) >> 5) * step +
        ((color1 & 0x07E0) >> 5) * (15 - step)) /
       15;
  cb = ((color0 & 0x001F) * step + (color1 & 0x001F) * (15 - step)) / 15;
  return (cr << 11) | (cg << 5) | cb;
}

static inline void set_color_table(uint16_t colortable[16], uint16_t fgcolor,
                                   uint16_t bgcolor) {
  for (int i = 0; i < 16; i++) {
    colortable[i] = interpolate_color(fgcolor, bgcolor, i);
  }
}

static inline void clamp_coords(int x, int y, int w, int h, int *x0, int *y0,
                                int *x1, int *y1) {
  *x0 = MAX(x, 0);
  *y0 = MAX(y, 0);
  *x1 = MIN(x + w - 1, DISPLAY_RESX - 1);
  *y1 = MIN(y + h - 1, DISPLAY_RESY - 1);
}

void display_clear(void) {
  const int saved_orientation = DISPLAY_ORIENTATION;
  // set MADCTL first so that we can set the window correctly next
  display_orientation(0);
  // address the complete frame memory
  display_set_window(0, 0, MAX_DISPLAY_RESX - 1, MAX_DISPLAY_RESY - 1);
  for (uint32_t i = 0; i < MAX_DISPLAY_RESX * MAX_DISPLAY_RESY; i++) {
    // 2 bytes per pixel because we're using RGB 5-6-5 format
    PIXELDATA(0x0000);
  }
  // go back to restricted window
  display_set_window(0, 0, DISPLAY_RESX - 1, DISPLAY_RESY - 1);
  // if valid, go back to the saved orientation
  display_orientation(saved_orientation);
}

void display_bar(int x, int y, int w, int h, uint16_t c) {
  x += DISPLAY_OFFSET.x;
  y += DISPLAY_OFFSET.y;
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
  clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
  display_set_window(x0, y0, x1, y1);
  for (int i = 0; i < (x1 - x0 + 1) * (y1 - y0 + 1); i++) {
    PIXELDATA(c);
  }
}

#define CORNER_RADIUS 16

static const uint8_t cornertable[CORNER_RADIUS * CORNER_RADIUS] = {
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  5,  9,  12, 14, 15, 0,  0,  0,
    0,  0,  0,  0,  0,  3,  9,  15, 15, 15, 15, 15, 15, 0,  0,  0,  0,  0,  0,
    0,  8,  15, 15, 15, 15, 15, 15, 15, 15, 0,  0,  0,  0,  0,  3,  12, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 0,  0,  0,  0,  3,  14, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 0,  0,  0,  3,  14, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 0,  0,  0,  12, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 0,  0,
    8,  15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 0,  3,  15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 0,  9,  15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 1,  15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 5,  15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 9,  15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 12,
    15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 14, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15,
    15, 15, 15, 15, 15, 15, 15, 15, 15,
};

void display_bar_radius(int x, int y, int w, int h, uint16_t c, uint16_t b,
                        uint8_t r) {
  if (r != 2 && r != 4 && r != 8 && r != 16) {
    return;
  } else {
    r = 16 / r;
  }
  uint16_t colortable[16] = {0};
  set_color_table(colortable, c, b);
  x += DISPLAY_OFFSET.x;
  y += DISPLAY_OFFSET.y;
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
  clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
  display_set_window(x0, y0, x1, y1);
  for (int j = y0; j <= y1; j++) {
    for (int i = x0; i <= x1; i++) {
      int rx = i - x;
      int ry = j - y;
      if (rx < CORNER_RADIUS / r && ry < CORNER_RADIUS / r) {
        uint8_t c = cornertable[rx * r + ry * r * CORNER_RADIUS];
        PIXELDATA(colortable[c]);
      } else if (rx < CORNER_RADIUS / r && ry >= h - CORNER_RADIUS / r) {
        uint8_t c = cornertable[rx * r + (h - 1 - ry) * r * CORNER_RADIUS];
        PIXELDATA(colortable[c]);
      } else if (rx >= w - CORNER_RADIUS / r && ry < CORNER_RADIUS / r) {
        uint8_t c = cornertable[(w - 1 - rx) * r + ry * r * CORNER_RADIUS];
        PIXELDATA(colortable[c]);
      } else if (rx >= w - CORNER_RADIUS / r && ry >= h - CORNER_RADIUS / r) {
        uint8_t c =
            cornertable[(w - 1 - rx) * r + (h - 1 - ry) * r * CORNER_RADIUS];
        PIXELDATA(colortable[c]);
      } else {
        PIXELDATA(c);
      }
    }
  }
}

#define UZLIB_WINDOW_SIZE (1 << 10)

static void uzlib_prepare(struct uzlib_uncomp *decomp, uint8_t *window,
                          const void *src, uint32_t srcsize, void *dest,
                          uint32_t destsize) {
  memzero(decomp, sizeof(struct uzlib_uncomp));
  if (window) {
    memzero(window, UZLIB_WINDOW_SIZE);
  }
  memzero(dest, destsize);
  decomp->source = (const uint8_t *)src;
  decomp->source_limit = decomp->source + srcsize;
  decomp->dest = (uint8_t *)dest;
  decomp->dest_limit = decomp->dest + destsize;
  uzlib_uncompress_init(decomp, window, window ? UZLIB_WINDOW_SIZE : 0);
}

void display_image(int x, int y, int w, int h, const void *data,
                   uint32_t datalen) {
#if TREZOR_MODEL == T
  x += DISPLAY_OFFSET.x;
  y += DISPLAY_OFFSET.y;
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
  clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
  display_set_window(x0, y0, x1, y1);
  x0 -= x;
  x1 -= x;
  y0 -= y;
  y1 -= y;

  struct uzlib_uncomp decomp = {0};
  uint8_t decomp_window[UZLIB_WINDOW_SIZE] = {0};
  uint8_t decomp_out[2] = {0};
  uzlib_prepare(&decomp, decomp_window, data, datalen, decomp_out,
                sizeof(decomp_out));

  for (uint32_t pos = 0; pos < w * h; pos++) {
    int st = uzlib_uncompress(&decomp);
    if (st == TINF_DONE) break;  // all OK
    if (st < 0) break;           // error
    const int px = pos % w;
    const int py = pos / w;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
      PIXELDATA((decomp_out[0] << 8) | decomp_out[1]);
    }
    decomp.dest = (uint8_t *)&decomp_out;
  }
#endif
}

#define AVATAR_BORDER_SIZE 4
#define AVATAR_BORDER_LOW                        \
  (AVATAR_IMAGE_SIZE / 2 - AVATAR_BORDER_SIZE) * \
      (AVATAR_IMAGE_SIZE / 2 - AVATAR_BORDER_SIZE)
#define AVATAR_BORDER_HIGH (AVATAR_IMAGE_SIZE / 2) * (AVATAR_IMAGE_SIZE / 2)
#define AVATAR_ANTIALIAS 1

void display_avatar(int x, int y, const void *data, uint32_t datalen,
                    uint16_t fgcolor, uint16_t bgcolor) {
#if TREZOR_MODEL == T
  x += DISPLAY_OFFSET.x;
  y += DISPLAY_OFFSET.y;
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
  clamp_coords(x, y, AVATAR_IMAGE_SIZE, AVATAR_IMAGE_SIZE, &x0, &y0, &x1, &y1);
  display_set_window(x0, y0, x1, y1);
  x0 -= x;
  x1 -= x;
  y0 -= y;
  y1 -= y;

  struct uzlib_uncomp decomp = {0};
  uint8_t decomp_window[UZLIB_WINDOW_SIZE] = {0};
  uint8_t decomp_out[2] = {0};
  uzlib_prepare(&decomp, decomp_window, data, datalen, decomp_out,
                sizeof(decomp_out));

  for (uint32_t pos = 0; pos < AVATAR_IMAGE_SIZE * AVATAR_IMAGE_SIZE; pos++) {
    int st = uzlib_uncompress(&decomp);
    if (st == TINF_DONE) break;  // all OK
    if (st < 0) break;           // error
    const int px = pos % AVATAR_IMAGE_SIZE;
    const int py = pos / AVATAR_IMAGE_SIZE;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
      int d = (px - AVATAR_IMAGE_SIZE / 2) * (px - AVATAR_IMAGE_SIZE / 2) +
              (py - AVATAR_IMAGE_SIZE / 2) * (py - AVATAR_IMAGE_SIZE / 2);
      // inside border area
      if (d < AVATAR_BORDER_LOW) {
        PIXELDATA((decomp_out[0] << 8) | decomp_out[1]);
      } else
          // outside border area
          if (d > AVATAR_BORDER_HIGH) {
        PIXELDATA(bgcolor);
        // border area
      } else {
#if AVATAR_ANTIALIAS
        d = 31 * (d - AVATAR_BORDER_LOW) /
            (AVATAR_BORDER_HIGH - AVATAR_BORDER_LOW);
        uint16_t c = 0;
        if (d >= 16) {
          c = interpolate_color(bgcolor, fgcolor, d - 16);
        } else {
          c = interpolate_color(fgcolor, (decomp_out[0] << 8) | decomp_out[1],
                                d);
        }
        PIXELDATA(c);
#else
        PIXELDATA(fgcolor);
#endif
      }
    }
    decomp.dest = (uint8_t *)&decomp_out;
  }
#endif
}

void display_icon(int x, int y, int w, int h, const void *data,
                  uint32_t datalen, uint16_t fgcolor, uint16_t bgcolor) {
  x += DISPLAY_OFFSET.x;
  y += DISPLAY_OFFSET.y;
  x &= ~1;  // cannot draw at odd coordinate
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
  clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
  display_set_window(x0, y0, x1, y1);
  x0 -= x;
  x1 -= x;
  y0 -= y;
  y1 -= y;

  uint16_t colortable[16] = {0};
  set_color_table(colortable, fgcolor, bgcolor);

  struct uzlib_uncomp decomp = {0};
  uint8_t decomp_window[UZLIB_WINDOW_SIZE] = {0};
  uint8_t decomp_out = 0;
  uzlib_prepare(&decomp, decomp_window, data, datalen, &decomp_out,
                sizeof(decomp_out));

  for (uint32_t pos = 0; pos < w * h / 2; pos++) {
    int st = uzlib_uncompress(&decomp);
    if (st == TINF_DONE) break;  // all OK
    if (st < 0) break;           // error
    const int px = pos % w;
    const int py = pos / w;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
      PIXELDATA(colortable[decomp_out >> 4]);
      PIXELDATA(colortable[decomp_out & 0x0F]);
    }
    decomp.dest = (uint8_t *)&decomp_out;
  }
}

// see docs/misc/toif.md for defintion of the TOIF format
bool display_toif_info(const uint8_t *data, uint32_t len, uint16_t *out_w,
                       uint16_t *out_h, bool *out_grayscale) {
  if (len < 12 || memcmp(data, "TOI", 3) != 0) {
    return false;
  }
  bool grayscale = false;
  if (data[3] == 'f') {
    grayscale = false;
  } else if (data[3] == 'g') {
    grayscale = true;
  } else {
    return false;
  }

  uint16_t w = *(uint16_t *)(data + 4);
  uint16_t h = *(uint16_t *)(data + 6);

  uint32_t datalen = *(uint32_t *)(data + 8);
  if (datalen != len - 12) {
    return false;
  }

  if (out_w != NULL && out_h != NULL && out_grayscale != NULL) {
    *out_w = w;
    *out_h = h;
    *out_grayscale = grayscale;
  }
  return true;
}

#if TREZOR_MODEL == T
#include "loader.h"
#endif

void display_loader(uint16_t progress, bool indeterminate, int yoffset,
                    uint16_t fgcolor, uint16_t bgcolor, const uint8_t *icon,
                    uint32_t iconlen, uint16_t iconfgcolor) {
#if TREZOR_MODEL == T
  uint16_t colortable[16] = {0}, iconcolortable[16] = {0};
  set_color_table(colortable, fgcolor, bgcolor);
  if (icon) {
    set_color_table(iconcolortable, iconfgcolor, bgcolor);
  }
  if ((DISPLAY_RESY / 2 - img_loader_size + yoffset < 0) ||
      (DISPLAY_RESY / 2 + img_loader_size - 1 + yoffset >= DISPLAY_RESY)) {
    return;
  }
  display_set_window(DISPLAY_RESX / 2 - img_loader_size,
                     DISPLAY_RESY / 2 - img_loader_size + yoffset,
                     DISPLAY_RESX / 2 + img_loader_size - 1,
                     DISPLAY_RESY / 2 + img_loader_size - 1 + yoffset);
  if (icon && memcmp(icon, "TOIg", 4) == 0 &&
      LOADER_ICON_SIZE == *(uint16_t *)(icon + 4) &&
      LOADER_ICON_SIZE == *(uint16_t *)(icon + 6) &&
      iconlen == 12 + *(uint32_t *)(icon + 8)) {
    uint8_t icondata[(LOADER_ICON_SIZE * LOADER_ICON_SIZE) / 2] = {0};
    memzero(&icondata, sizeof(icondata));
    struct uzlib_uncomp decomp = {0};
    uzlib_prepare(&decomp, NULL, icon + 12, iconlen - 12, icondata,
                  sizeof(icondata));
    uzlib_uncompress(&decomp);
    icon = icondata;
  } else {
    icon = NULL;
  }
  for (int y = 0; y < img_loader_size * 2; y++) {
    for (int x = 0; x < img_loader_size * 2; x++) {
      int mx = x, my = y;
      uint16_t a = 0;
      if ((mx >= img_loader_size) && (my >= img_loader_size)) {
        mx = img_loader_size * 2 - 1 - x;
        my = img_loader_size * 2 - 1 - y;
        a = 499 - (img_loader[my][mx] >> 8);
      } else if (mx >= img_loader_size) {
        mx = img_loader_size * 2 - 1 - x;
        a = img_loader[my][mx] >> 8;
      } else if (my >= img_loader_size) {
        my = img_loader_size * 2 - 1 - y;
        a = 500 + (img_loader[my][mx] >> 8);
      } else {
        a = 999 - (img_loader[my][mx] >> 8);
      }
// inside of circle - draw glyph
#define LOADER_ICON_CORNER_CUT 2
#define LOADER_INDETERMINATE_WIDTH 100
      if (icon &&
          mx + my > (((LOADER_ICON_SIZE / 2) + LOADER_ICON_CORNER_CUT) * 2) &&
          mx >= img_loader_size - (LOADER_ICON_SIZE / 2) &&
          my >= img_loader_size - (LOADER_ICON_SIZE / 2)) {
        int i =
            (x - (img_loader_size - (LOADER_ICON_SIZE / 2))) +
            (y - (img_loader_size - (LOADER_ICON_SIZE / 2))) * LOADER_ICON_SIZE;
        uint8_t c = 0;
        if (i % 2) {
          c = icon[i / 2] & 0x0F;
        } else {
          c = (icon[i / 2] & 0xF0) >> 4;
        }
        PIXELDATA(iconcolortable[c]);
      } else {
        uint8_t c = 0;
        if (indeterminate) {
          uint16_t diff =
              (progress > a) ? (progress - a) : (1000 + progress - a);
          if (diff < LOADER_INDETERMINATE_WIDTH ||
              diff > 1000 - LOADER_INDETERMINATE_WIDTH) {
            c = (img_loader[my][mx] & 0x00F0) >> 4;
          } else {
            c = img_loader[my][mx] & 0x000F;
          }
        } else {
          if (progress > a) {
            c = (img_loader[my][mx] & 0x00F0) >> 4;
          } else {
            c = img_loader[my][mx] & 0x000F;
          }
        }
        PIXELDATA(colortable[c]);
      }
    }
  }
#endif
}

#ifndef TREZOR_PRINT_DISABLE

#define DISPLAY_PRINT_COLS (DISPLAY_RESX / 6)
#define DISPLAY_PRINT_ROWS (DISPLAY_RESY / 8)
static char display_print_buf[DISPLAY_PRINT_ROWS][DISPLAY_PRINT_COLS];
static uint16_t display_print_fgcolor = COLOR_WHITE,
                display_print_bgcolor = COLOR_BLACK;

// set colors for display_print function
void display_print_color(uint16_t fgcolor, uint16_t bgcolor) {
  display_print_fgcolor = fgcolor;
  display_print_bgcolor = bgcolor;
}

// display text using bitmap font
void display_print(const char *text, int textlen) {
  static uint8_t row = 0, col = 0;

  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }

  // print characters to internal buffer (display_print_buf)
  for (int i = 0; i < textlen; i++) {
    switch (text[i]) {
      case '\r':
        break;
      case '\n':
        row++;
        col = 0;
        break;
      default:
        display_print_buf[row][col] = text[i];
        col++;
        break;
    }

    if (col >= DISPLAY_PRINT_COLS) {
      col = 0;
      row++;
    }

    if (row >= DISPLAY_PRINT_ROWS) {
      for (int j = 0; j < DISPLAY_PRINT_ROWS - 1; j++) {
        memcpy(display_print_buf[j], display_print_buf[j + 1],
               DISPLAY_PRINT_COLS);
      }
      memzero(display_print_buf[DISPLAY_PRINT_ROWS - 1], DISPLAY_PRINT_COLS);
      row = DISPLAY_PRINT_ROWS - 1;
    }
  }

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
    if (x < DISPLAY_PRINT_COLS && y < DISPLAY_PRINT_ROWS) {
      c = display_print_buf[y][x] & 0x7F;
      // char invert = display_print_buf[y][x] & 0x80;
    } else {
      c = ' ';
    }
    if (c < ' ') {
      c = ' ';
    }
    const uint8_t *g = Font_Bitmap + (5 * (c - ' '));
    if (k < 5 && (g[k] & (1 << j))) {
      PIXELDATA(display_print_fgcolor);
    } else {
      PIXELDATA(display_print_bgcolor);
    }
  }
  display_refresh();
}

#ifdef TREZOR_EMULATOR
#define mini_vsnprintf vsnprintf
#include <stdio.h>
#else
#include "mini_printf.h"
#endif

// variadic display_print
void display_printf(const char *fmt, ...) {
  if (!strchr(fmt, '%')) {
    display_print(fmt, strlen(fmt));
  } else {
    va_list va;
    va_start(va, fmt);
    char buf[256] = {0};
    int len = mini_vsnprintf(buf, sizeof(buf), fmt, va);
    display_print(buf, len);
    va_end(va);
  }
}

#endif  // TREZOR_PRINT_DISABLE

static uint8_t convert_char(const uint8_t c) {
  static char last_was_utf8 = 0;

  // non-printable ASCII character
  if (c < ' ') {
    last_was_utf8 = 0;
    return 0x7F;
  }

  // regular ASCII character
  if (c < 0x80) {
    last_was_utf8 = 0;
    return c;
  }

  // UTF-8 handling: https://en.wikipedia.org/wiki/UTF-8#Description

  // bytes 11xxxxxx are first bytes of UTF-8 characters
  if (c >= 0xC0) {
    last_was_utf8 = 1;
    return 0x7F;
  }

  if (last_was_utf8) {
    // bytes 10xxxxxx can be successive UTF-8 characters ...
    return 0;  // skip glyph
  } else {
    // ... or they are just non-printable ASCII characters
    return 0x7F;
  }

  return 0;
}

static const uint8_t *get_glyph(int font, uint8_t c) {
  c = convert_char(c);
  if (!c) return 0;

  // printable ASCII character
  if (c >= ' ' && c < 0x7F) {
    switch (font) {
#ifdef TREZOR_FONT_NORMAL_ENABLE
      case FONT_NORMAL:
        return FONT_NORMAL_DATA[c - ' '];
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
      case FONT_BOLD:
        return FONT_BOLD_DATA[c - ' '];
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
      case FONT_MONO:
        return FONT_MONO_DATA[c - ' '];
#endif
    }
    return 0;
  }

// non-printable character
#define PASTER(s) s##_glyph_nonprintable
#define NONPRINTABLE_GLYPH(s) PASTER(s)

  switch (font) {
#ifdef TREZOR_FONT_NORMAL_ENABLE
    case FONT_NORMAL:
      return NONPRINTABLE_GLYPH(FONT_NORMAL_DATA);
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
    case FONT_BOLD:
      return NONPRINTABLE_GLYPH(FONT_BOLD_DATA);
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
    case FONT_MONO:
      return NONPRINTABLE_GLYPH(FONT_MONO_DATA);
#endif
  }
  return 0;
}

static void display_text_render(int x, int y, const char *text, int textlen,
                                int font, uint16_t fgcolor, uint16_t bgcolor) {
  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }

  uint16_t colortable[16] = {0};
  set_color_table(colortable, fgcolor, bgcolor);

  // render glyphs
  for (int i = 0; i < textlen; i++) {
    const uint8_t *g = get_glyph(font, (uint8_t)text[i]);
    if (!g) continue;
    const uint8_t w = g[0];      // width
    const uint8_t h = g[1];      // height
    const uint8_t adv = g[2];    // advance
    const uint8_t bearX = g[3];  // bearingX
    const uint8_t bearY = g[4];  // bearingY
    if (w && h) {
      const int sx = x + bearX;
      const int sy = y - bearY;
      int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
      clamp_coords(sx, sy, w, h, &x0, &y0, &x1, &y1);
      display_set_window(x0, y0, x1, y1);
      for (int j = y0; j <= y1; j++) {
        for (int i = x0; i <= x1; i++) {
          const int rx = i - sx;
          const int ry = j - sy;
          const int a = rx + ry * w;
#if TREZOR_FONT_BPP == 1
          const uint8_t c = ((g[5 + a / 8] >> (7 - (a % 8) * 1)) & 0x01) * 15;
#elif TREZOR_FONT_BPP == 2
          const uint8_t c = ((g[5 + a / 4] >> (6 - (a % 4) * 2)) & 0x03) * 5;
#elif TREZOR_FONT_BPP == 4
          const uint8_t c = (g[5 + a / 2] >> (4 - (a % 2) * 4)) & 0x0F;
#elif TREZOR_FONT_BPP == 8
          const uint8_t c = g[5 + a / 1] >> 4;
#else
#error Unsupported TREZOR_FONT_BPP value
#endif
          PIXELDATA(colortable[c]);
        }
      }
    }
    x += adv;
  }
}

void display_text(int x, int y, const char *text, int textlen, int font,
                  uint16_t fgcolor, uint16_t bgcolor) {
  x += DISPLAY_OFFSET.x;
  y += DISPLAY_OFFSET.y;
  display_text_render(x, y, text, textlen, font, fgcolor, bgcolor);
}

void display_text_center(int x, int y, const char *text, int textlen, int font,
                         uint16_t fgcolor, uint16_t bgcolor) {
  x += DISPLAY_OFFSET.x;
  y += DISPLAY_OFFSET.y;
  int w = display_text_width(text, textlen, font);
  display_text_render(x - w / 2, y, text, textlen, font, fgcolor, bgcolor);
}

void display_text_right(int x, int y, const char *text, int textlen, int font,
                        uint16_t fgcolor, uint16_t bgcolor) {
  x += DISPLAY_OFFSET.x;
  y += DISPLAY_OFFSET.y;
  int w = display_text_width(text, textlen, font);
  display_text_render(x - w, y, text, textlen, font, fgcolor, bgcolor);
}

// compute the width of the text (in pixels)
int display_text_width(const char *text, int textlen, int font) {
  int width = 0;
  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }
  for (int i = 0; i < textlen; i++) {
    const uint8_t *g = get_glyph(font, (uint8_t)text[i]);
    if (!g) continue;
    const uint8_t adv = g[2];  // advance
    width += adv;
    /*
    if (i != textlen - 1) {
        const uint8_t adv = g[2]; // advance
        width += adv;
    } else { // last character
        const uint8_t w = g[0]; // width
        const uint8_t bearX = g[3]; // bearingX
        width += (bearX + w);
    }
    */
  }
  return width;
}

// Returns how many characters of the string can be used before exceeding
// the requested width. Tries to avoid breaking words if possible.
int display_text_split(const char *text, int textlen, int font,
                       int requested_width) {
  int width = 0;
  int lastspace = 0;
  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }
  for (int i = 0; i < textlen; i++) {
    if (text[i] == ' ') {
      lastspace = i;
    }
    const uint8_t *g = get_glyph(font, (uint8_t)text[i]);
    if (!g) continue;
    const uint8_t adv = g[2];  // advance
    width += adv;
    if (width > requested_width) {
      if (lastspace > 0) {
        return lastspace;
      } else {
        return i;
      }
    }
  }
  return textlen;
}

#define QR_MAX_VERSION 9

void display_qrcode(int x, int y, const char *data, uint32_t datalen,
                    uint8_t scale) {
  if (scale < 1 || scale > 10) return;

  uint8_t codedata[qrcodegen_BUFFER_LEN_FOR_VERSION(QR_MAX_VERSION)] = {0};
  uint8_t tempdata[qrcodegen_BUFFER_LEN_FOR_VERSION(QR_MAX_VERSION)] = {0};

  int side = 0;
  if (qrcodegen_encodeText(data, tempdata, codedata, qrcodegen_Ecc_MEDIUM,
                           qrcodegen_VERSION_MIN, QR_MAX_VERSION,
                           qrcodegen_Mask_AUTO, true)) {
    side = qrcodegen_getSize(codedata);
  }

  x += DISPLAY_OFFSET.x - (side + 2) * scale / 2;
  y += DISPLAY_OFFSET.y - (side + 2) * scale / 2;
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
  clamp_coords(x, y, (side + 2) * scale, (side + 2) * scale, &x0, &y0, &x1,
               &y1);
  display_set_window(x0, y0, x1, y1);
  for (int j = y0; j <= y1; j++) {
    for (int i = x0; i <= x1; i++) {
      int rx = (i - x) / scale - 1;
      int ry = (j - y) / scale - 1;
      // 1px border
      if (rx < 0 || ry < 0 || rx >= side || ry >= side) {
        PIXELDATA(0xFFFF);
        continue;
      }
      if (qrcodegen_getModule(codedata, rx, ry)) {
        PIXELDATA(0x0000);
      } else {
        PIXELDATA(0xFFFF);
      }
    }
  }
}

void display_offset(int set_xy[2], int *get_x, int *get_y) {
  if (set_xy) {
    DISPLAY_OFFSET.x = set_xy[0];
    DISPLAY_OFFSET.y = set_xy[1];
  }
  *get_x = DISPLAY_OFFSET.x;
  *get_y = DISPLAY_OFFSET.y;
}

int display_orientation(int degrees) {
  if (degrees != DISPLAY_ORIENTATION) {
#if TREZOR_MODEL == T
    if (degrees == 0 || degrees == 90 || degrees == 180 || degrees == 270) {
#elif TREZOR_MODEL == 1
    if (degrees == 0 || degrees == 180) {
#else
#error Unknown Trezor model
#endif
      DISPLAY_ORIENTATION = degrees;
      display_set_orientation(degrees);
    }
  }
  return DISPLAY_ORIENTATION;
}

int display_backlight(int val) {
#if TREZOR_MODEL == 1
  val = 255;
#endif
  if (DISPLAY_BACKLIGHT != val && val >= 0 && val <= 255) {
    DISPLAY_BACKLIGHT = val;
    display_set_backlight(val);
  }
  return DISPLAY_BACKLIGHT;
}

void display_fade(int start, int end, int delay) {
  for (int i = 0; i < 100; i++) {
    display_backlight(start + i * (end - start) / 100);
    hal_delay(delay / 100);
  }
  display_backlight(end);
}
