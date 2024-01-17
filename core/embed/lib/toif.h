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

#ifndef LIB_TOIF_H
#define LIB_TOIF_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
  TOIF_FULL_COLOR_BE = 0,  // big endian
  TOIF_GRAYSCALE_OH = 1,   // odd hi
  TOIF_FULL_COLOR_LE = 2,  // little endian
  TOIF_GRAYSCALE_EH = 3,   // even hi
} toif_format_t;

bool toif_header_parse(const uint8_t *buf, uint32_t len, uint16_t *out_w,
                       uint16_t *out_h, toif_format_t *out_format);

#endif  // LIB_TOIF_H
