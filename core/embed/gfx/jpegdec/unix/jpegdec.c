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

#include <gfx/jpegdec.h>

struct jpegdec {
  int todo;
};

// Initialize and reset the decoder internal state
bool jpegdec_open(void) { return true; }

// Release the decoder and free resources
void jpegdec_close(void) {}

jpegdec_state_t jpegdec_process(jpegdec_input_t* input) {
  return JPEGDEC_STATE_ERROR;
}

bool jpegdec_get_info(jpegdec_image_t* info) { return false; }

bool jpegdec_get_slice_rgba8888(uint32_t* rgba8888, jpegdec_slice_t* slice) {
  return false;
}

bool jpegdec_get_slice_mono8(uint32_t* mono8, jpegdec_slice_t* slice) {
  return false;
}
