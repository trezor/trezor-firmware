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

static const char hex_chars[] = "0123456789ABCDEF";

bool cstr_encode_hex(char* dst, size_t dst_len, const void* src,
                     size_t src_len) {
  if (dst_len < src_len * 2 + 1) {
    if (dst_len > 0) {
      dst[0] = '\0';
    }
    return false;
  }

  for (size_t i = 0; i < src_len; i++) {
    dst[i * 2] = hex_chars[((uint8_t*)src)[i] >> 4];
    dst[i * 2 + 1] = hex_chars[((uint8_t*)src)[i] & 0x0F];
  }
  dst[src_len * 2] = '\0';

  return true;
}

bool cstr_append(char* dst, size_t dst_len, const char* src) {
  while (*dst != '\0' && dst_len > 1) {
    dst++;
    dst_len--;
  }

  while (*src != '\0' && dst_len > 1) {
    *dst++ = *src++;
    dst_len--;
  }

  if (dst_len > 0) {
    *dst = '\0';
  }

  return *src == '\0';
}

bool cstr_append_uint32(char* dst, size_t dst_len, uint32_t value) {
  char buffer[12] = "";
  char* p = buffer + sizeof(buffer) - 1;

  *p = '\0';

  if (value == 0) {
    *(--p) = '0';
  } else {
    while (value > 0) {
      *(--p) = (char)('0' + value % 10);
      value /= 10;
    }
  }

  return cstr_append(dst, dst_len, p);
}

bool cstr_append_int32(char* dst, size_t dst_len, int32_t value) {
  char buffer[12] = "";
  char* p = buffer + sizeof(buffer) - 1;

  *p = '\0';

  if (value == 0) {
    *(--p) = '0';
  } else {
    bool negative = value < 0;
    uint32_t abs_value = negative ? -value : value;

    while (abs_value > 0) {
      *(--p) = (char)('0' + abs_value % 10);
      abs_value /= 10;
    }

    if (negative) {
      *(--p) = '-';
    }
  }

  return cstr_append(dst, dst_len, p);
}

bool cstr_append_uint32_hex(char* dst, size_t dst_len, uint32_t value) {
  char temp[sizeof(value) * 2 + 1];
  for (int i = 2 * sizeof(value) - 1; i >= 0; i--) {
    temp[i] = hex_chars[value & 0x0F];
    value >>= 4;
  }
  temp[sizeof(temp) - 1] = '\0';
  return cstr_append(dst, dst_len, temp);
}
