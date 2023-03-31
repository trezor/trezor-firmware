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

#ifndef _COLORS_H
#define _COLORS_H

#include "common.h"

#ifdef TREZOR_MODEL_T
#define RGB16(R, G, B) ((R & 0xF8) << 8) | ((G & 0xFC) << 3) | ((B & 0xF8) >> 3)
#endif

#define COLOR_WHITE 0xFFFF
#define COLOR_BLACK 0x0000

static inline uint16_t interpolate_color(uint16_t color0, uint16_t color1,
                                         uint8_t step) {
  uint8_t cr = 0, cg = 0, cb = 0;
  cr = (((color0 & 0xF800) >> 11) * step +
        ((color1 & 0xF800) >> 11) * (15 - step)) /
       15;
  cg = (((color0 & 0x07E0) >> 5) * step +
        ((color1 & 0x07E0) >> 5) * (15 - step)) /
       15;
  cb = ((color0 & 0x001F) * step + (color1 & 0x001F) * (15 - step)) / 15;
  return (cr << 11) | (cg << 5) | cb;
}

static inline void set_color_table(uint16_t colortable[16], uint16_t fgcolor,
                                   uint16_t bgcolor) {
  for (int i = 0; i < 16; i++) {
    colortable[i] = interpolate_color(fgcolor, bgcolor, i);
  }
}

uint32_t rgb565_to_rgb888(uint16_t color);

uint32_t interpolate_rgb888_color(uint32_t color0, uint32_t color1,
                                  uint8_t step);

#endif  //_COLORS_H
