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

#ifndef __DER_H
#define __DER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "buffer.h"
#include "options.h"

#define DER_SEQUENCE 0x30
#define DER_INTEGER 0x02
#define DER_BIT_STRING 0x03
#define DER_OCTET_STRING 0x04

// Struct representing a DER-encoded ASN.1 data value.
typedef struct {
  // Single-octet identifier encoding the ASN.1 class, type and tag number.
  uint8_t id;
  // A buffer containing the entire DER encoding of the data value including the
  // tag and length, but with the position indicator initialized to the offset
  // of the contents octets.
  BUFFER_READER buf;
} DER_ITEM;

bool __wur der_read_length(BUFFER_READER *buf, size_t *len);
bool __wur der_write_length(BUFFER_WRITER *buf, size_t len);
bool __wur der_read_item(BUFFER_READER *buf, DER_ITEM *item);
bool __wur der_reencode_int(BUFFER_READER *reader, BUFFER_WRITER *writer);

#endif  // __DER_H
