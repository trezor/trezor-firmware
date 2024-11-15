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

#include <gfx/gfx_bitblt.h>

void gfx_mono8_fill(const gfx_bitblt_t* bb) {
  uint8_t* dst_ptr = (uint8_t*)bb->dst_row + bb->dst_x;
  uint16_t height = bb->height;

  uint8_t fg = gfx_color_lum(bb->src_fg);

  while (height-- > 0) {
    for (int x = 0; x < bb->width; x++) {
      dst_ptr[x] = fg;
    }
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
  }
}

void gfx_mono8_copy_mono1p(const gfx_bitblt_t* bb) {
  uint8_t* dst_ptr = (uint8_t*)bb->dst_row + bb->dst_x;
  uint8_t* src = (uint8_t*)bb->src_row;
  uint16_t src_ofs = bb->src_stride * bb->src_y + bb->src_x;
  uint16_t height = bb->height;

  uint8_t fg = gfx_color_lum(bb->src_fg);
  uint8_t bg = gfx_color_lum(bb->src_bg);

  while (height-- > 0) {
    for (int x = 0; x < bb->width; x++) {
      uint8_t mask = 1 << (7 - ((src_ofs + x) & 7));
      uint8_t data = src[(src_ofs + x) / 8];
      dst_ptr[x] = (data & mask) ? fg : bg;
    }
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ofs += bb->src_stride;
  }
}

void gfx_mono8_copy_mono4(const gfx_bitblt_t* bb) {
  uint8_t* dst_ptr = (uint8_t*)bb->dst_row + bb->dst_x;
  uint8_t* src_row = (uint8_t*)bb->src_row;
  uint16_t height = bb->height;

  uint8_t fg = gfx_color_lum(bb->src_fg);
  uint8_t bg = gfx_color_lum(bb->src_bg);

  while (height-- > 0) {
    for (int x = 0; x < bb->width; x++) {
      uint8_t src_data = src_row[(x + bb->src_x) / 2];
      uint8_t src_lum = (x + bb->src_x) & 1 ? src_data >> 4 : src_data & 0xF;
      dst_ptr[x] = (fg * src_lum + bg * (15 - src_lum)) / 15;
    }
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_row += bb->src_stride / sizeof(*src_row);
  }
}

void gfx_mono8_blend_mono1p(const gfx_bitblt_t* bb) {
  uint8_t* dst_ptr = (uint8_t*)bb->dst_row + bb->dst_x;
  uint8_t* src = (uint8_t*)bb->src_row;
  uint16_t src_ofs = bb->src_stride * bb->src_y + bb->src_x;
  uint16_t height = bb->height;

  uint8_t fg = gfx_color_lum(bb->src_fg);

  while (height-- > 0) {
    for (int x = 0; x < bb->width; x++) {
      uint8_t mask = 1 << (7 - ((src_ofs + x) & 7));
      uint8_t data = src[(src_ofs + x) / 8];
      dst_ptr[x] = (data & mask) ? fg : dst_ptr[x];
    }
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ofs += bb->src_stride;
  }
}

void gfx_mono8_blend_mono4(const gfx_bitblt_t* bb) {
  uint8_t* dst_ptr = (uint8_t*)bb->dst_row + bb->dst_x;
  uint8_t* src_row = (uint8_t*)bb->src_row;
  uint16_t height = bb->height;

  uint8_t fg = gfx_color_lum(bb->src_fg);

  while (height-- > 0) {
    for (int x = 0; x < bb->width; x++) {
      uint8_t src_data = src_row[(x + bb->src_x) / 2];
      uint8_t src_alpha = (x + bb->src_x) & 1 ? src_data >> 4 : src_data & 0x0F;
      src_alpha = src_alpha * bb->src_alpha / 15;
      dst_ptr[x] = (fg * src_alpha + dst_ptr[x] * (255 - src_alpha)) / 255;
    }
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_row += bb->src_stride / sizeof(*src_row);
  }
}
