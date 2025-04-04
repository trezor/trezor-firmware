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

#include <trezor_rtl.h>

#include <gfx/gfx_color.h>
#include <gfx/jpegdec.h>

#include <jpeglib.h>

#define MAX_SLICE_HEIGHT 16
#define MAX_SLICE_WIDTH \
  (JPEGDEC_RGBA8888_BUFFER_SIZE / (MAX_SLICE_HEIGHT * sizeof(uint32_t)))

// Custom source manager structure
typedef struct {
  struct jpeg_source_mgr pub;
  uint8_t buffer[4096];
  jpegdec_input_t *input;

} custom_source_mgr_t;

// Our internal decoder state.
struct jpegdec {
  bool inuse;

  // jpeglib context
  struct jpeg_decompress_struct cinfo;
  struct jpeg_error_mgr jerr;

  // Our custom source manager
  custom_source_mgr_t source_mgr;

  // Last decoder state
  jpegdec_state_t state;
  // Image info
  jpegdec_image_t image;

  // Up to MAX_SLICE_HEIGHT lines of decoded data in RGBA8888 format
  JSAMPARRAY slice_buffer;

  // Current slice coordinates
  int16_t slice_x;
  int16_t slice_y;
};

// JPEG decoder instance
jpegdec_t g_jpegdec = {
    .inuse = false,
};

//---------------------------------------------------------------------
// Custom source manager functions
//---------------------------------------------------------------------

static void init_source(j_decompress_ptr cinfo) {
  // No special initialization is needed.
  UNUSED(cinfo);
}

static boolean fill_input_buffer(j_decompress_ptr cinfo) {
  custom_source_mgr_t *src = (custom_source_mgr_t *)cinfo->src;
  jpegdec_input_t *input = src->input;

  if (input->offset < input->size) {
    size_t nbytes = MIN(input->size - input->offset, sizeof(src->buffer));
    memcpy(src->buffer, input->data + input->offset, nbytes);
    input->offset += nbytes;
    src->pub.next_input_byte = src->buffer;
    src->pub.bytes_in_buffer = nbytes;
    return TRUE;
  }

  // If no more data is available and this is the last chunk,
  // supply a fake EOI marker.

  if (input->last_chunk) {
    src->buffer[0] = 0xFF;
    src->buffer[1] = JPEG_EOI;
    src->pub.next_input_byte = src->buffer;
    src->pub.bytes_in_buffer = 2;
    return TRUE;
  }

  // No data available, but not the last chunk: suspend input
  return FALSE;
}

static void skip_input_data(j_decompress_ptr cinfo, long num_bytes) {
  custom_source_mgr_t *src = (custom_source_mgr_t *)cinfo->src;

  if (num_bytes > 0) {
    while (num_bytes > (long)src->pub.bytes_in_buffer) {
      num_bytes -= (long)src->pub.bytes_in_buffer;
      fill_input_buffer(cinfo);
    }
    src->pub.next_input_byte += num_bytes;
    src->pub.bytes_in_buffer -= num_bytes;
  }
}

static void term_source(j_decompress_ptr cinfo) {
  // No cleanup necessary
  UNUSED(cinfo);
}

//---------------------------------------------------------------------
// JPEG decoder functions
//---------------------------------------------------------------------

bool jpegdec_open(void) {
  jpegdec_t *dec = &g_jpegdec;

  if (dec->inuse) {
    return false;
  }

  memset(dec, 0, sizeof(jpegdec_t));
  dec->inuse = true;

  // Set up the JPEG decompression object with default error handling
  dec->cinfo.err = jpeg_std_error(&dec->jerr);
  jpeg_create_decompress(&dec->cinfo);

  // Init our custom source manager
  custom_source_mgr_t *src = &dec->source_mgr;
  src->pub.init_source = init_source;
  src->pub.fill_input_buffer = fill_input_buffer;
  src->pub.skip_input_data = skip_input_data;
  src->pub.resync_to_restart = jpeg_resync_to_restart;
  src->pub.term_source = term_source;
  src->pub.bytes_in_buffer = 0;
  src->pub.next_input_byte = NULL;
  src->input = NULL;
  dec->cinfo.src = (struct jpeg_source_mgr *)src;

  dec->state = JPEGDEC_STATE_NEED_DATA;

  return true;
}

