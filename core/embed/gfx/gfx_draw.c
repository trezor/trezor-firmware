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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <gfx/fonts.h>
#include <gfx/gfx_draw.h>
#include <io/display.h>

typedef struct {
  int16_t dst_x;
  int16_t dst_y;
  int16_t src_x;
  int16_t src_y;
  int16_t width;
  int16_t height;
} gfx_clip_t;

static inline gfx_clip_t gfx_clip(gfx_rect_t dst, const gfx_bitmap_t* bitmap) {
  int16_t dst_x = dst.x0;
  int16_t dst_y = dst.y0;

  int16_t src_x = 0;
  int16_t src_y = 0;

  if (bitmap != NULL) {
    src_x += bitmap->offset.x;
    src_y += bitmap->offset.y;

    // Normalize negative x-offset of bitmap
    if (src_x < 0) {
      dst_x -= src_x;
      src_x = 0;
    }

    // Normalize negative y-offset of src bitmap
    if (src_y < 0) {
      dst_y -= src_y;
      src_y = 0;
    }
  }

  // Normalize negative top-left of destination rectangle
  if (dst_x < 0) {
    src_x -= dst_x;
    dst_x = 0;
  }

  if (dst_y < 0) {
    src_y -= dst_y;
    dst_y = 0;
  }

  // Calculate dimension of effective rectangle
  int16_t width = MIN(DISPLAY_RESX, dst.x1) - dst_x;
  int16_t height = MIN(DISPLAY_RESY, dst.y1) - dst_y;

  if (bitmap != NULL) {
    width = MIN(width, bitmap->size.x - src_x);
    height = MIN(height, bitmap->size.y - src_y);
  }

  gfx_clip_t clip = {
      .dst_x = dst_x,
      .dst_y = dst_y,
      .src_x = src_x,
      .src_y = src_y,
      .width = width,
      .height = height,
  };

  return clip;
}

void gfx_clear(void) {
  gfx_bitblt_t bb = {
      // Destination bitmap
      .height = DISPLAY_RESY,
      .width = DISPLAY_RESX,
      .dst_row = NULL,
      .dst_x = 0,
      .dst_y = 0,
      .dst_stride = 0,

      // Source bitmap
      .src_fg = 0,
      .src_alpha = 255,
  };

  display_fill(&bb);
}

void gfx_draw_bar(gfx_rect_t rect, gfx_color_t color) {
  gfx_clip_t clip = gfx_clip(rect, NULL);

  if (clip.width <= 0 || clip.height <= 0) {
    return;
  }

  gfx_bitblt_t bb = {
      // Destination bitmap
      .height = clip.height,
      .width = clip.width,
      .dst_row = NULL,
      .dst_x = clip.dst_x,
      .dst_y = clip.dst_y,
      .dst_stride = 0,

      // Source bitmap
      .src_fg = color,
      .src_alpha = 255,
  };

  display_fill(&bb);
}

void gfx_draw_bitmap(gfx_rect_t rect, const gfx_bitmap_t* bitmap) {
  gfx_clip_t clip = gfx_clip(rect, bitmap);

  if (clip.width <= 0 || clip.height <= 0) {
    return;
  }

  gfx_bitblt_t bb = {
      // Destination bitmap
      .height = clip.height,
      .width = clip.width,
      .dst_row = NULL,
      .dst_x = clip.dst_x,
      .dst_y = clip.dst_y,
      .dst_stride = 0,

      // Source bitmap
      .src_row = (uint8_t*)bitmap->ptr + bitmap->stride * clip.src_y,
      .src_x = clip.src_x,
      .src_y = clip.src_y,
      .src_stride = bitmap->stride,
      .src_fg = bitmap->fg_color,
      .src_bg = bitmap->bg_color,
      .src_alpha = 255,
  };

  // Currently, we use `gfx_draw_bitmap` exclusively for text rendering.
  // Therefore, we are including the variant of `display_copy_xxx()` that is
  // specifically needed for drawing glyphs in the format we are using
  // to save some space in the flash memory.

#if TREZOR_FONT_BPP == 1
  if (bitmap->format == GFX_FORMAT_MONO1P) {
    display_copy_mono1p(&bb);
  }
#endif
#if TREZOR_FONT_BPP == 4
  if (bitmap->format == GFX_FORMAT_MONO4) {
    display_copy_mono4(&bb);
  }
#endif
}

