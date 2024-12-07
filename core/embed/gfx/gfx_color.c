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

#include <gfx/gfx_color.h>

const gfx_color16_t* gfx_color16_gradient_a4(gfx_color_t fg_color,
                                             gfx_color_t bg_color) {
  static gfx_color16_t cache[16] = {0};

  if (gfx_color_to_color16(bg_color) != cache[0] ||
      gfx_color_to_color16(fg_color) != cache[15]) {
    for (int alpha = 0; alpha < 16; alpha++) {
      cache[alpha] = gfx_color16_blend_a4(fg_color, bg_color, alpha);
    }
  }

  return cache;
}

const gfx_color32_t* gfx_color32_gradient_a4(gfx_color_t fg_color,
                                             gfx_color_t bg_color) {
  static gfx_color32_t cache[16] = {0};

  if (bg_color != gfx_color32_to_color(cache[0]) ||
      fg_color != gfx_color32_to_color(cache[15])) {
    for (int alpha = 0; alpha < 16; alpha++) {
      cache[alpha] = gfx_color32_blend_a4(fg_color, bg_color, alpha);
    }
  }

  return cache;
}
