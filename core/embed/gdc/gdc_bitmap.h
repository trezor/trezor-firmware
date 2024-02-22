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

#ifndef GDC_BITMAP_H
#define GDC_BITMAP_H

#include "gdc_color.h"
#include "gdc_geom.h"

#include <stddef.h>
#include <stdint.h>

// forward declaration
typedef struct gdc_vmt gdc_vmt_t;

// ------------------------------------------------------------------------
// GDC Bitmap pixel format
//

typedef enum {
  GDC_FORMAT_UNKNOWN,   //
  GDC_FORMAT_MONO1,     // 1-bpp per pixel
  GDC_FORMAT_MONO4,     // 4-bpp per pixel
  GDC_FORMAT_RGB565,    // 16-bpp per pixel
  GDC_FORMAT_RGBA8888,  // 32-bpp

} gdc_format_t;

// ------------------------------------------------------------------------
// GDC Bitmap Attributes
//

#define GDC_BITMAP_READ_ONLY 0x01  // Read-only data
// #define GDC_BITMAP_DMA_READ    0x02 // DMA read pending
// #define GDC_BITMAP_DMA_WRITE   0x04 // DMA write pending

// ------------------------------------------------------------------------
// GDC Bitmap
//
// Structure holding pointer to the bitmap data, its format and sizes
//
// Note: gdc_bitmap_t itself can be used as GDC as long as it contains
// valid gdc virtual table pointer.

typedef struct gdc_bitmap {
  // GDC virtual method table
  // (must be the first field of the structure)
  const gdc_vmt_t* vmt;
  // pointer to top-left pixel
  void* ptr;
  // stride in bytes
  size_t stride;
  // size in pixels
  gdc_size_t size;
  // format of pixels, GDC_FORMAT_xxx
  uint8_t format;
  // attributes, GDC_BITMAP_xxx
  uint8_t attrs;

} gdc_bitmap_t;

// Initializes RGB565 bitmap structure
// GDC and format fields and filled automatically.
gdc_bitmap_t gdc_bitmap_rgb565(void* data_ptr, size_t stride, gdc_size_t size,
                               uint8_t attrs);

// Initializes RGBA8888 bitmap structure
// GDC and format fields and filled automatically.
gdc_bitmap_t gdc_bitmap_rgba8888(void* data_ptr, size_t stride, gdc_size_t size,
                                 uint8_t attrs);

// ------------------------------------------------------------------------
// GDC Bitmap reference
//
// Structure is used when bitmap is beeing drawed to supply
// additional parameters

typedef struct {
  // soruce bitmap
  const gdc_bitmap_t* bitmap;
  // offset used when bitmap is drawed on gdc
  gdc_offset_t offset;
  // foreground color (used with MONOx formats)
  gdc_color_t fg_color;
  // background color (used with MONOx formats)
  gdc_color_t bg_color;

} gdc_bitmap_ref_t;

#endif  // GDC_BITMAP_H
