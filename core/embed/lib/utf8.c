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

#include "utf8.h"

#define UTF8_IS_CONT(ch) (((ch)&0xC0) == 0x80)

void utf8_substr(const char *buf_start, size_t buf_len, int char_off,
                         int char_len, const char **out_start, int *out_len) {
  size_t i = 0;

  for (; i < buf_len; i++) {
    if (char_off == 0) {
      break;
    }
    if (!UTF8_IS_CONT(buf_start[i])) {
      char_off--;
    }
  }
  size_t i_start = i;

  for (; i < buf_len; i++) {
    if (char_len == 0) {
      break;
    }
    if (!UTF8_IS_CONT(buf_start[i])) {
      char_len--;
    }
  }

  for (; i < buf_len; i++) {
    if (!UTF8_IS_CONT(buf_start[i])) {
      break;
    }
  }

  *out_start = buf_start + i_start;
  *out_len = i - i_start;
}
