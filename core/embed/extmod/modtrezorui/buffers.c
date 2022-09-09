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

#if USE_DMA2D

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

BUFFER_SECTION uint32_t line_buffer_16bpp[BUFFERS_16BPP][LINE_BUFFER_16BPP_SIZE / 4];
BUFFER_SECTION uint32_t line_buffer_4bpp[BUFFERS_4BPP][LINE_BUFFER_4BPP_SIZE / 4];
BUFFER_SECTION uint32_t text_buffer[BUFFERS_TEXT][TEXT_BUFFER_SIZE / 4];

uint8_t* buffers_get_line_buffer_16bpp(uint16_t idx, bool clear) {
  if (idx >= BUFFERS_16BPP) {
    return NULL;
  }
  if (clear) {
    memzero(line_buffer_16bpp[idx], sizeof(line_buffer_16bpp[idx]));
  }
  return (uint8_t*)line_buffer_16bpp[idx];
}

uint8_t* buffers_get_line_buffer_4bpp(uint16_t idx, bool clear) {
  if (idx >= BUFFERS_4BPP) {
    return NULL;
  }
  if (clear) {
    memzero(line_buffer_4bpp[idx], sizeof(line_buffer_4bpp[idx]));
  }
  return (uint8_t*)line_buffer_4bpp[idx];
}

uint8_t* buffers_get_text_buffer(uint16_t idx, bool clear) {
  if (idx >= BUFFERS_TEXT) {
    return NULL;
  }
  if (clear) {
    memzero(text_buffer[idx], sizeof(text_buffer[idx]));
  }
  return (uint8_t*)text_buffer[idx];
}

#endif
