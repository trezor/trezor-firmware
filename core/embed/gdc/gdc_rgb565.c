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
#include "gdc_dma2d.h"
#include "gdc_ops.h"

#include <string.h>

static void gdc_rgb565_release(gdc_t* gdc) {
  /* gdc_bitmap_t* bitmap = (gdc_bitmap_t*) gdc;

  if (bitmap->release != NULL) {
      bitmap->release(bitmap->context);
  }*/
}

static gdc_bitmap_t* gdc_rgb565_get_bitmap(gdc_t* gdc) {
  return (gdc_bitmap_t*)gdc;
}

static bool gdc_rgb565_fill(gdc_t* gdc, dma2d_params_t* params) {
  return rgb565_fill(params);
}

static bool gdc_rgb565_copy_mono4(gdc_t* gdc, dma2d_params_t* params) {
  return rgb565_copy_mono4(params);
}

static bool gdc_rgb565_copy_rgb565(gdc_t* gdc, dma2d_params_t* params) {
  return rgb565_copy_rgb565(params);
}

static bool gdc_rgb565_blend_mono4(gdc_t* gdc, dma2d_params_t* params) {
  return rgb565_blend_mono4(params);
}

gdc_bitmap_t gdc_bitmap_rgb565(void* data_ptr, size_t stride, gdc_size_t size,
                               uint8_t attrs) {
  static const gdc_vmt_t gdc_rgb565 = {
      .release = gdc_rgb565_release,
      .get_bitmap = gdc_rgb565_get_bitmap,
      .fill = gdc_rgb565_fill,
      .copy_mono4 = gdc_rgb565_copy_mono4,
      .copy_rgb565 = gdc_rgb565_copy_rgb565,
      .copy_rgba8888 = NULL,
      .blend_mono4 = gdc_rgb565_blend_mono4,
  };

  gdc_bitmap_t bitmap = {.vmt = &gdc_rgb565,
                         .ptr = data_ptr,
                         .stride = stride,
                         .size = size,
                         .format = GDC_FORMAT_RGB565,
                         .attrs = attrs};

  return bitmap;
}