jpegdec_state_t jpegdec_process(jpegdec_input_t *input) {
  jpegdec_t *dec = &g_jpegdec;

  if (!dec->inuse) {
    return JPEGDEC_STATE_ERROR;
  }

  dec->source_mgr.input = input;

  if (dec->state == JPEGDEC_STATE_SLICE_READY) {
    dec->slice_x += MAX_SLICE_WIDTH;
    if (dec->slice_x < dec->image.width) {
      // There is more data ready in the slice buffer
      return JPEGDEC_STATE_SLICE_READY;
    }
    dec->slice_x = 0;
    dec->slice_y = MIN(dec->image.height, dec->slice_y + MAX_SLICE_HEIGHT);

    if (dec->slice_y >= dec->image.height) {
      // The image is fully decoded
      dec->state = JPEGDEC_STATE_FINISHED;
      return dec->state;
    }
  }

  if (dec->state == JPEGDEC_STATE_FINISHED ||
      dec->state == JPEGDEC_STATE_ERROR) {
    // Do nothing if the decoder is finished or in error state
  } else if (dec->image.width == 0 && dec->image.height == 0) {
    // Decode jpeg headers and get image parameters
    int ret = jpeg_consume_input(&dec->cinfo);

    switch (ret) {
      case JPEG_SUSPENDED:
        dec->state = JPEGDEC_STATE_NEED_DATA;
        break;

      case JPEG_REACHED_SOS:
        dec->image.width = (int16_t)dec->cinfo.image_width;
        dec->image.height = (int16_t)dec->cinfo.image_height;

        if (dec->cinfo.num_components == 1) {
          dec->image.format = JPEGDEC_IMAGE_GRAYSCALE;
        } else if (dec->cinfo.num_components == 3) {
          int h = dec->cinfo.comp_info[0].h_samp_factor;
          int v = dec->cinfo.comp_info[0].v_samp_factor;
          if (h == 2 && v == 2)
            dec->image.format = JPEGDEC_IMAGE_YCBCR420;
          else if (h == 2 && v == 1)
            dec->image.format = JPEGDEC_IMAGE_YCBCR422;
          else
            dec->image.format = JPEGDEC_IMAGE_YCBCR444;
        } else {
          dec->state = JPEGDEC_STATE_ERROR;
          break;
        }

        dec->slice_x = 0;
        dec->slice_y = 0;

        // Set the output color space
        // (need to be set before jpeg_start_decompress)
        dec->cinfo.out_color_space = JCS_EXT_BGRA;

        jpeg_start_decompress(&dec->cinfo);

        // Allocate the output buffer
        dec->slice_buffer = (*dec->cinfo.mem->alloc_sarray)(
            (j_common_ptr)&dec->cinfo, JPOOL_IMAGE,
            dec->cinfo.output_width * dec->cinfo.output_components,
            MAX_SLICE_HEIGHT);

        dec->state = JPEGDEC_STATE_INFO_READY;
        break;

      default:
        dec->state = JPEGDEC_STATE_ERROR;
        break;
    }
  } else {
    // Image headers where decoded, now we can decode the image data
    // Read scanlines until we have a full slice

    for (;;) {
      // Row in slice buffer
      size_t row = dec->cinfo.output_scanline - dec->slice_y;

      if (row >= MAX_SLICE_HEIGHT) {
        dec->slice_y = dec->cinfo.output_scanline;
        row = 0;
      }

      int lines_read =
          jpeg_read_scanlines(&dec->cinfo, &dec->slice_buffer[row], 1);

      if (lines_read == 0) {
        dec->state = JPEGDEC_STATE_NEED_DATA;
        break;
      }

      if (row == MAX_SLICE_HEIGHT - 1 ||
          dec->cinfo.output_scanline >= dec->cinfo.output_height) {
        dec->state = JPEGDEC_STATE_SLICE_READY;
        break;
      }
    }
  }

  return dec->state;
}

bool jpegdec_get_info(jpegdec_image_t *image) {
  jpegdec_t *dec = &g_jpegdec;

  if (!dec->inuse) {
    return false;
  }

  if (dec->image.width == 0 || dec->image.height == 0) {
    return false;
  }

  *image = dec->image;
  return true;
}

bool jpegdec_get_slice_rgba8888(uint32_t *rgba8888, jpegdec_slice_t *slice) {
  jpegdec_t *dec = &g_jpegdec;

  if (!dec->inuse) {
    return false;
  }

  if (dec->state != JPEGDEC_STATE_SLICE_READY) {
    return false;
  }

  slice->x = dec->slice_x;
  slice->y = dec->slice_y;
  slice->width = MIN(dec->image.width - dec->slice_x, MAX_SLICE_WIDTH);
  slice->height = MIN(dec->image.height - dec->slice_y, MAX_SLICE_HEIGHT);

  for (int y = 0; y < slice->height; y++) {
    void *src = &((uint32_t *)dec->slice_buffer[y])[slice->x];
    void *dst = rgba8888 + y * slice->width;
    memcpy(dst, src, slice->width * sizeof(uint32_t));
  }

  return true;
}

bool jpegdec_get_slice_mono8(uint32_t *mono8, jpegdec_slice_t *slice) {
  jpegdec_t *dec = &g_jpegdec;

  if (!dec->inuse) {
    return false;
  }

  if (dec->state != JPEGDEC_STATE_SLICE_READY) {
    return false;
  }

  slice->x = dec->slice_x;
  slice->y = dec->slice_y;
  slice->width = MIN(dec->image.width - dec->slice_x, MAX_SLICE_WIDTH);
  slice->height = MIN(dec->image.height - dec->slice_y, MAX_SLICE_HEIGHT);

  uint8_t *dst = (uint8_t *)mono8;

  for (int y = 0; y < slice->height; y++) {
    for (int x = 0; x < slice->width; x++) {
      gfx_color32_t color = ((uint32_t *)dec->slice_buffer[y])[slice->x + x];
      dst[y * slice->width + x] = gfx_color32_lum(color);
    }
  }

  return true;
}

void jpegdec_close(void) {
  jpegdec_t *dec = &g_jpegdec;

  if (dec->inuse) {
    jpeg_destroy_decompress(&dec->cinfo);

    memset(dec, 0, sizeof(jpegdec_t));
  }
}
