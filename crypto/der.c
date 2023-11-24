/**
 * Copyright (c) 2023 Trezor Company s.r.o.
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT HMAC_SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include "der.h"

bool der_read_length(BUFFER_READER *buf, size_t *len) {
  // Read the initial octet.
  uint8_t init = 0;
  if (!buffer_get(buf, &init)) {
    return false;
  }

  if (init < 0x80) {
    // Short form. Encodes length in initial octet.
    *len = init;
    return true;
  }

  if (init == 0x80 || init == 0xFF) {
    // Indefinite length or RFU.
    return false;
  }

  // Long form.
  uint8_t byte = 0;
  if (!buffer_peek(buf, &byte) || byte == 0) {
    // Encoding is not the shortest possible.
    return false;
  }

  if ((init & 0x7F) > sizeof(*len)) {
    // Length overflow.
    return false;
  }

  *len = 0;
  for (int i = 0; i < (init & 0x7F); ++i) {
    if (!buffer_get(buf, &byte)) {
      return false;
    }
    *len = (*len << 8) + byte;
  }

  if (*len < 0x80) {
    // Encoding is not the shortest possible.
    return false;
  }

  return true;
}

bool der_write_length(BUFFER_WRITER *buf, size_t len) {
  if (len < 0x80) {
    // Short form. Encodes length in initial octet.
    return buffer_put(buf, len);
  }

  // Long form.
  uint8_t encoding[sizeof(len) + 1] = {0};
  size_t pos = sizeof(encoding) - 1;
  while (len != 0) {
    encoding[pos] = len & 0xff;
    len >>= 8;
    pos -= 1;
  }
  encoding[pos] = 0x80 | (sizeof(encoding) - 1 - pos);
  return buffer_write_array(buf, &encoding[pos], sizeof(encoding) - pos);
}

bool der_read_item(BUFFER_READER *buf, DER_ITEM *item) {
  if (!buffer_get(buf, &item->id) || ((item->id & 0x1f) == 0x1f)) {
    // Multi-byte identifiers not supported.
    return false;
  }

  size_t len = 0;
  if (!der_read_length(buf, &len)) {
    return false;
  }

  return buffer_read_buffer(buf, &item->cont, len);
}
