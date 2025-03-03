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

#pragma once

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
  // Downscaling for the source bitmap
  // (0 => no downscaling, 1 => 1/2, 2 => 1/4, 3 => 1/8)
  uint8_t src_downscale;

} gfx_bitblt_t;

#ifdef KERNEL_MODE

// Initializes bitblt operations
void gfx_bitblt_init(void);

// Deinitializes bitblt operations
void gfx_bitblt_deinit(void);

#endif  // KERNEL_MODE

// Checks if src_x and width are within the bounds of the source bitmap
static inline bool gfx_bitblt_check_src_x(const gfx_bitblt_t* bb,
                                          size_t pixel_bits) {
  return (bb->src_x + bb->width >= bb->src_x) &&  // overflow check
         (((bb->src_x + bb->width) * pixel_bits + 7) / 8 <= bb->src_stride);
}

// Checks if dst_x and width are within the bounds of the destination bitmap
static inline bool gfx_bitblt_check_dst_x(const gfx_bitblt_t* bb,
                                          size_t pixel_bits) {
  return (bb->dst_x + bb->width >= bb->dst_x) &&  // overflow check
         (((bb->dst_x + bb->width) * pixel_bits + 7) / 8 <= bb->dst_stride);
}

// Checks if dst_y and height are within the bounds of the destination bitmap
static inline bool gfx_bitblt_check_dst_y(const gfx_bitblt_t* bb,
                                          size_t fb_size) {
  return (bb->dst_y + bb->height >= bb->dst_y) &&  // overflow check
         (bb->dst_y + bb->height) * bb->dst_stride <= fb_size;
}

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
