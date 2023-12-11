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

#ifndef _BUFFERS_H
#define _BUFFERS_H

#include <stdbool.h>

#include "common.h"
#include TREZOR_BOARD

#define BUFFER_PIXELS DISPLAY_RESX

#define TEXT_BUFFER_HEIGHT 36

#if TEXT_BUFFER_HEIGHT < FONT_MAX_HEIGHT
#error Text buffer height is too small, please adjust to match used fonts
#endif

#define LINE_BUFFER_16BPP_SIZE (BUFFER_PIXELS * 2)
#define LINE_BUFFER_4BPP_SIZE (BUFFER_PIXELS / 2)
#define TEXT_BUFFER_SIZE ((BUFFER_PIXELS * TEXT_BUFFER_HEIGHT) / 2)
#define JPEG_BUFFER_SIZE (BUFFER_PIXELS * 16)

// 3100 is needed according to tjpgd docs,
// 256 because we need non overlapping memory in rust
// 6 << 10 is for huffman decoding table
// 1000 bytes reserve, as we discovered that we are running out of memory
// sometimes
#define JPEG_WORK_SIZE (3100 + 256 + (6 << 10) + 1000)

#if defined BOOTLOADER
#define BUFFER_SECTION __attribute__((section(".buf")))
#else
#define BUFFER_SECTION
#endif

#if defined BOOTLOADER || defined TREZOR_EMULATOR
#define NODMA_BUFFER_SECTION
#else
#define NODMA_BUFFER_SECTION __attribute__((section(".no_dma_buffers")))
#endif

typedef __attribute__((aligned(4))) struct {
  uint8_t buffer[LINE_BUFFER_16BPP_SIZE];
} buffer_line_16bpp_t;

typedef __attribute__((aligned(4))) struct {
  uint8_t buffer[LINE_BUFFER_4BPP_SIZE];
} buffer_line_4bpp_t;

typedef __attribute__((aligned(4))) struct {
  uint8_t buffer[TEXT_BUFFER_SIZE];
} buffer_text_t;

typedef __attribute__((aligned(4))) struct {
  uint16_t buffer[JPEG_BUFFER_SIZE];
} buffer_jpeg_t;

typedef __attribute__((aligned(4))) struct {
  uint8_t buffer[JPEG_WORK_SIZE];
} buffer_jpeg_work_t;

typedef __attribute__((aligned(4))) struct {
  uint16_t buffer[10][3][BUFFER_PIXELS];
} buffer_blurring_t;

typedef __attribute__((aligned(4))) struct {
  uint16_t buffer[3][BUFFER_PIXELS];
} buffer_blurring_totals_t;

extern const int32_t text_buffer_height;
extern const int32_t buffer_width;

buffer_line_16bpp_t* buffers_get_line_16bpp(bool clear);
void buffers_free_line_16bpp(buffer_line_16bpp_t* buffer);

buffer_line_4bpp_t* buffers_get_line_4bpp(bool clear);
void buffers_free_line_4bpp(buffer_line_4bpp_t* buffer);

buffer_text_t* buffers_get_text(bool clear);
void buffers_free_text(buffer_text_t* buffer);

buffer_jpeg_t* buffers_get_jpeg(bool clear);
void buffers_free_jpeg(buffer_jpeg_t* buffer);

buffer_jpeg_work_t* buffers_get_jpeg_work(bool clear);
void buffers_free_jpeg_work(buffer_jpeg_work_t* buffer);

buffer_blurring_t* buffers_get_blurring(bool clear);
void buffers_free_blurring(buffer_blurring_t* buffer);

buffer_blurring_totals_t* buffers_get_blurring_totals(bool clear);
void buffers_free_blurring_totals(buffer_blurring_totals_t* buffer);

#endif  // _BUFFERS_H
