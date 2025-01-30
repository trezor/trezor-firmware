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

#include <rtl/strutils.h>

#include <ctype.h>
#include <stdlib.h>

bool cstr_parse_int32(const char* str, int base, int32_t* result) {
  char* endptr;
  int32_t value = strtol(str, &endptr, base);
  if (endptr > str && endptr == str + strlen(str)) {
    *result = value;
    return true;
  } else {
    return false;
  }
}

bool cstr_parse_uint32(const char* str, int base, uint32_t* result) {
  char* endptr;
  uint32_t value = strtoul(str, &endptr, base);
  if (endptr > str && endptr == str + strlen(str)) {
    *result = value;
    return true;
  } else {
    return false;
  }
}

const char* cstr_skip_whitespace(const char* str) {
  while (isspace((unsigned char)*str)) {
    str++;
  }
  return str;
}

bool cstr_starts_with(const char* str, const char* prefix) {
  size_t prefix_len = strlen(prefix);
  return strlen(str) >= prefix_len && 0 == strncmp(str, prefix, prefix_len);
}

static inline bool parse_nibble(char c, uint32_t* value) {
  uint8_t nibble = 0;

  if (c >= '0' && c <= '9') {
    nibble = c - '0';
  } else if (c >= 'A' && c <= 'F') {
    nibble = c - 'A' + 10;
  } else if (c >= 'a' && c <= 'f') {
    nibble = c - 'a' + 10;
  } else {
    return false;
  }

  *value = (*value << 4) + nibble;
  return true;
}

bool cstr_decode_hex(const char* str, uint8_t* dst, size_t dst_len,
                     size_t* bytes_written) {
  size_t idx = 0;

  while (idx < dst_len) {
    str = cstr_skip_whitespace(str);
    uint32_t value = 0;
    if (!parse_nibble(str[0], &value)) break;
    if (!parse_nibble(str[1], &value)) break;
    dst[idx++] = value;
    str += 2;
  }

  *bytes_written = idx;

  return *cstr_skip_whitespace(str) == '\0';
}

bool cstr_encode_hex(char* dst, size_t dst_len, const void* src,
                     size_t src_len) {
  static const char hex[] = "0123456789ABCDEF";

  if (dst_len < src_len * 2 + 1) {
    if (dst_len > 0) {
      dst[0] = '\0';
    }
    return false;
  }

  for (size_t i = 0; i < src_len; i++) {
    dst[i * 2] = hex[((uint8_t*)src)[i] >> 4];
    dst[i * 2 + 1] = hex[((uint8_t*)src)[i] & 0x0F];
  }
  dst[src_len * 2] = '\0';

  return true;
}