#if TREZOR_FONT_BPP == 1
#define GLYPH_FORMAT GFX_FORMAT_MONO1P
#define GLYPH_STRIDE(w) (((w) + 7) / 8)
#elif TREZOR_FONT_BPP == 2
#error Unsupported TREZOR_FONT_BPP value
#define GLYPH_FORMAT GFX_FORMAT_MONO2
#define GLYPH_STRIDE(w) (((w) + 3) / 4)
#elif TREZOR_FONT_BPP == 4
#define GLYPH_FORMAT GFX_FORMAT_MONO4
#define GLYPH_STRIDE(w) (((w) + 1) / 2)
#elif TREZOR_FONT_BPP == 8
#error Unsupported TREZOR_FONT_BPP value
#define GLYPH_FORMAT GFX_FORMAT_MONO8
#define GLYPH_STRIDE(w) (w)
#else
#error Unsupported TREZOR_FONT_BPP value
#endif

#define GLYPH_WIDTH(g) ((g)[0])
#define GLYPH_HEIGHT(g) ((g)[1])
#define GLYPH_ADVANCE(g) ((g)[2])
#define GLYPH_BEARING_X(g) ((g)[3])
#define GLYPH_BEARING_Y(g) ((g)[4])
#define GLYPH_DATA(g) ((void*)&(g)[5])

void gfx_draw_text(gfx_offset_t pos, const char* text, size_t maxlen,
                   const gfx_text_attr_t* attr, gfx_text_align_t align) {
  if (text == NULL) {
    return;
  }

  if (align == GFX_ALIGN_CENTER) {
    int w = font_text_width(attr->font, text, maxlen);
    pos = gfx_offset(pos.x - w / 2, pos.y);
  }

  gfx_bitmap_t bitmap = {
      .format = GLYPH_FORMAT,
      .fg_color = attr->fg_color,
      .bg_color = attr->bg_color,
  };

  int max_height = font_max_height(attr->font);
  int baseline = font_baseline(attr->font);

  for (int i = 0; i < maxlen; i++) {
    uint8_t ch = (uint8_t)text[i];

    if (ch == 0 || pos.x >= DISPLAY_RESX) {
      break;
    }

    const uint8_t* glyph = font_get_glyph(attr->font, ch);

    if (glyph == NULL) {
      continue;
    }

    bitmap.ptr = GLYPH_DATA(glyph);
    bitmap.stride = GLYPH_STRIDE(GLYPH_WIDTH(glyph));
    bitmap.size.x = GLYPH_WIDTH(glyph);
    bitmap.size.y = GLYPH_HEIGHT(glyph);

    bitmap.offset.x = -GLYPH_BEARING_X(glyph);
    bitmap.offset.y = -(max_height - baseline - GLYPH_BEARING_Y(glyph));

    gfx_draw_bitmap(gfx_rect(pos.x, pos.y, DISPLAY_RESX, DISPLAY_RESY),
                    &bitmap);

    pos.x += GLYPH_ADVANCE(glyph);
  }
}

#ifdef TREZOR_PRODTEST

#include "qrcode/qrcodegen.h"
#define QR_MAX_VERSION 9

void gfx_draw_qrcode(gfx_offset_t offset, uint8_t scale, const char* data) {
  if (scale < 1 || scale > 10) return;

  int x = offset.x;
  int y = offset.y;

  uint8_t codedata[qrcodegen_BUFFER_LEN_FOR_VERSION(QR_MAX_VERSION)] = {0};
  uint8_t tempdata[qrcodegen_BUFFER_LEN_FOR_VERSION(QR_MAX_VERSION)] = {0};

  int side = 0;
  if (qrcodegen_encodeText(data, tempdata, codedata, qrcodegen_Ecc_MEDIUM,
                           qrcodegen_VERSION_MIN, QR_MAX_VERSION,
                           qrcodegen_Mask_AUTO, true)) {
    side = qrcodegen_getSize(codedata);
  }

  // Calculate border size (1 extra modules around the QR code)
  int border_side = ((side + 2) * scale);

  // Calculate border left-top corner
  x -= border_side / 2;
  y -= border_side / 2;

  // Fill the backround (including the border) with white color
  gfx_rect_t border_rect = gfx_rect_wh(x, y, border_side, border_side);
  gfx_draw_bar(border_rect, COLOR_WHITE);

  // Center QR code inside the border
  x += scale;
  y += scale;

  // Draw black modules
  for (int i = 0; i < side; i++) {
    for (int j = 0; j < side; j++) {
      if (qrcodegen_getModule(codedata, i, j)) {
        gfx_rect_t rect =
            gfx_rect_wh(x + i * scale, y + j * scale, scale, scale);
        gfx_draw_bar(rect, COLOR_BLACK);
      }
    }
  }
}

#endif  // TREZOR_PRODTEST
