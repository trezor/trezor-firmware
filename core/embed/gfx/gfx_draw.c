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

static inline gfx_clip_t gfx_clip(gfx_rect_t dst) {
  int16_t dst_x = dst.x0;
  int16_t dst_y = dst.y0;

  int16_t src_x = 0;
  int16_t src_y = 0;

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
  gfx_clip_t clip = gfx_clip(rect);

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
