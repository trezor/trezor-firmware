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

#include "buffers.h"
#include "common.h"
#include "display.h"

#ifdef USE_DMA2D
#include "dma2d.h"
#endif

#ifdef USE_RUST_LOADER
#include "rust_ui.h"
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
  PIXELDATA_DIRTY();
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
  PIXELDATA_DIRTY();
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
  PIXELDATA_DIRTY();
}

void display_bar_radius_buffer(int x, int y, int w, int h, uint8_t r,
                               buffer_text_t *buffer) {
  if (h > 32) {
    return;
  }
  if (r != 2 && r != 4 && r != 8 && r != 16) {
    return;
  } else {
    r = 16 / r;
  }
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
  clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
  for (int j = y0; j <= y1; j++) {
    for (int i = x0; i <= x1; i++) {
      int rx = i - x;
      int ry = j - y;
      int p = j * DISPLAY_RESX + i;
      uint8_t c = 0;
      if (rx < CORNER_RADIUS / r && ry < CORNER_RADIUS / r) {
        c = cornertable[rx * r + ry * r * CORNER_RADIUS];
      } else if (rx < CORNER_RADIUS / r && ry >= h - CORNER_RADIUS / r) {
        c = cornertable[rx * r + (h - 1 - ry) * r * CORNER_RADIUS];
      } else if (rx >= w - CORNER_RADIUS / r && ry < CORNER_RADIUS / r) {
        c = cornertable[(w - 1 - rx) * r + ry * r * CORNER_RADIUS];
      } else if (rx >= w - CORNER_RADIUS / r && ry >= h - CORNER_RADIUS / r) {
        c = cornertable[(w - 1 - rx) * r + (h - 1 - ry) * r * CORNER_RADIUS];
      } else {
        c = 15;
      }
      int b = p / 2;
      if (p % 2) {
        buffer->buffer[b] |= c << 4;
      } else {
        buffer->buffer[b] |= (c);
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

#ifndef USE_DMA2D
void display_image(int x, int y, int w, int h, const void *data,
                   uint32_t datalen) {
#if defined TREZOR_MODEL_T
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

  PIXELDATA_DIRTY();
  for (uint32_t pos = 0; pos < w * h; pos++) {
    int st = uzlib_uncompress(&decomp);
    if (st == TINF_DONE) break;  // all OK
    if (st < 0) break;           // error
    const int px = pos % w;
    const int py = pos / w;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
      PIXELDATA((decomp_out[1] << 8) | decomp_out[0]);
    }
    decomp.dest = (uint8_t *)&decomp_out;
  }
#endif
}
#else
void display_image(int x, int y, int w, int h, const void *data,
                   uint32_t datalen) {
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

  line_buffer_16bpp_t *b1 = buffers_get_line_buffer_16bpp(0, false);
  line_buffer_16bpp_t *b2 = buffers_get_line_buffer_16bpp(1, false);

  uzlib_prepare(&decomp, decomp_window, data, datalen, b1, w * 2);

  dma2d_setup_16bpp();

  for (int32_t pos = 0; pos < h; pos++) {
    int32_t pixels = w;
    line_buffer_16bpp_t *next_buf = (pos % 2 == 1) ? b1 : b2;
    decomp.dest = next_buf->buffer;
    decomp.dest_limit = next_buf->buffer + w * 2;
    int st = uzlib_uncompress(&decomp);
    if (st < 0) break;  // error
    dma2d_wait_for_transfer();
    dma2d_start(next_buf->buffer, (uint8_t *)DISPLAY_DATA_ADDRESS, pixels);
  }
  dma2d_wait_for_transfer();
}
#endif

#define AVATAR_BORDER_SIZE 4
#define AVATAR_BORDER_LOW                        \
  (AVATAR_IMAGE_SIZE / 2 - AVATAR_BORDER_SIZE) * \
      (AVATAR_IMAGE_SIZE / 2 - AVATAR_BORDER_SIZE)
#define AVATAR_BORDER_HIGH (AVATAR_IMAGE_SIZE / 2) * (AVATAR_IMAGE_SIZE / 2)
#define AVATAR_ANTIALIAS 1

void display_avatar(int x, int y, const void *data, uint32_t datalen,
                    uint16_t fgcolor, uint16_t bgcolor) {
#if defined TREZOR_MODEL_T
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
      if (d < AVATAR_BORDER_LOW) {
        // inside border area
        PIXELDATA((decomp_out[0] << 8) | decomp_out[1]);
      } else if (d > AVATAR_BORDER_HIGH) {
        // outside border area
        PIXELDATA(bgcolor);
      } else {
        // border area
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
  PIXELDATA_DIRTY();
#endif
}

#ifndef USE_DMA2D
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
    const int px = (pos * 2) % w;
    const int py = (pos * 2) / w;
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) {
      PIXELDATA(colortable[decomp_out & 0x0F]);
      PIXELDATA(colortable[decomp_out >> 4]);
    }
    decomp.dest = (uint8_t *)&decomp_out;
  }
  PIXELDATA_DIRTY();
}
#else
void display_icon(int x, int y, int w, int h, const void *data,
                  uint32_t datalen, uint16_t fgcolor, uint16_t bgcolor) {
  x += DISPLAY_OFFSET.x;
  y += DISPLAY_OFFSET.y;
  x &= ~1;  // cannot draw at odd coordinate
  w &= ~1;  // cannot draw odd-wide icons
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;
  clamp_coords(x, y, w, h, &x0, &y0, &x1, &y1);
  display_set_window(x0, y0, x1, y1);
  x0 -= x;
  x1 -= x;
  y0 -= y;
  y1 -= y;

  int width = x1 - x0 + 1;
  if (width <= 0) {
    return;
  }

  uint8_t b[DISPLAY_RESX / 2];
  line_buffer_4bpp_t *b1 = buffers_get_line_buffer_4bpp(0, false);
  line_buffer_4bpp_t *b2 = buffers_get_line_buffer_4bpp(1, false);

  struct uzlib_uncomp decomp = {0};
  uint8_t decomp_window[UZLIB_WINDOW_SIZE] = {0};

  uzlib_prepare(&decomp, decomp_window, data, datalen, b, w / 2);

  dma2d_setup_4bpp(fgcolor, bgcolor);

  int off_x = x < 0 ? -x : 0;

  for (uint32_t pos = 0; pos < h; pos++) {
    line_buffer_4bpp_t *next_buf = (pos % 2 == 0) ? b1 : b2;
    decomp.dest = b;
    decomp.dest_limit = b + w / 2;
    int st = uzlib_uncompress(&decomp);
    if (st < 0) break;  // error
    if (pos >= y0 && pos <= y1) {
      memcpy(next_buf->buffer, &b[off_x / 2], width / 2);
      dma2d_wait_for_transfer();
      dma2d_start(next_buf->buffer, (uint8_t *)DISPLAY_DATA_ADDRESS, width);
    }
  }
  dma2d_wait_for_transfer();
}
#endif

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

#ifndef USE_RUST_LOADER
#if defined TREZOR_MODEL_T
#include "loader_T.h"
#elif defined TREZOR_MODEL_R
#include "loader_R.h"
#endif

void display_loader(uint16_t progress, bool indeterminate, int yoffset,
                    uint16_t fgcolor, uint16_t bgcolor, const uint8_t *icon,
                    uint32_t iconlen, uint16_t iconfgcolor) {
#if defined TREZOR_MODEL_T || defined TREZOR_MODEL_R
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
  uint8_t icondata[(LOADER_ICON_SIZE * LOADER_ICON_SIZE) / 2] = {0};
  if (icon && memcmp(icon, "TOIG", 4) == 0 &&
      LOADER_ICON_SIZE == *(uint16_t *)(icon + 4) &&
      LOADER_ICON_SIZE == *(uint16_t *)(icon + 6) &&
      iconlen == 12 + *(uint32_t *)(icon + 8)) {
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
          c = (icon[i / 2] & 0xF0) >> 4;
        } else {
          c = icon[i / 2] & 0x0F;
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
  PIXELDATA_DIRTY();
#endif
}
#else

void display_loader(uint16_t progress, bool indeterminate, int yoffset,
                    uint16_t fgcolor, uint16_t bgcolor, const uint8_t *icon,
                    uint32_t iconlen, uint16_t iconfgcolor) {
#if defined TREZOR_MODEL_T || defined TREZOR_MODEL_R
  loader_uncompress_r(yoffset, fgcolor, bgcolor, iconfgcolor, progress,
                      indeterminate, icon, iconlen);
#endif
}
#endif

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
  PIXELDATA_DIRTY();
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
  PIXELDATA_DIRTY();
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
  PIXELDATA_DIRTY();
}

void display_offset(int set_xy[2], int *get_x, int *get_y) {
  if (set_xy) {
    DISPLAY_OFFSET.x = set_xy[0];
    DISPLAY_OFFSET.y = set_xy[1];
  }
  *get_x = DISPLAY_OFFSET.x;
  *get_y = DISPLAY_OFFSET.y;
}

void display_fade(int start, int end, int delay) {
  for (int i = 0; i < 100; i++) {
    display_backlight(start + i * (end - start) / 100);
    hal_delay(delay / 100);
  }
  display_backlight(end);
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

void display_pixeldata_dirty(void) { PIXELDATA_DIRTY(); }
