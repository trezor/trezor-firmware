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

#include <stdlib.h>
#include <string.h>

#include "buffer.h"

void buffer_reader_init(BUFFER_READER *reader, const uint8_t *data,
                        size_t size) {
  reader->data = data;
  reader->size = size;
  reader->pos = 0;
}

void buffer_writer_init(BUFFER_WRITER *writer, uint8_t *data, size_t size) {
  writer->data = data;
  writer->size = size;
  writer->pos = 0;
}

size_t buffer_remaining(BUFFER_READER *buf) {
  if ((buf->data == NULL) || (buf->pos > buf->size)) {
    return 0;
  }

  return buf->size - buf->pos;
}

bool buffer_peek(const BUFFER_READER *buf, uint8_t *byte) {
  if ((buf->data == NULL) || (buf->pos >= buf->size)) {
    return false;
  }

  *byte = buf->data[buf->pos];
  return true;
}

bool buffer_get(BUFFER_READER *buf, uint8_t *byte) {
  if (!buffer_peek(buf, byte)) {
    return false;
  }

  buf->pos += 1;
  return true;
}

bool buffer_read_buffer(BUFFER_READER *src, BUFFER_READER *dest, size_t size) {
  if ((src->data == NULL) || (src->pos + size > src->size)) {
    return false;
  }

  buffer_reader_init(dest, &src->data[src->pos], size);
  src->pos += size;
  return true;
}

void buffer_lstrip(BUFFER_READER *buf, uint8_t byte) {
  if (buf->data == NULL) {
    return;
  }

  while ((buf->pos < buf->size) && (buf->data[buf->pos] == byte)) {
    buf->pos += 1;
  }
  return;
}

bool buffer_put(BUFFER_WRITER *writer, uint8_t byte) {
  if ((writer->data == NULL) || (writer->pos >= writer->size)) {
    return false;
  }

  writer->data[writer->pos] = byte;
  writer->pos += 1;
  return true;
}

bool buffer_write_array(BUFFER_WRITER *writer, const uint8_t *src,
                        size_t size) {
  if ((writer->data == NULL) || (writer->pos + size > writer->size)) {
    return false;
  }

  memcpy(&writer->data[writer->pos], src, size);
  writer->pos += size;
  return true;
}

bool buffer_write_buffer(BUFFER_WRITER *dest, BUFFER_READER *src) {
  if ((src->data == NULL) || (src->pos > src->size)) {
    return false;
  }

  if (!buffer_write_array(dest, &src->data[src->pos], src->size - src->pos)) {
    return false;
  }

  src->pos = src->size;
  return true;
}

size_t buffer_written_size(BUFFER_WRITER *writer) { return writer->pos; }
