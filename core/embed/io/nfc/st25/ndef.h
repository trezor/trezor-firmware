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

#pragma once

#include <trezor_types.h>

#define NDEF_MAX_RECORDS 3
#define NDEF_MAX_RECORD_PAYLOAD_BYTES 50

typedef enum {
  NDEF_OK = 0,
  NDEF_ERROR = 1,
} ndef_status_t;

typedef struct {
  union {
    struct {
      uint8_t mb : 1;
      uint8_t me : 1;
      uint8_t cf : 1;
      uint8_t sr : 1;
      uint8_t il : 1;
      uint8_t tnf : 3;
    };
    uint8_t byte;
  };
} ndef_record_header_t;

typedef struct {
  ndef_record_header_t header;
  uint8_t type_length;
  uint32_t payload_length;
  uint8_t id_length;
  uint8_t type;
  uint8_t id;
  uint8_t payload[NDEF_MAX_RECORD_PAYLOAD_BYTES];
  uint16_t record_total_len;
} ndef_record_t;

typedef struct {
  uint32_t message_total_len;
  uint8_t records_cnt;
  ndef_record_t records[NDEF_MAX_RECORDS];
} ndef_message_t;

// Parse the NDEF message from the byte buffer
// Returns NDEF_OK if the message is parsed successfully
ndef_status_t ndef_parse_message(const uint8_t *buffer, size_t buffer_size,
                                 ndef_message_t *message);

// Parse the NDEF record from the byte buffer
// Returns NDEF_OK if the record is parsed successfully
ndef_status_t ndef_parse_record(const uint8_t *buffer, size_t buffer_size,
                                ndef_record_t *rec);

// Write the NDEF message with single URI record into the byte buffer
// Returns the size of the byte buffer.
size_t ndef_create_uri(const char *uri, uint8_t *buffer, size_t buffer_size);
