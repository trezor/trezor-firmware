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

#include "gdc_ops.h"

#include "display.h"

static void set_window(const dma2d_params_t* dp) {
  display_set_window(dp->dst_x, dp->dst_y, dp->dst_x + dp->width - 1,
                     dp->dst_y + dp->height + 1);
}

bool wnd565_fill(const dma2d_params_t* dp) {
  set_window(dp);

  uint16_t height = dp->height;

  while (height-- > 0) {
    for (int x = 0; x < dp->width; x++) {
      PIXELDATA(dp->src_fg);
    }
  }

  return true;
}

bool wnd565_copy_rgb565(const dma2d_params_t* dp) {
  set_window(dp);

  uint16_t* src_ptr = (uint16_t*)dp->src_row + dp->src_x;
  uint16_t height = dp->height;

  while (height-- > 0) {
    for (int x = 0; x < dp->width; x++) {
      PIXELDATA(src_ptr[x]);
    }
    src_ptr += dp->src_stride / sizeof(*src_ptr);
  }

  return true;
}
