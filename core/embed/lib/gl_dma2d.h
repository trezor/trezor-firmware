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

#ifndef GL_DMA2D_H
#define GL_DMA2D_H

#include <stdbool.h>
#include <stdint.h>

#include "gl_color.h"

typedef struct {
  // Destination bitma[
  // Following fields are used for all operations
  uint16_t height;
  uint16_t width;
  void* dst_row;
  uint16_t dst_x;
  uint16_t dst_y;
  uint16_t dst_stride;

  // Source bitmap
  // Used for copying and blending, but src_fg & src_alpha
  // fields are also used for fill operation
  void* src_row;
  uint16_t src_x;
  uint16_t src_y;
  uint16_t src_stride;
  gl_color_t src_fg;
  gl_color_t src_bg;
  uint8_t src_alpha;

} dma2d_params_t;

bool rgb565_fill(const dma2d_params_t* dp);
bool rgb565_copy_mono4(const dma2d_params_t* dp);
bool rgb565_copy_rgb565(const dma2d_params_t* dp);
bool rgb565_blend_mono4(const dma2d_params_t* dp);

bool rgba8888_fill(const dma2d_params_t* dp);
bool rgba8888_copy_mono4(const dma2d_params_t* dp);
bool rgba8888_copy_rgb565(const dma2d_params_t* dp);
bool rgba8888_copy_rgba8888(const dma2d_params_t* dp);
bool rgba8888_blend_mono4(const dma2d_params_t* dp);

bool mono8_fill(const dma2d_params_t* dp);
bool mono8_copy_mono1p(const dma2d_params_t* dp);
bool mono8_copy_mono4(const dma2d_params_t* dp);
bool mono8_blend_mono1p(const dma2d_params_t* dp);
bool mono8_blend_mono4(const dma2d_params_t* dp);

#endif  // GL_DMA2D_H