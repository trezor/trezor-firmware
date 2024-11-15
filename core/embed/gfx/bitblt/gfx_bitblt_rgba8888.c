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

#if USE_DMA2D
#include "dma2d_bitblt.h"
#endif

void gfx_rgba8888_fill(const gfx_bitblt_t* bb) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (!dma2d_rgba8888_fill(bb))
#endif
  {
    uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
    uint16_t height = bb->height;

    if (bb->src_alpha == 255) {
      while (height-- > 0) {
        for (int x = 0; x < bb->width; x++) {
          dst_ptr[x] = gfx_color_to_color32(bb->src_fg);
        }
        dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
      }
    } else {
      uint8_t alpha = bb->src_alpha;
      while (height-- > 0) {
        for (int x = 0; x < bb->width; x++) {
          dst_ptr[x] = gfx_color32_blend_a8(
              bb->src_fg, gfx_color32_to_color(dst_ptr[x]), alpha);
        }
        dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
      }
    }
  }
}

void gfx_rgba8888_copy_mono1p(const gfx_bitblt_t* bb) {
  uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
  uint8_t* src = (uint8_t*)bb->src_row;
  uint16_t src_ofs = bb->src_stride * bb->src_y + bb->src_x;
  uint16_t height = bb->height;

  uint32_t fg = gfx_color_to_color32(bb->src_fg);
  uint32_t bg = gfx_color_to_color32(bb->src_bg);

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

void gfx_rgba8888_copy_mono4(const gfx_bitblt_t* bb) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (!dma2d_rgba8888_copy_mono4(bb))
#endif
  {
    const gfx_color32_t* gradient =
        gfx_color32_gradient_a4(bb->src_fg, bb->src_bg);

    uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
    uint8_t* src_row = (uint8_t*)bb->src_row;
    uint16_t height = bb->height;

    while (height-- > 0) {
      for (int x = 0; x < bb->width; x++) {
        uint8_t fg_data = src_row[(x + bb->src_x) / 2];
        uint8_t fg_lum = (x + bb->src_x) & 1 ? fg_data >> 4 : fg_data & 0xF;
        dst_ptr[x] = gradient[fg_lum];
      }
      dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
      src_row += bb->src_stride / sizeof(*src_row);
    }
  }
}

void gfx_rgba8888_copy_rgb565(const gfx_bitblt_t* bb) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (!dma2d_rgba8888_copy_rgb565(bb))
#endif
  {
    uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
    uint16_t* src_ptr = (uint16_t*)bb->src_row + bb->src_x;
    uint16_t height = bb->height;

    while (height-- > 0) {
      for (int x = 0; x < bb->width; x++) {
        dst_ptr[x] = gfx_color16_to_color32(src_ptr[x]);
      }
      dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
      src_ptr += bb->src_stride / sizeof(*src_ptr);
    }
  }
}

void gfx_rgba8888_copy_rgba8888(const gfx_bitblt_t* bb) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (!dma2d_rgba8888_copy_rgba8888(bb))
#endif
  {
    uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
    uint32_t* src_ptr = (uint32_t*)bb->src_row + bb->src_x;
    uint16_t height = bb->height;

    while (height-- > 0) {
      for (int x = 0; x < bb->width; x++) {
        dst_ptr[x] = src_ptr[x];
      }
      dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
      src_ptr += bb->src_stride / sizeof(*src_ptr);
    }
  }
}

void gfx_rgba8888_blend_mono4(const gfx_bitblt_t* bb) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (!dma2d_rgba8888_blend_mono4(bb))
#endif
  {
    uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
    uint8_t* src_row = (uint8_t*)bb->src_row;
    uint16_t height = bb->height;

    while (height-- > 0) {
      for (int x = 0; x < bb->width; x++) {
        uint8_t fg_data = src_row[(x + bb->src_x) / 2];
        uint8_t fg_alpha = (x + bb->src_x) & 1 ? fg_data >> 4 : fg_data & 0x0F;
        fg_alpha = fg_alpha * bb->src_alpha / 15;
        dst_ptr[x] = gfx_color32_blend_a8(
            bb->src_fg, gfx_color32_to_color(dst_ptr[x]), fg_alpha);
      }
      dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
      src_row += bb->src_stride / sizeof(*src_row);
    }
  }
}

void gfx_rgba8888_blend_mono8(const gfx_bitblt_t* bb) {
#if defined(USE_DMA2D) && !defined(TREZOR_EMULATOR)
  if (!dma2d_rgba8888_blend_mono8(bb))
#endif
  {
    uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
    uint8_t* src_ptr = (uint8_t*)bb->src_row + bb->src_x;
    uint16_t height = bb->height;

    while (height-- > 0) {
      for (int x = 0; x < bb->width; x++) {
        uint8_t fg_alpha = src_ptr[x];
        dst_ptr[x] = gfx_color32_blend_a8(
            bb->src_fg, gfx_color32_to_color(dst_ptr[x]), fg_alpha);
      }
      dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
      src_ptr += bb->src_stride / sizeof(*src_ptr);
    }
  }
}
