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

#include <display.h>

#include "display_draw.h"
#include "fonts/fonts.h"
#include "gl_draw.h"

typedef struct {
  int16_t dst_x;
  int16_t dst_y;
  int16_t src_x;
  int16_t src_y;
  int16_t width;
  int16_t height;
} gl_clip_t;

static inline gl_clip_t gl_clip(gl_rect_t dst, const gl_bitmap_t* bitmap) {
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

  gl_clip_t clip = {
      .dst_x = dst_x,
      .dst_y = dst_y,
      .src_x = src_x,
      .src_y = src_y,
      .width = width,
      .height = height,
  };

  return clip;
}

void gl_clear(void) {
  gl_bitblt_t bb = {
      // Destination bitmap
      .height = DISPLAY_RESX,
      .width = DISPLAY_RESY,
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

void gl_draw_bar(gl_rect_t rect, gl_color_t color) {
  gl_clip_t clip = gl_clip(rect, NULL);

  if (clip.width <= 0 || clip.height <= 0) {
    return;
  }

  gl_bitblt_t bb = {
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

void gl_draw_bitmap(gl_rect_t rect, const gl_bitmap_t* bitmap) {
  gl_clip_t clip = gl_clip(rect, bitmap);

  if (clip.width <= 0 || clip.height <= 0) {
    return;
  }

  gl_bitblt_t bb = {
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

#if TREZOR_FONT_BPP == 1
  if (bitmap->format == GL_FORMAT_MONO1P) {
    display_copy_mono1p(&bb);
  }
#endif
#if TREZOR_FONT_BPP == 4
  if (bitmap->format == GL_FORMAT_MONO4) {
    display_copy_mono4(&bb);
  }
#endif
}

#if TREZOR_FONT_BPP == 1
#define GLYPH_FORMAT GL_FORMAT_MONO1P
#define GLYPH_STRIDE(w) (((w) + 7) / 8)
#elif TREZOR_FONT_BPP == 2
#error Unsupported TREZOR_FONT_BPP value
#define GLYPH_FORMAT GL_FORMAT_MONO2
#define GLYPH_STRIDE(w) (((w) + 3) / 4)
#elif TREZOR_FONT_BPP == 4
#define GLYPH_FORMAT GL_FORMAT_MONO4
#define GLYPH_STRIDE(w) (((w) + 1) / 2)
#elif TREZOR_FONT_BPP == 8
#error Unsupported TREZOR_FONT_BPP value
#define GLYPH_FORMAT GL_FORMAT_MONO8
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

void gl_draw_text(gl_offset_t pos, const char* text, size_t maxlen,
                  const gl_text_attr_t* attr) {
  if (text == NULL) {
    return;
  }

  gl_bitmap_t bitmap = {
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

    gl_draw_bitmap(gl_rect(pos.x, pos.y, DISPLAY_RESX, DISPLAY_RESY), &bitmap);

    pos.x += GLYPH_ADVANCE(glyph);
  }
}

// ===============================================================
// emulation of legacy functions

void display_clear(void) { gl_clear(); }

void display_bar(int x, int y, int w, int h, uint16_t c) {
  gl_draw_bar(gl_rect_wh(x, y, w, h), c);
}

void display_text(int x, int y, const char* text, int textlen, int font,
                  uint16_t fg_color, uint16_t bg_color) {
  gl_text_attr_t attr = {
      .font = font,
      .fg_color = fg_color,
      .bg_color = bg_color,
  };

  size_t maxlen = textlen < 0 ? UINT32_MAX : textlen;
  gl_draw_text(gl_offset(x, y), text, maxlen, &attr);
}

void display_text_center(int x, int y, const char* text, int textlen, int font,
                         uint16_t fg_color, uint16_t bg_color) {
  gl_text_attr_t attr = {
      .font = font,
      .fg_color = fg_color,
      .bg_color = bg_color,
  };

  size_t maxlen = textlen < 0 ? UINT32_MAX : textlen;
  int w = font_text_width(font, text, textlen);
  gl_draw_text(gl_offset(x - w / 2, y), text, maxlen, &attr);
}
