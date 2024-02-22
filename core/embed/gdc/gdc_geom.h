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

#ifndef GDC_GEOM_H
#define GDC_GEOM_H

// ------------------------------------------------------------------------
// GDC Rectangle
//
// used for simplified manipulation with rectangle coordinates

typedef struct {
  int16_t x0;
  int16_t y0;
  int16_t x1;
  int16_t y1;
} gdc_rect_t;

// Creates a rectangle from top-left coordinates and dimensions
static inline gdc_rect_t gdc_rect_wh(int16_t x, int16_t y, int16_t w,
                                     int16_t h) {
  gdc_rect_t rect = {
      .x0 = x,
      .y0 = y,
      .x1 = x + w,
      .y1 = y + h,
  };

  return rect;
}

// Creates a rectangle from top-left and bottom-right coordinates
static inline gdc_rect_t gdc_rect(int16_t x0, int16_t y0, int16_t x1,
                                  int16_t y1) {
  gdc_rect_t rect = {
      .x0 = x0,
      .y0 = y0,
      .x1 = x1,
      .y1 = y1,
  };

  return rect;
}

// ------------------------------------------------------------------------
// GDC Size
//
// used for simplified manipulation with size of objects

typedef struct {
  int16_t x;
  int16_t y;
} gdc_size_t;

// Creates a rectangle from top-left and bottom-right coordinates
static inline gdc_size_t gdc_size(int16_t x, int16_t y) {
  gdc_size_t size = {
      .x = x,
      .y = y,
  };

  return size;
}

// ------------------------------------------------------------------------
// GDC Offset
//
// used for simplified manipulation with size of objects

typedef gdc_size_t gdc_offset_t;

#endif  // GDC_GEOM_H
