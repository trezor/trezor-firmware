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

#include "colors.h"

uint32_t rgb565_to_rgb888(uint16_t color) {
  uint32_t res = 0;
  res |= ((((((uint32_t)color & 0xF800) >> 11) * 527) + 23) >> 6) << 16;
  res |= ((((((uint32_t)color & 0x07E0) >> 5) * 259) + 33) >> 6) << 8;
  res |= ((((((uint32_t)color & 0x001F) >> 0) * 527) + 23) >> 6) << 0;
  res |= 0xFF000000;
  return res;
}

uint32_t interpolate_rgb888_color(uint32_t color0, uint32_t color1,
                                  uint8_t step) {
  uint32_t cr, cg, cb;
  cr = (((color0 & 0xFF0000) >> 16) * step +
        ((color1 & 0xFF0000) >> 16) * (15 - step)) /
       15;
  cg = (((color0 & 0xFF00) >> 8) * step +
        ((color1 & 0xFF00) >> 8) * (15 - step)) /
       15;
  cb = ((color0 & 0x00FF) * step + (color1 & 0x00FF) * (15 - step)) / 15;
  return (cr << 16) | (cg << 8) | cb | 0xFF000000;
}
