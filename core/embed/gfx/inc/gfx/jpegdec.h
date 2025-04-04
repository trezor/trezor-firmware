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

// Maximum number of blocks (8x8) in a slice.
// The more blocks we use, the decodeer is faster.
// Minimum value is 4 to support 4:2:0 subsampling (MCU is 16x16).
#define JPEGDEC_MAX_SLICE_BLOCKS 16

// Size of Y/YCbCr data buffer
// The worst case is 192 bytes per block (8x8 pixels) for 4:4:4 subsampling
#define JPEGDEC_YCBCR_BUFFER_SIZE (JPEGDEC_MAX_SLICE_BLOCKS * 8 * 8 * 3)

// Maximum size of the RGBA8888 buffer for a slice.
#define JPEGDEC_RGBA8888_BUFFER_SIZE (JPEGDEC_MAX_SLICE_BLOCKS * 8 * 8 * 4)

// Maximum size of the MONO8 buffer for a slice
#define JPEGDEC_MONO8_BUFFER_SIZE (JPEGDEC_MAX_SLICE_BLOCKS * 8 * 8)

typedef struct jpegdec jpegdec_t;

typedef enum {
  // Decoder needs more data
  // (jpegdec_process should be called with more data)
  JPEGDEC_STATE_NEED_DATA,
  // Image info is ready
  // (jpegdec_get_info can be called to get the image info)
  JPEGDEC_STATE_INFO_READY,
  // Decoded slice is ready
  // (jpegdec_get_slice_xxx can be called to get the slice data)
  JPEGDEC_STATE_SLICE_READY,
  // Decoding is finished
  JPEGDEC_STATE_FINISHED,
  // Error occurred, decoding is stopped
  JPEGDEC_STATE_ERROR,
} jpegdec_state_t;

typedef enum {
  JPEGDEC_IMAGE_GRAYSCALE,  // Gray scale image
  JPEGDEC_IMAGE_YCBCR420,   // Color image with 4:2:0 subsampling
  JPEGDEC_IMAGE_YCBCR422,   // Color image with 4:2:2 subsampling
  JPEGDEC_IMAGE_YCBCR444,   // Color image with 4:4:4 subsampling
} jpegdec_image_format_t;

typedef struct {
  // Pointer to the data
  const uint8_t* data;
  // Size of the data in bytes
  size_t size;
  // Current offset in the data
  size_t offset;
  // Set to true when no more data is available
  bool last_chunk;
} jpegdec_input_t;

typedef struct {
  // Image format
  jpegdec_image_format_t format;
  // Image width in pixels
  int16_t width;
  // Image height in pixels
  int16_t height;
} jpegdec_image_t;

typedef struct {
  // Slice x-coordinate
  int16_t x;
  // Slice y-coordinate
  int16_t y;
  // Slice width
  int16_t width;
  // Slice height
  int16_t height;
} jpegdec_slice_t;

// Initialize and reset the decoder internal state
bool jpegdec_open(void);

// Release the decoder and free resources
void jpegdec_close(void);

// Process all or part of the input buffer and advances the `input->offset`
//
// `input->offset` must be aligned to 4 bytes.
// `input->size` must be aligned to 4 bytes except for the last chunk.
// `input->last_chunk` must be set to true when no more data is available.
//
// Returns the current state of the decoder:
// - `JPEGDEC_STATE_NEED_DATA` - more data is needed
// - `JPEGDEC_STATE_INFO_READY` - the image info is ready
// - `JPEGDEC_STATE_SLICE_READY` - a decoded slice is ready
// - `JPEGDEC_STATE_FINISHED` - the decoding is finished
// - `JPEGDEC_STATE_ERROR` - an error occurred
jpegdec_state_t jpegdec_process(jpegdec_input_t* input);

// Get the decoded image info
//
// Can be called anytimer if the decoder went through the
// `JPEGDEC_STATE_INFO_READY` state.
//
// Returns true if the info is available
bool jpegdec_get_info(jpegdec_image_t* info);

// Copy the last decoded slice to the buffer
//
// `rgba8888` must be a buffer of at least `JPEGDEC_RGBA8888_BUFFER_SIZE`
// bytes and must be aligned to 4 bytes.
//
// Can be called immediately after `jpegdec_process` returns
// `JPEGDEC_STATE_SLICE_READY`.
bool jpegdec_get_slice_rgba8888(uint32_t* rgba8888, jpegdec_slice_t* slice);

// Copy the last decoded slice to the buffer
//
// `mono8` must be a buffer of at least `JPEGDEC_MONO8_BUFFER_SIZE`
// bytes and must be aligned to 4 bytes.
//
// Can be called immediately after `jpegdec_process` returns
// `JPEGDEC_STATE_SLICE_READY`.
bool jpegdec_get_slice_mono8(uint32_t* mono8, jpegdec_slice_t* slice);
