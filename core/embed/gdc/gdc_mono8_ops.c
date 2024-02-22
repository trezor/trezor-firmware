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

#include "gdc_color.h"
#include "gdc_ops.h"

bool mono8_fill(const dma2d_params_t* dp) {
  uint8_t* dst_ptr = (uint8_t*)dp->dst_row + dp->dst_x;
  uint16_t height = dp->height;

  uint8_t fg = gdc_color_lum(dp->src_fg);

  while (height-- > 0) {
    for (int x = 0; x < dp->width; x++) {
      dst_ptr[x] = fg;
    }
    dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
  }

  return true;
}

bool mono8_copy_mono1p(const dma2d_params_t* dp) {
  uint8_t* dst_ptr = (uint8_t*)dp->dst_row + dp->dst_x;
  uint8_t* src = (uint8_t*)dp->src_row;
  uint16_t src_ofs = dp->src_stride * dp->src_y + dp->src_x;
  uint16_t height = dp->height;

  uint8_t fg = gdc_color_lum(dp->src_fg);
  uint8_t bg = gdc_color_lum(dp->src_bg);

  while (height-- > 0) {
    for (int x = 0; x < dp->width; x++) {
      uint8_t mask = 1 << (7 - ((src_ofs + x) & 7));
      uint8_t data = src[(src_ofs + x) / 8];
      dst_ptr[x] = (data & mask) ? fg : bg;
    }
    dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
    src_ofs += dp->src_stride;
  }

  return true;
}

bool mono8_copy_mono4(const dma2d_params_t* dp) {
  uint8_t* dst_ptr = (uint8_t*)dp->dst_row + dp->dst_x;
  uint8_t* src_row = (uint8_t*)dp->src_row;
  uint16_t height = dp->height;

  uint8_t fg = gdc_color_lum(dp->src_fg);
  uint8_t bg = gdc_color_lum(dp->src_bg);

  while (height-- > 0) {
    for (int x = 0; x < dp->width; x++) {
      uint8_t src_data = src_row[(x + dp->src_x) / 2];
      uint8_t src_lum = (x + dp->src_x) & 1 ? src_data >> 4 : src_data & 0xF;
      dst_ptr[x] = (fg * src_lum + bg * (15 - src_lum)) / 15;
    }
    dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
    src_row += dp->src_stride / sizeof(*src_row);
  }

  return true;
}

bool mono8_blend_mono1p(const dma2d_params_t* dp) {
  uint8_t* dst_ptr = (uint8_t*)dp->dst_row + dp->dst_x;
  uint8_t* src = (uint8_t*)dp->src_row;
  uint16_t src_ofs = dp->src_stride * dp->src_y + dp->src_x;
  uint16_t height = dp->height;

  uint8_t fg = gdc_color_lum(dp->src_fg);

  while (height-- > 0) {
    for (int x = 0; x < dp->width; x++) {
      uint8_t mask = 1 << (7 - ((src_ofs + x) & 7));
      uint8_t data = src[(src_ofs + x) / 8];
      dst_ptr[x] = (data & mask) ? fg : dst_ptr[x];
    }
    dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
    src_ofs += dp->src_stride;
  }

  return true;
}

bool mono8_blend_mono4(const dma2d_params_t* dp) {
  uint8_t* dst_ptr = (uint8_t*)dp->dst_row + dp->dst_x;
  uint8_t* src_row = (uint8_t*)dp->src_row;
  uint16_t height = dp->height;

  uint8_t fg = gdc_color_lum(dp->src_fg);

  while (height-- > 0) {
    for (int x = 0; x < dp->width; x++) {
      uint8_t src_data = src_row[(x + dp->src_x) / 2];
      uint8_t src_alpha = (x + dp->src_x) & 1 ? src_data >> 4 : src_data & 0x0F;
      dst_ptr[x] = (fg * src_alpha + dst_ptr[x] * (15 - src_alpha)) / 15;
    }
    dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
    src_row += dp->src_stride / sizeof(*src_row);
  }

  return true;
}
