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

#include "buffers.h"
#include "common.h"
#include "fonts/fonts.h"
#include "memzero.h"

#if defined BOOTLOADER
#define BUFFER_SECTION __attribute__((section(".buf")))
#else
#define BUFFER_SECTION
#endif

#define BUFFERS_16BPP 3
#define BUFFERS_4BPP 3
#define BUFFERS_TEXT 1

const int32_t text_buffer_height = FONT_MAX_HEIGHT;
const int32_t buffer_width = DISPLAY_RESX;

BUFFER_SECTION line_buffer_16bpp_t line_buffers_16bpp[BUFFERS_16BPP];
BUFFER_SECTION line_buffer_4bpp_t line_buffers_4bpp[BUFFERS_4BPP];
BUFFER_SECTION buffer_text_t text_buffers[BUFFERS_TEXT];

line_buffer_16bpp_t* buffers_get_line_buffer_16bpp(uint16_t idx, bool clear) {
  if (idx >= BUFFERS_16BPP) {
    return NULL;
  }
  if (clear) {
    memzero(&line_buffers_16bpp[idx], sizeof(line_buffers_16bpp[idx]));
  }
  return &line_buffers_16bpp[idx];
}

line_buffer_4bpp_t* buffers_get_line_buffer_4bpp(uint16_t idx, bool clear) {
  if (idx >= BUFFERS_4BPP) {
    return NULL;
  }
  if (clear) {
    memzero(&line_buffers_4bpp[idx], sizeof(line_buffers_4bpp[idx]));
  }
  return &line_buffers_4bpp[idx];
}

buffer_text_t* buffers_get_text_buffer(uint16_t idx, bool clear) {
  if (idx >= BUFFERS_TEXT) {
    return NULL;
  }
  if (clear) {
    memzero(&text_buffers[idx], sizeof(text_buffers[idx]));
  }
  return &text_buffers[idx];
}
