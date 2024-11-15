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

#ifndef GFX_BITBLT_H
#define GFX_BITBLT_H

#include <trezor_types.h>

#include <gfx/gfx_color.h>

// These module provides low-level bit block transfer (bitblt)
// operations on different bitmap/framebuffer types.
//
// `fill` - fills a rectangle with a solid color (with an optional
//          alpha, allowing color blending).
//
// `copy` - copies a bitmap or part of it to the destination bitmap.
//
// `blend` - blends a bitmap with a 1- or 4-bit alpha channel to the
//           destination using background and foreground colors.
//
// These operations might be accelerated using DMA2D (ChromART accelerator)
// on the STM32 platform.

// Represents a set of parameters for a bit block transfer operation.
typedef struct {
  // Pointer to the destination bitmap's first row
  void* dst_row;
  // Number of bytes per line in the destination bitmap
  uint16_t dst_stride;
  // X-coordinate of the top-left corner inside the destination
  uint16_t dst_x;
  // Y-coordinate of the top-left corner inside the destination
  uint16_t dst_y;
  // Height of the filled/copied/blended area
  uint16_t height;
  // Width of the filled/copied/blended area
  uint16_t width;

  // Pointer to the source bitmap's first row
  // (unused for fill operations)
  void* src_row;
  // Number of bytes per line in the source bitmap
  // (unused for fill operations)
  uint16_t src_stride;
  // X-coordinate of the origin in the source bitmap
  // (unused for fill operations)
  uint16_t src_x;
  // Y-coordinate of the origin in the source bitmap
  // (unused for fill operations)
  uint16_t src_y;

  // Foreground color used when copying/blending/filling
  gfx_color_t src_fg;
  // Background color used when copying mono bitmaps
  gfx_color_t src_bg;
  // Alpha value for fill operation (255 => normal fill, 0 => noop)
  uint8_t src_alpha;

} gfx_bitblt_t;

// Initializes bitblt operations
void gfx_bitblt_init(void);

// If the bitblt operation is asynchronous, waits until it's finished
void gfx_bitblt_wait(void);

// Functions for RGB565 bitmap/framebuffer

// Fills a rectangle with a solid color
void gfx_rgb565_fill(const gfx_bitblt_t* bb);
// Copies a mono bitmap (with 1-bit alpha channel)
void gfx_rgb565_copy_mono1p(const gfx_bitblt_t* bb);
// Copies a mono bitmap (with 4-bit alpha channel)
void gfx_rgb565_copy_mono4(const gfx_bitblt_t* bb);
// Copies an RGB565 bitmap
void gfx_rgb565_copy_rgb565(const gfx_bitblt_t* bb);
// Blends a mono bitmap (with 4-bit alpha channel)
// with the destination bitmap
void gfx_rgb565_blend_mono4(const gfx_bitblt_t* bb);
// Blends a mono bitmap (with 8-bit alpha channel)
// with the destination bitmap
void gfx_rgb565_blend_mono8(const gfx_bitblt_t* bb);

// Functions for RGBA8888 bitmap/framebuffer
void gfx_rgba8888_fill(const gfx_bitblt_t* bb);
// Copies a mono bitmap (with 1-bit alpha channel)
void gfx_rgba8888_copy_mono1p(const gfx_bitblt_t* bb);
// Copies a mono bitmap (with 4-bit alpha channel)
void gfx_rgba8888_copy_mono4(const gfx_bitblt_t* bb);
// Copies an RGB565 bitmap
void gfx_rgba8888_copy_rgb565(const gfx_bitblt_t* bb);
// Copies an RGBA8888 bitmap
void gfx_rgba8888_copy_rgba8888(const gfx_bitblt_t* bb);
// Blends a mono bitmap (with 4-bit alpha channel)
// with the destination bitmap
void gfx_rgba8888_blend_mono4(const gfx_bitblt_t* bb);
// Blends a mono bitmap (with 8-bit alpha channel)
// with the destination bitmap
void gfx_rgba8888_blend_mono8(const gfx_bitblt_t* bb);

// Functions for Mono8 bitmap/framebuffer
void gfx_mono8_fill(const gfx_bitblt_t* bb);
// Copies a mono bitmap (with 1-bit alpha channel)
void gfx_mono8_copy_mono1p(const gfx_bitblt_t* bb);
// Copies a mono bitmap (with 4-bit alpha channel)
void gfx_mono8_copy_mono4(const gfx_bitblt_t* bb);
// Blends a mono bitmap (with 1-bit alpha channel)
// with the destination bitmap
void gfx_mono8_blend_mono1p(const gfx_bitblt_t* bb);
// Blends a mono bitmap (with 4-bit alpha channel)
// with the destination bitmap
void gfx_mono8_blend_mono4(const gfx_bitblt_t* bb);

#endif  // GFX_BITBLT_H
