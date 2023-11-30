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
  size_t begin_pos = buf->pos;
  if (!buffer_get(buf, &item->id) || ((item->id & 0x1f) == 0x1f)) {
    // Multi-byte identifiers not supported.
    return false;
  }

  size_t len = 0;
  if (!der_read_length(buf, &len)) {
    return false;
  }

  size_t header_size = buf->pos - begin_pos;
  if (!buffer_seek(buf, begin_pos) ||
      !buffer_read_buffer(buf, &item->buf, header_size + len)) {
    return false;
  }

  return buffer_seek(&item->buf, header_size);
}

// Reencode a positive integer which violates the encoding rules in Rec. ITU-T
// X.690, section 8.3.2 (the bits of the first octet and bit 8 of the second
// octet shall not all be zero).
bool der_reencode_int(BUFFER_READER *reader, BUFFER_WRITER *writer) {
  // Read a DER-encoded integer.
  DER_ITEM item = {0};
  if (!der_read_item(reader, &item) || item.id != DER_INTEGER) {
    return false;
  }

  // Strip any leading 0x00 bytes.
  buffer_lstrip(&item.buf, 0x00);
  size_t len = buffer_remaining(&item.buf);

  // Positive integers should start with one 0x00 byte if and only if the most
  // significant byte is >= 0x80.
  uint8_t msb = 0;
  bool prepend_null = (!buffer_peek(&item.buf, &msb) || msb >= 0x80);
  if (prepend_null) {
    len += 1;
  }

  if (!buffer_put(writer, DER_INTEGER) || !der_write_length(writer, len)) {
    return false;
  }

  if (prepend_null) {
    if (!buffer_put(writer, 0x00)) {
      return false;
    }
  }

  return buffer_write_buffer(writer, &item.buf);
}
