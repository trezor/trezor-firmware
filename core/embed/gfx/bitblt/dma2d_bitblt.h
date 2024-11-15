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

#include <gfx/gfx_bitblt.h>

// Initializes DMA2D peripheral
void dma2d_init(void);

// Waits until any pending DMA2D operation is finished
void dma2d_wait(void);

// Following functions are hardware (DMA2D) accelerated versions
// of `gfx_rgb565_xxx()` and `gfx_rgba8888_xxx()` function from `gfx_bitblt.h`

// These functions may return `false`, indicating that the accelerated
// operation cannot be performed and must be implemented in software

bool dma2d_rgb565_fill(const gfx_bitblt_t* bb);
bool dma2d_rgb565_copy_mono4(const gfx_bitblt_t* bb);
bool dma2d_rgb565_copy_rgb565(const gfx_bitblt_t* bb);
bool dma2d_rgb565_blend_mono4(const gfx_bitblt_t* bb);
bool dma2d_rgb565_blend_mono8(const gfx_bitblt_t* bb);

bool dma2d_rgba8888_fill(const gfx_bitblt_t* bb);
bool dma2d_rgba8888_copy_mono4(const gfx_bitblt_t* bb);
bool dma2d_rgba8888_copy_rgb565(const gfx_bitblt_t* bb);
bool dma2d_rgba8888_copy_rgba8888(const gfx_bitblt_t* bb);
bool dma2d_rgba8888_blend_mono4(const gfx_bitblt_t* bb);
bool dma2d_rgba8888_blend_mono8(const gfx_bitblt_t* bb);

#endif  // TREZORHAL_DMA2D_BITBLT_H
