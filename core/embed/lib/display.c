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
  font_glyph_iter_t iter = font_glyph_iter_init(font, (uint8_t *)text, textlen);
  const uint8_t *g = NULL;
  while (font_next_glyph(&iter, &g)) {
    const uint8_t w = g[0];      // width
    const uint8_t h = g[1];      // height
    const uint8_t adv = g[2];    // advance
    const uint8_t bearX = g[3];  // bearingX
    const uint8_t bearY = g[4];  // bearingY
#if TREZOR_FONT_BPP == 4
    uint8_t wa = w + (w & 1);
#else
    uint8_t wa = w;
#endif
    if (wa && h) {
      for (int j = 0; j < h; j++) {
        for (int i = 0; i < wa; i++) {
          const int a = i + j * wa;
#if TREZOR_FONT_BPP == 1
          const uint8_t c = ((g[5 + a / 8] >> (7 - (a % 8) * 1)) & 0x01) * 15;
#elif TREZOR_FONT_BPP == 2
          const uint8_t c = ((g[5 + a / 4] >> (6 - (a % 4) * 2)) & 0x03) * 5;
#elif TREZOR_FONT_BPP == 4
          const uint8_t c = (g[5 + a / 2] >> ((a % 2) * 4)) & 0x0F;
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
  font_glyph_iter_t iter = font_glyph_iter_init(font, (uint8_t *)text, textlen);
  const uint8_t *g = NULL;
  while (font_next_glyph(&iter, &g)) {
    const uint8_t w = g[0];      // width
    const uint8_t h = g[1];      // height
    const uint8_t adv = g[2];    // advance
    const uint8_t bearX = g[3];  // bearingX
    const uint8_t bearY = g[4];  // bearingY

#if TREZOR_FONT_BPP == 4
    uint8_t wa = w + (w & 1);
#else
    uint8_t wa = w;
#endif

    if (w && h) {
      for (int j = 0; j < h; j++) {
        for (int i = 0; i < wa; i++) {
          const int a = i + j * wa;
#if TREZOR_FONT_BPP == 1
          const uint8_t c = ((g[5 + a / 8] >> (7 - (a % 8) * 1)) & 0x01) * 15;
#elif TREZOR_FONT_BPP == 2
          const uint8_t c = ((g[5 + a / 4] >> (6 - (a % 4) * 2)) & 0x03) * 5;
#elif TREZOR_FONT_BPP == 4
          const uint8_t c = (g[5 + a / 2] >> ((a % 2) * 4)) & 0x0F;
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
  font_glyph_iter_t iter = font_glyph_iter_init(font, (uint8_t *)text, textlen);
  const uint8_t *g = NULL;
  while (font_next_glyph(&iter, &g)) {
    const uint8_t w = g[0];      // width
    const uint8_t h = g[1];      // height
    const uint8_t adv = g[2];    // advance
    const uint8_t bearX = g[3];  // bearingX
    const uint8_t bearY = g[4];  // bearingY

#if TREZOR_FONT_BPP == 4
    uint8_t wa = w + (w & 1);
#else
    uint8_t wa = w;
#endif
    if (wa && h) {
      const int sx = x + bearX;
      const int sy = y - bearY;
      int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
      clamp_coords(sx, sy, w, h, &x0, &y0, &x1, &y1);
      display_set_window(x0, y0, x1, y1);
      for (int j = y0; j <= y1; j++) {
        for (int i = x0; i <= x1; i++) {
          const int rx = i - sx;
          const int ry = j - sy;
          const int a = rx + ry * wa;
#if TREZOR_FONT_BPP == 1
          const uint8_t c = ((g[5 + a / 8] >> (7 - (a % 8) * 1)) & 0x01) * 15;
#elif TREZOR_FONT_BPP == 2
          const uint8_t c = ((g[5 + a / 4] >> (6 - (a % 4) * 2)) & 0x03) * 5;
#elif TREZOR_FONT_BPP == 4
          const uint8_t c = (g[5 + a / 2] >> ((a % 2) * 4)) & 0x0F;
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
  int w = font_text_width(font, text, textlen);
  display_text_render(x - w / 2, y, text, textlen, font, fgcolor, bgcolor);
}

void display_text_right(int x, int y, const char *text, int textlen, int font,
                        uint16_t fgcolor, uint16_t bgcolor) {
  x += DISPLAY_OFFSET.x;
  y += DISPLAY_OFFSET.y;
  int w = font_text_width(font, text, textlen);
  display_text_render(x - w, y, text, textlen, font, fgcolor, bgcolor);
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
