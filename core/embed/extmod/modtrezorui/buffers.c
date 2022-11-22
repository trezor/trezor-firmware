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

#define BUFFERS_16BPP 3
#define BUFFERS_4BPP 3
#define BUFFERS_TEXT 1
#define BUFFERS_JPEG 1
#define BUFFERS_JPEG_WORK 1
#define BUFFERS_BLURRING 1

const int32_t text_buffer_height = FONT_MAX_HEIGHT;
const int32_t buffer_width = DISPLAY_RESX;

BUFFER_SECTION line_buffer_16bpp_t line_buffers_16bpp[BUFFERS_16BPP];
BUFFER_SECTION line_buffer_4bpp_t line_buffers_4bpp[BUFFERS_4BPP];
BUFFER_SECTION buffer_text_t text_buffers[BUFFERS_TEXT];
NODMA_BUFFER_SECTION buffer_jpeg_t jpeg_buffers[BUFFERS_JPEG];
NODMA_BUFFER_SECTION buffer_jpeg_work_t jpeg_work_buffers[BUFFERS_JPEG_WORK];
NODMA_BUFFER_SECTION buffer_blurring_t blurring_buffers[BUFFERS_BLURRING];

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

buffer_jpeg_t* buffers_get_jpeg_buffer(uint16_t idx, bool clear) {
  if (idx >= BUFFERS_JPEG) {
    return NULL;
  }

  if (clear) {
    memzero(&jpeg_buffers[idx], sizeof(jpeg_buffers[idx]));
  }
  return &jpeg_buffers[idx];
}

buffer_jpeg_work_t* buffers_get_jpeg_work_buffer(uint16_t idx, bool clear) {
  if (idx >= BUFFERS_JPEG_WORK) {
    return NULL;
  }

  if (clear) {
    memzero(&jpeg_work_buffers[idx], sizeof(jpeg_work_buffers[idx]));
  }
  return &jpeg_work_buffers[idx];
}

buffer_blurring_t* buffers_get_blurring_buffer(uint16_t idx, bool clear) {
  if (idx >= BUFFERS_BLURRING) {
    return NULL;
  }

  if (clear) {
    memzero(&blurring_buffers[idx], sizeof(blurring_buffers[idx]));
  }
  return &blurring_buffers[idx];
}
