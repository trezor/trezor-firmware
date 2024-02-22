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

#include "gdc_wnd565.h"
#include "gdc_ops.h"

#include <string.h>

#include "display.h"

static void gdc_wnd565_release(gdc_t* gdc) {
  // gdc_wnd565_t* wnd = (gdc_wnd565_t*)gdc;

  // if (wnd->config.release != NULL) {
  //   wnd->config.release(wnd->config.context);
  // }
}

static gdc_bitmap_t* gdc_wnd565_get_bitmap(gdc_t* gdc) {
  return &((gdc_wnd565_t*)gdc)->bitmap;
}

static bool gdc_wnd565_fill(gdc_t* gdc, dma2d_params_t* params) {
  return wnd565_fill(params);
}

static bool gdc_wnd565_copy_rgb565(gdc_t* gdc, dma2d_params_t* params) {
  return wnd565_copy_rgb565(params);
}

gdc_t* gdc_wnd565_init(gdc_wnd565_t* gdc, gdc_wnd565_config_t* config) {
  static const gdc_vmt_t gdc_wnd565 = {
      .release = gdc_wnd565_release,
      .get_bitmap = gdc_wnd565_get_bitmap,
      .fill = gdc_wnd565_fill,
      .copy_mono4 = NULL,  // gdc_wnd565_copy_mono4,
      .copy_rgb565 = gdc_wnd565_copy_rgb565,
      .copy_rgba8888 = NULL,
      .blend_mono4 = NULL,
  };

  memset(gdc, 0, sizeof(gdc_wnd565_t));
  gdc->vmt = &gdc_wnd565;
  gdc->bitmap.format = GDC_FORMAT_RGB565;
  gdc->bitmap.size = config->size;
  gdc->bitmap.ptr = (void*)config->reg_address;

  return (gdc_t*)&gdc->vmt;
}

gdc_t* display_acquire_gdc(void) {
  static gdc_wnd565_t wnd = {};

  if (wnd.vmt == NULL) {
    gdc_wnd565_config_t config = {
        .size.x = 240,
        .size.y = 240,
    };
    gdc_wnd565_init(&wnd, &config);
  }

  return (gdc_t*)&wnd.vmt;
}
