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

#include "display.h"
#include "buffers.h"
#include "common.h"

#ifdef USE_DMA2D
#include "dma2d.h"
#endif

#include "fonts/fonts.h"

#include <stdarg.h>
#include <string.h>

#include "memzero.h"

#include "display_interface.h"

static struct { int x, y; } DISPLAY_OFFSET;

// common display functions

#define CLAMP(x, min, max) (MIN(MAX((x), (min)), (max)))

static inline void clamp_coords(int x, int y, int w, int h, int *x0, int *y0,
                                int *x1, int *y1) {
  *x0 = CLAMP(x, 0, DISPLAY_RESX);
  *y0 = CLAMP(y, 0, DISPLAY_RESY);
  *x1 = CLAMP(x + w - 1, -1, DISPLAY_RESX - 1);
  *y1 = CLAMP(y + h - 1, -1, DISPLAY_RESY - 1);
}

void display_clear(void) {
#ifdef DISPLAY_EFFICIENT_CLEAR
  display_efficient_clear();
#else
  const int saved_orientation = display_get_orientation();

  display_reset_state();

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
  // flag display for refresh
#endif
  display_pixeldata_dirty();
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
  display_pixeldata_dirty();
}

void display_text_render_buffer(const char *text, int textlen, int font,
                                buffer_text_t *buffer, int text_offset) {
  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }

  int x = 0;
  int max_height = font_max_height(font);
  int baseline = font_baseline(font);

  // render glyphs
  for (int c_idx = 0; c_idx < textlen; c_idx++) {
    const uint8_t *g = font_get_glyph(font, (uint8_t)text[c_idx]);
    if (!g) continue;
    const uint8_t w = g[0];      // width
    const uint8_t h = g[1];      // height
    const uint8_t adv = g[2];    // advance
    const uint8_t bearX = g[3];  // bearingX
    const uint8_t bearY = g[4];  // bearingY
    if (w && h) {
      for (int j = 0; j < h; j++) {
        for (int i = 0; i < w; i++) {
          const int a = i + j * w;
#if TREZOR_FONT_BPP == 1
          const uint8_t c = ((g[5 + a / 8] >> (7 - (a % 8) * 1)) & 0x01) * 15;
#elif TREZOR_FONT_BPP == 2
          const uint8_t c = ((g[5 + a / 4] >> (6 - (a % 4) * 2)) & 0x03) * 5;
#elif TREZOR_FONT_BPP == 4
          const uint8_t c = (g[5 + a / 2] >> (4 - (a % 2) * 4)) & 0x0F;
#elif TREZOR_FONT_BPP == 8
#error Rendering into buffer not supported when using TREZOR_FONT_BPP = 8
          // const uint8_t c = g[5 + a / 1] >> 4;
#else
#error Unsupported TREZOR_FONT_BPP value
#endif

          int x_pos = text_offset + i + x + bearX;
          int y_pos = j + max_height - bearY - baseline;

          if (y_pos < 0) continue;

          if (x_pos >= BUFFER_PIXELS || x_pos < 0) {
            continue;
          }

          int buffer_pos = x_pos + y_pos * BUFFER_PIXELS;

          if (buffer_pos < (sizeof(buffer_text_t) * 2)) {
            int b = buffer_pos / 2;
            if (buffer_pos % 2) {
              buffer->buffer[b] |= c << 4;
            } else {
              buffer->buffer[b] |= (c);
            }
          }
        }
      }
    }
    x += adv;
  }
}

