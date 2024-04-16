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

#ifndef GL_DRAW_H
#define GL_DRAW_H

#include "gl_color.h"

// 2D rectangle coordinates
//
// `x0`, `y0` - top-left coordinates
// `x1`, `y1` - bottom-right coordinates point (not included)
typedef struct {
  int16_t x0;
  int16_t y0;
  int16_t x1;
  int16_t y1;
} gl_rect_t;

// Builds a rectangle (`gl_rect_t`) from top-left coordinates and dimensions
static inline gl_rect_t gl_rect_wh(int16_t x, int16_t y, int16_t w, int16_t h) {
  gl_rect_t rect = {
      .x0 = x,
      .y0 = y,
      .x1 = x + w,
      .y1 = y + h,
  };

  return rect;
}

// Builds a rectangle (`gl_rect_t`) from top-left and bottom-right coordinates
static inline gl_rect_t gl_rect(int16_t x0, int16_t y0, int16_t x1,
                                int16_t y1) {
  gl_rect_t rect = {
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
} gl_offset_t;

// Builds a `gl_offset_t` structure
static inline gl_offset_t gl_offset(int16_t x, int16_t y) {
  gl_offset_t offset = {
      .x = x,
      .y = y,
  };

  return offset;
}

// 2D size in pixels
typedef struct {
  int16_t x;
  int16_t y;
} gl_size_t;

// Builds a `gl_size_t` structure
static inline gl_size_t gl_size(int16_t x, int16_t y) {
  gl_size_t size = {
      .x = x,
      .y = y,
  };

  return size;
}

// Format of pixels in a bitmap
typedef enum {
  GL_FORMAT_UNKNOWN,   //
  GL_FORMAT_MONO1P,    // 1-bpp per pixel (packed)
  GL_FORMAT_MONO4,     // 4-bpp per pixel
  GL_FORMAT_RGB565,    // 16-bpp per pixel
  GL_FORMAT_RGBA8888,  // 32-bpp
} gl_format_t;

// 2D bitmap reference
typedef struct {
  // pointer to top-left pixel
  void* ptr;
  // stride in bytes
  size_t stride;
  // size in pixels
  gl_size_t size;
  // format of pixels, GL_FORMAT_xxx
  uint8_t format;
  // offset used when bitmap is drawed using gl_draw_bitmap()
  gl_offset_t offset;
  // foreground color (used with MONOx formats)
  gl_color_t fg_color;
  // background color (used with MONOx formats)
  gl_color_t bg_color;
} gl_bitmap_t;

// Text attributes (font and color)
typedef struct {
  // Font identifier
  int font;
  // Foreground color
  gl_color_t fg_color;
  // Background color
  gl_color_t bg_color;
} gl_text_attr_t;

// Fills a rectangle with a specified color.
void gl_draw_bar(gl_rect_t rect, gl_color_t color);

// Draws a bitmap into the specified rectangle.
//
// The destination rectangle may not be fully filled if the source bitmap
// is smaller then destination rectangle or if the bitmap is translated by
// an offset partially or completely outside the destination rectangle.
void gl_draw_bitmap(gl_rect_t rect, const gl_bitmap_t* bitmap);

// Draws a text to the specified position.
//
// `offset` - the most left point on the font baseline
// `text` - utf-8 text
// `maxlen` - maximum number of characters displayed (use SIZE_MAX when not
// specified) `attr` - font & text color
void gl_draw_text(gl_offset_t offset, const char* text, size_t maxlen,
                  const gl_text_attr_t* attr);

#endif  // GL_DRAW_H
