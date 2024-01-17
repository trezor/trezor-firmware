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

#include "toif.h"
#include <stddef.h>
#include <string.h>

// see docs/misc/toif.md for definition of the TOIF format
bool toif_header_parse(const uint8_t *data, uint32_t len, uint16_t *out_w,
                       uint16_t *out_h, toif_format_t *out_format) {
  if (len < 12 || memcmp(data, "TOI", 3) != 0) {
    return false;
  }
  toif_format_t format = false;
  if (data[3] == 'f') {
    format = TOIF_FULL_COLOR_BE;
  } else if (data[3] == 'g') {
    format = TOIF_GRAYSCALE_OH;
  } else if (data[3] == 'F') {
    format = TOIF_FULL_COLOR_LE;
  } else if (data[3] == 'G') {
    format = TOIF_GRAYSCALE_EH;
  } else {
    return false;
  }

  uint16_t w = *(uint16_t *)(data + 4);
  uint16_t h = *(uint16_t *)(data + 6);

  uint32_t datalen = *(uint32_t *)(data + 8);
  if (datalen != len - 12) {
    return false;
  }

  if (out_w != NULL && out_h != NULL && out_format != NULL) {
    *out_w = w;
    *out_h = h;
    *out_format = format;
  }
  return true;
}