// see docs/misc/toif.md for definition of the TOIF format
bool display_toif_info(const uint8_t *data, uint32_t len, uint16_t *out_w,
                       uint16_t *out_h, toif_format_t *out_format) {
  if (len < 12 || memcmp(data, "TOI", 3) != 0) {
    return false;
  }
  toif_format_t format = false;
  if (data[3] == 'f') {
    format = TOIF_FULL_COLOR_BE;
  } else if (data[3] == 'g') {
    format = TOIF_GRAYSCALE_OH;
  } else if (data[3] == 'F') {
    format = TOIF_FULL_COLOR_LE;
  } else if (data[3] == 'G') {
    format = TOIF_GRAYSCALE_EH;
  } else {
    return false;
  }

  uint16_t w = *(uint16_t *)(data + 4);
  uint16_t h = *(uint16_t *)(data + 6);

  uint32_t datalen = *(uint32_t *)(data + 8);
  if (datalen != len - 12) {
    return false;
  }

  if (out_w != NULL && out_h != NULL && out_format != NULL) {
    *out_w = w;
    *out_h = h;
    *out_format = format;
  }
  return true;
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
  display_pixeldata_dirty();
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

#ifdef FRAMEBUFFER
static void display_text_render(int x, int y, const char *text, int textlen,
                                int font, uint16_t fgcolor, uint16_t bgcolor) {
  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }

  int total_adv = 0;

  uint32_t *fb = display_get_fb_addr();

  uint16_t colortable[16] = {0};
  set_color_table(colortable, fgcolor, bgcolor);

  // render glyphs
  for (int c_idx = 0; c_idx < textlen; c_idx++) {
    const uint8_t *g = font_get_glyph(font, (uint8_t)text[c_idx]);
    if (!g) continue;
    const uint8_t w = g[0];      // width
    const uint8_t h = g[1];      // height
    const uint8_t adv = g[2];    // advance
    const uint8_t bearX = g[3];  // bearingX
    const uint8_t bearY = g[4];  // bearingY
    if (w && h) {
      for (int j = 0; j < h; j++) {
        for (int i = 0; i < w; i++) {
          const int a = i + j * w;
#if TREZOR_FONT_BPP == 1
          const uint8_t c = ((g[5 + a / 8] >> (7 - (a % 8) * 1)) & 0x01) * 15;
#elif TREZOR_FONT_BPP == 2
          const uint8_t c = ((g[5 + a / 4] >> (6 - (a % 4) * 2)) & 0x03) * 5;
#elif TREZOR_FONT_BPP == 4
          const uint8_t c = (g[5 + a / 2] >> (4 - (a % 2) * 4)) & 0x0F;
#elif TREZOR_FONT_BPP == 8
#error Rendering into buffer not supported when using TREZOR_FONT_BPP = 8
          // const uint8_t c = g[5 + a / 1] >> 4;
#else
#error Unsupported TREZOR_FONT_BPP value
#endif

          int x_pos = x + i + total_adv + bearX;
          int y_pos = y + j - bearY;

          if (y_pos < 0) continue;

          if (x_pos >= DISPLAY_FRAMEBUFFER_WIDTH || x_pos < 0 ||
              y_pos >= DISPLAY_FRAMEBUFFER_HEIGHT || y_pos < 0) {
            continue;
          }

          display_pixel((uint8_t *)fb, x_pos, y_pos, colortable[c]);
        }
      }
    }
    total_adv += adv;
  }
  display_pixeldata_dirty();
}

#else
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
    const uint8_t *g = font_get_glyph(font, (uint8_t)text[i]);
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
  display_pixeldata_dirty();
}
#endif

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
    const uint8_t *g = font_get_glyph(font, (uint8_t)text[i]);
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
    const uint8_t *g = font_get_glyph(font, (uint8_t)text[i]);
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

#ifdef TREZOR_PRODTEST

#include "qr-code-generator/qrcodegen.h"
#define QR_MAX_VERSION 9

void display_qrcode(int x, int y, const char *data, uint8_t scale) {
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
  display_pixeldata_dirty();
}

#endif

void display_offset(int set_xy[2], int *get_x, int *get_y) {
  if (set_xy) {
    DISPLAY_OFFSET.x = set_xy[0];
    DISPLAY_OFFSET.y = set_xy[1];
  }
  *get_x = DISPLAY_OFFSET.x;
  *get_y = DISPLAY_OFFSET.y;
}

void display_fade(int start, int end, int delay) {
#ifdef USE_BACKLIGHT
  for (int i = 0; i < 100; i++) {
    display_backlight(start + i * (end - start) / 100);
    hal_delay(delay / 100);
  }
  display_backlight(end);
#endif
}

#define UTF8_IS_CONT(ch) (((ch)&0xC0) == 0x80)

void display_utf8_substr(const char *buf_start, size_t buf_len, int char_off,
                         int char_len, const char **out_start, int *out_len) {
  size_t i = 0;

  for (; i < buf_len; i++) {
    if (char_off == 0) {
      break;
    }
    if (!UTF8_IS_CONT(buf_start[i])) {
      char_off--;
    }
  }
  size_t i_start = i;

  for (; i < buf_len; i++) {
    if (char_len == 0) {
      break;
    }
    if (!UTF8_IS_CONT(buf_start[i])) {
      char_len--;
    }
  }

  for (; i < buf_len; i++) {
    if (!UTF8_IS_CONT(buf_start[i])) {
      break;
    }
  }

  *out_start = buf_start + i_start;
  *out_len = i - i_start;
}
