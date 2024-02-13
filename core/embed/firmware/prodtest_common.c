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

#include "prodtest_common.h"
#include "mini_printf.h"
#include "usb.h"

void vcp_puts(const char *s, size_t len) {
  int r = usb_vcp_write_blocking(VCP_IFACE, (const uint8_t *)s, len, -1);
  (void)r;
}

void vcp_print(const char *fmt, ...) {
  static char buf[128];
  va_list va;
  va_start(va, fmt);
  int r = mini_vsnprintf(buf, sizeof(buf), fmt, va);
  va_end(va);
  vcp_puts(buf, r);
}

void vcp_println(const char *fmt, ...) {
  static char buf[128];
  va_list va;
  va_start(va, fmt);
  int r = mini_vsnprintf(buf, sizeof(buf), fmt, va);
  va_end(va);
  vcp_puts(buf, r);
  vcp_puts("\r\n", 2);
}

void vcp_println_hex(uint8_t *data, uint16_t len) {
  for (int i = 0; i < len; i++) {
    vcp_print("%02X", data[i]);
  }
  vcp_puts("\r\n", 2);
}

static uint16_t get_byte_from_hex(const char **hex) {
  uint8_t result = 0;

  // Skip whitespace.
  while (**hex == ' ') {
    *hex += 1;
  }

  for (int i = 0; i < 2; i++) {
    result <<= 4;
    char c = **hex;
    if (c >= '0' && c <= '9') {
      result |= c - '0';
    } else if (c >= 'A' && c <= 'F') {
      result |= c - 'A' + 10;
    } else if (c >= 'a' && c <= 'f') {
      result |= c - 'a' + 10;
    } else if (c == '\0') {
      return 0x100;
    } else {
      return 0xFFFF;
    }
    *hex += 1;
  }
  return result;
}

int get_from_hex(uint8_t *buf, uint16_t buf_len, const char *hex) {
  int len = 0;
  uint16_t b = get_byte_from_hex(&hex);
  for (len = 0; len < buf_len && b <= 0xff; ++len) {
    buf[len] = b;
    b = get_byte_from_hex(&hex);
  }

  if (b == 0x100) {
    // Success.
    return len;
  }

  if (b > 0xff) {
    // Non-hexadecimal character.
    return -1;
  }

  // Buffer too small.
  return -2;
}
