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

#include "gdc_core.h"

#include <string.h>

static void gdc_rgba8888_release(gdc_t* gdc) {
  /* gdc_bitmap_t* bitmap = (gdc_bitmap_t*) gdc;

  if (bitmap->release != NULL) {
      bitmap->release(bitmap->context);
  }*/
}

static gdc_bitmap_t* gdc_rgba8888_get_bitmap(gdc_t* gdc) {
  return (gdc_bitmap_t*)gdc;
}

gdc_bitmap_t gdc_bitmap_rgba8888(void* data_ptr, size_t stride, gdc_size_t size,
                                 uint8_t attrs) {
  static const gdc_vmt_t gdc_rgba8888 = {
      .release = gdc_rgba8888_release,
      .get_bitmap = gdc_rgba8888_get_bitmap,
      .fill = NULL,           // dma2d_rgba8888_fill,
      .copy_mono4 = NULL,     // dma2d_rgba8888_copy_mono4,
      .copy_rgb565 = NULL,    // dma2d_rgba8888_copy_rgb565,
      .copy_rgba8888 = NULL,  // dma2d_rgba8888_copy_rgba8888,
      .blend_mono4 = NULL,    // dma2d_rgba8888_blend_mono4_mono4,
  };

  gdc_bitmap_t bitmap = {
      .vmt = &gdc_rgba8888,
      .ptr = data_ptr,
      .stride = stride,
      .size = size,
      .format = GDC_FORMAT_RGBA8888,
      .attrs = attrs,
  };

  return bitmap;
}
