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
#include "display_defs.h"

#define BUFFER_PIXELS DISPLAY_RESX

#define TEXT_BUFFER_HEIGHT 24

#if TEXT_BUFFER_HEIGHT < FONT_MAX_HEIGHT
#error Text buffer height is too small, please adjust to match used fonts
#endif

#define LINE_BUFFER_16BPP_SIZE BUFFER_PIXELS * 2
#define LINE_BUFFER_4BPP_SIZE BUFFER_PIXELS / 2
#define TEXT_BUFFER_SIZE (BUFFER_PIXELS * TEXT_BUFFER_HEIGHT) / 2

typedef __attribute__((aligned(4))) struct {
  uint8_t buffer[LINE_BUFFER_16BPP_SIZE];
} line_buffer_16bpp_t;

typedef __attribute__((aligned(4))) struct {
  uint8_t buffer[LINE_BUFFER_4BPP_SIZE];
} line_buffer_4bpp_t;

typedef __attribute__((aligned(4))) struct {
  uint8_t buffer[TEXT_BUFFER_SIZE];
} buffer_text_t;

extern const int32_t text_buffer_height;
extern const int32_t buffer_width;

line_buffer_16bpp_t* buffers_get_line_buffer_16bpp(uint16_t idx, bool clear);
line_buffer_4bpp_t* buffers_get_line_buffer_4bpp(uint16_t idx, bool clear);
buffer_text_t* buffers_get_text_buffer(uint16_t idx, bool clear);

#endif  //_BUFFERS_H
