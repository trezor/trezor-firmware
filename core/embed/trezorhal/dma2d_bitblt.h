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

#ifndef TREZORHAL_DMA2D_BITBLT_H
#define TREZORHAL_DMA2D_BITBLT_H

#include "gl_bitblt.h"

// Returns `true` if the specified address is accessible by DMA2D
// and can be used by any of the following functions
bool dma2d_accessible(const void* ptr);

// Waits until any pending DMA2D operation is finished
void dma2d_wait(void);

// Following functions are hardware (DMA2D) accelerated versions
// of `gl_rgb565_xxx()` and `gl_rgba8888_xxx()` function from `gl_bitblt.h`

void dma2d_rgb565_fill(const gl_bitblt_t* bb);
void dma2d_rgb565_copy_mono4(const gl_bitblt_t* bb);
void dma2d_rgb565_copy_rgb565(const gl_bitblt_t* bb);
void dma2d_rgb565_blend_mono4(const gl_bitblt_t* bb);

void dma2d_rgba8888_fill(const gl_bitblt_t* bb);
void dma2d_rgba8888_copy_mono4(const gl_bitblt_t* bb);
void dma2d_rgba8888_copy_rgb565(const gl_bitblt_t* bb);
void dma2d_rgba8888_copy_rgba8888(const gl_bitblt_t* bb);
void dma2d_rgba8888_blend_mono4(const gl_bitblt_t* bb);

#endif  // TREZORHAL_DMA2D_BITBLT_H
