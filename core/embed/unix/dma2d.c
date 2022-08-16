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

#include "dma2d.h"
#include "colors.h"
#include "display_interface.h"

typedef enum {
  DMA2D_LAYER_FG = 1,
  DMA2D_LAYER_BG = 0,
} dma2d_layer_t;

typedef enum {
  DMA2D_MODE_CONST = 0,
  DMA2D_MODE_4BPP,
  DMA2D_MODE_16BPP,
  DMA2D_MODE_4BPP_OVER_4BPP,
  DMA2D_MODE_4BPP_OVER_16BPP,
} dma2d_mode_t;

static uint16_t clut_bg[16];
static uint16_t clut_fg[16];
static uint16_t dma2d_color;
static dma2d_mode_t mode = 0;

void dma2d_init(void) {
  // do nothing
}

void dma2d_init_clut(uint16_t fg, uint16_t bg, dma2d_layer_t layer) {
  uint16_t* table;
  if (layer == DMA2D_LAYER_BG) {
    table = clut_bg;
  } else {
    table = clut_fg;
  }

  set_color_table(table, fg, bg);
}

void dma2d_setup_const(void) { mode = DMA2D_MODE_CONST; }

void dma2d_setup_4bpp(uint16_t fg_color, uint16_t bg_color) {
  dma2d_init_clut(fg_color, bg_color, DMA2D_LAYER_FG);
  mode = DMA2D_MODE_4BPP;
}

void dma2d_setup_16bpp(void) { mode = DMA2D_MODE_16BPP; }

void dma2d_setup_4bpp_over_16bpp(uint16_t overlay_color) {
  mode = DMA2D_MODE_4BPP_OVER_16BPP;
  dma2d_color = overlay_color;
}

void dma2d_setup_4bpp_over_4bpp(uint16_t fg_color, uint16_t bg_color,
                                uint16_t overlay_color) {
  mode = DMA2D_MODE_4BPP_OVER_4BPP;

  dma2d_color = overlay_color;
  dma2d_init_clut(fg_color, bg_color, DMA2D_LAYER_BG);
}

void dma2d_start(uint8_t* in_addr, uint8_t* out_addr, int32_t pixels) {
  (void)out_addr;
  for (int i = 0; i < pixels; i++) {
    if (mode == DMA2D_MODE_4BPP) {
      uint8_t c = ((uint8_t*)in_addr)[i / 2];
      uint8_t even_pix = c >> 4;
      uint8_t odd_pix = c & 0xF;
      PIXELDATA(clut_fg[odd_pix]);
      PIXELDATA(clut_fg[even_pix]);
      i++;  // wrote two pixels
    }
    if (mode == DMA2D_MODE_16BPP) {
      uint16_t c = ((uint16_t*)in_addr)[i];
      PIXELDATA(c);
    }
  }
}

void dma2d_start_const(uint16_t color, uint8_t* out_addr, int32_t pixels) {
  (void)out_addr;
  for (int i = 0; i < pixels; i++) {
    PIXELDATA(color);
  }
}

void dma2d_start_blend(uint8_t* overlay_addr, uint8_t* bg_addr,
                       uint8_t* out_addr, int32_t pixels) {
  (void)out_addr;
  for (int i = 0; i < pixels; i++) {
    if (mode == DMA2D_MODE_4BPP_OVER_4BPP) {
      uint8_t c = overlay_addr[i / 2];
      uint8_t b = bg_addr[i / 2];

      uint8_t odd_overlay_pix = c & 0xF;
      uint8_t odd_bg_pix = b & 0xF;
      uint16_t c_odd_bg = clut_bg[odd_bg_pix];
      uint16_t final_odd_color =
          interpolate_color(dma2d_color, c_odd_bg, odd_overlay_pix);
      PIXELDATA(final_odd_color);

      uint8_t even_overlay_pix = c >> 4;
      uint8_t even_bg_pix = b >> 4;
      uint16_t c_even_bg = clut_bg[even_bg_pix];
      uint16_t final_even_color =
          interpolate_color(dma2d_color, c_even_bg, even_overlay_pix);
      PIXELDATA(final_even_color);

      i++;  // wrote two pixels
    }
    if (mode == DMA2D_MODE_4BPP_OVER_16BPP) {
      uint16_t c = ((uint16_t*)bg_addr)[i];
      uint8_t o = overlay_addr[i / 2];
      uint8_t o_pix;
      if (i % 2 == 0) {
        o_pix = o & 0xF;
      } else {
        o_pix = o >> 4;
      }
      uint16_t final_odd_color = interpolate_color(dma2d_color, c, o_pix);
      PIXELDATA(final_odd_color);
    }
  }
}

void dma2d_wait_for_transfer(void) {
  // done in place when emulating, so no need for wait here
}
