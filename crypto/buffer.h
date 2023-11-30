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

#ifndef __BUFFER_H
#define __BUFFER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "options.h"

// Buffer reader struct, wraps a pointer to const data.
typedef struct {
  const uint8_t *data;
  size_t size;
  size_t pos;
} BUFFER_READER;

// Buffer writer struct, wraps a pointer to non-const data.
typedef struct {
  uint8_t *data;
  size_t size;
  size_t pos;
} BUFFER_WRITER;

void buffer_reader_init(BUFFER_READER *buf, const uint8_t *data, size_t size);
void buffer_writer_init(BUFFER_WRITER *buf, uint8_t *data, size_t size);
size_t __wur buffer_remaining(BUFFER_READER *buf);
bool __wur buffer_ptr(BUFFER_READER *buf, const uint8_t **ptr);
bool __wur buffer_peek(const BUFFER_READER *buf, uint8_t *byte);
bool __wur buffer_get(BUFFER_READER *buf, uint8_t *byte);
bool __wur buffer_seek(BUFFER_READER *buf, size_t pos);
bool __wur buffer_read_buffer(BUFFER_READER *src, BUFFER_READER *dest,
                              size_t size);
void buffer_lstrip(BUFFER_READER *buf, uint8_t byte);
bool __wur buffer_put(BUFFER_WRITER *writer, uint8_t byte);
bool __wur buffer_write_array(BUFFER_WRITER *writer, const uint8_t *src,
                              size_t size);
bool __wur buffer_write_buffer(BUFFER_WRITER *dest, BUFFER_READER *src);
size_t __wur buffer_written_size(BUFFER_WRITER *writer);

#endif  // __BUFFER_H
