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

#pragma once

#include <gfx/gfx_color.h>

// 2D rectangle coordinates
//
// `x0`, `y0` - top-left coordinates
// `x1`, `y1` - bottom-right coordinates point (not included)
typedef struct {
  int16_t x0;
  int16_t y0;
  int16_t x1;
  int16_t y1;
} gfx_rect_t;

// Builds a rectangle (`gfx_rect_t`) from top-left coordinates and dimensions
static inline gfx_rect_t gfx_rect_wh(int16_t x, int16_t y, int16_t w,
                                     int16_t h) {
  gfx_rect_t rect = {
      .x0 = x,
      .y0 = y,
      .x1 = x + w,
      .y1 = y + h,
  };

  return rect;
}

// Builds a rectangle (`gfx_rect_t`) from top-left and bottom-right coordinates
static inline gfx_rect_t gfx_rect(int16_t x0, int16_t y0, int16_t x1,
                                  int16_t y1) {
  gfx_rect_t rect = {
      .x0 = x0,
      .y0 = y0,
      .x1 = x1,
      .y1 = y1,
  };

  return rect;
}

// 2D offset/ coordinates
typedef struct {
  int16_t x;
  int16_t y;
} gfx_offset_t;

// Builds a `gfx_offset_t` structure
static inline gfx_offset_t gfx_offset(int16_t x, int16_t y) {
  gfx_offset_t offset = {
      .x = x,
      .y = y,
  };

  return offset;
}

// 2D size in pixels
typedef struct {
  int16_t x;
  int16_t y;
} gfx_size_t;

// Builds a `gfx_size_t` structure
static inline gfx_size_t gfx_size(int16_t x, int16_t y) {
  gfx_size_t size = {
      .x = x,
      .y = y,
  };

  return size;
}

// Format of pixels in a bitmap
typedef enum {
  GFX_FORMAT_UNKNOWN,   //
  GFX_FORMAT_MONO1P,    // 1-bpp per pixel (packed)
  GFX_FORMAT_MONO4,     // 4-bpp per pixel
  GFX_FORMAT_RGB565,    // 16-bpp per pixel
  GFX_FORMAT_RGBA8888,  // 32-bpp
} gfx_format_t;

// Clears the display with a black color.
void gfx_clear(void);

// Fills a rectangle with a specified color.
void gfx_draw_bar(gfx_rect_t rect, gfx_color_t color);
