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

#ifndef GDC_CORE_H
#define GDC_CORE_H

#include "gdc_bitmap.h"
#include "gdc_color.h"
#include "gdc_dma2d.h"
#include "gdc_geom.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// ------------------------------------------------------------------------
// GDC - Graphics Device Context
//

typedef void gdc_t;

// ------------------------------------------------------------------------
// GDC (Graphic Device Context) Virtual Method Table
//
// GDC structure is implementation specific. Only requirement is that
// it starts with a field of type gdc_vmt_t* vmt.
//
//    typedef struct
//    {
//        gdc_vmt_t* vmt;
//
//        // GDC specific data
//
//    } gdc_impl_specific_t;
//

typedef void (*gdc_release_t)(gdc_t* gdc);
typedef gdc_bitmap_t* (*gdc_get_bitmap_t)(gdc_t* gdc);
typedef bool (*gdc_fill_t)(gdc_t* gdc, dma2d_params_t* params);
typedef bool (*gdc_copy_mono4_t)(gdc_t* gdc, dma2d_params_t* params);
typedef bool (*gdc_copy_rgb565_t)(gdc_t* gdc, dma2d_params_t* params);
typedef bool (*gdc_copy_rgba8888_t)(gdc_t* gdc, dma2d_params_t* params);
typedef bool (*gdc_blend_mono4_t)(gdc_t* gdc, dma2d_params_t* params);

// GDC virtual methods
struct gdc_vmt {
  gdc_release_t release;
  gdc_get_bitmap_t get_bitmap;
  gdc_fill_t fill;
  gdc_copy_mono4_t copy_mono4;
  gdc_copy_rgb565_t copy_rgb565;
  gdc_copy_rgba8888_t copy_rgba8888;
  gdc_blend_mono4_t blend_mono4;
};

// ------------------------------------------------------------------------
// GDC (Graphic Device Context) Public API

// Releases reference to GDC
void gdc_release(gdc_t* gdc);

// Gets size of GDC bounding rectangle
gdc_size_t gdc_get_size(const gdc_t* gdc);

// Wait for pending DMA operation applied on this GDC
// (used by high level code before accessing GDC's framebuffer/bitmap)
void gdc_wait_for_pending_ops(gdc_t* gdc);

// Fills a rectangle with a specified color
bool gdc_fill_rect(gdc_t* gdc, gdc_rect_t rect, gdc_color_t color);

// Draws a bitmap into the specified rectangle
// The destination rectangle may not be fully filled if the source bitmap
// is smaller then destination rectangle or if the bitmap is translated by
// an offset partially or completely outside the destination rectangle.
bool gdc_draw_bitmap(gdc_t* gdc, gdc_rect_t rect, const gdc_bitmap_ref_t* src);

// Blends a bitmap with the gdc background in the specified rectangle.
// The destination rectangle may not be fully filled if the source bitmap
// is smaller then destination rectangle or if the bitmap is translated by
// an offset partially or completely outside the destination rectangle.
bool gdc_draw_blended(gdc_t* gdc, gdc_rect_t rect, const gdc_bitmap_ref_t* src);

// ------------------------------------------------------------------------
// this will be defined elsewhere::

// Gets GDC for the hardware display
// Returns NULL if display gdc was already acquired and not released
gdc_t* display_acquire_gdc(void);

#endif  // GDC_CORE_H
