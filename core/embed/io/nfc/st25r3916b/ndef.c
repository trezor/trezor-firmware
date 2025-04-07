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
#ifdef KERNEL_MODE

#include "ndef.h"
#include <trezor_rtl.h>

#define NDEF_MESSAGE_URI_OVERHEAD 7

ndef_status_t ndef_parse_message(const uint8_t *buffer, size_t buffer_size,
                                 ndef_message_t *message) {
  memset(message, 0, sizeof(ndef_message_t));

  size_t remaining_len = buffer_size;

  if (remaining_len <= 0) {
    return NDEF_ERROR;
  }

  // Indicate TLV header
  if (*buffer == 0x3) {
    buffer++;
    remaining_len--;
  } else {
    return NDEF_ERROR;  // Not a valid TLV structure
  }

  if (remaining_len <= 0) {
    return NDEF_ERROR;
  }

  // TLV length
  if (*buffer == 0xFF) {
    // TLV 3 byte length format
    buffer++;
    remaining_len--;

    if (remaining_len < 2) {
      return NDEF_ERROR;
    }
    message->message_total_len = (int16_t)(buffer[0] << 8 | buffer[1]);
    buffer = buffer + 2;
    remaining_len = remaining_len - 2;

  } else {
    message->message_total_len = *buffer;
    buffer++;
    remaining_len--;
  }

  if (message->message_total_len > remaining_len) {
    return NDEF_ERROR;  // Not enough room to cover while message
  }
  remaining_len = message->message_total_len;

  ndef_status_t status;
  while (1) {
    status = ndef_parse_record(buffer, remaining_len,
                               &message->records[message->records_cnt]);

    if (status != NDEF_OK) {
      return status;
    }

    buffer += message->records[message->records_cnt].record_total_len;
    remaining_len -= message->records[message->records_cnt].record_total_len;
    message->records_cnt++;

    if (message->records_cnt >= NDEF_MAX_RECORDS) {
      break;  // Max records reached
    }

    if (remaining_len == 0) {
      break;
    }
  }

  // Check TLV termination character
  if (*buffer != 0xFE) {
    return NDEF_ERROR;  // Not a valid TLV structure
  }

  return NDEF_OK;
}

ndef_status_t ndef_parse_record(const uint8_t *buffer, size_t buffer_size,
                                ndef_record_t *rec) {
  uint8_t bp = 0;

  // Check if there is enough items to cover first part of the header revelaing
  // record length
  if (buffer_size < 3) {
    return NDEF_ERROR;  // Not enough data to parse
  }

  // Look at first byte, parse header
  rec->header.byte = buffer[bp++];

  if (rec->header.tnf == 0x00 || rec->header.tnf > 0x06) {
    return NDEF_ERROR;  // Empty or non-existing record
  }

  rec->type_length = buffer[bp++];

  if (rec->header.sr) {
    rec->payload_length = buffer[bp++];
  } else {
    rec->payload_length = (uint32_t)buffer[bp];
    bp += 4;
  }

  if (rec->header.il) {
    rec->id_length = buffer[bp++];
  } else {
    // ID length ommited
    rec->id_length = 0;
  }

  if (rec->type_length > 0) {
    rec->type = buffer[bp];
    bp += rec->type_length;
  } else {
    // Type length ommited
    rec->type = 0;
  }

  if (rec->id_length == 0) {
    // ID ommited
    rec->id = 0;
  } else {
    rec->id = buffer[bp++];
  }

  if (rec->payload_length > 0) {
    if (rec->payload_length > NDEF_MAX_RECORD_PAYLOAD_BYTES) {
      return NDEF_ERROR;  // Payload too long
    }

    memcpy(rec->payload, buffer + bp, rec->payload_length);
    bp += rec->payload_length;
  } else {
    // Payload length ommited;
  }

  rec->record_total_len = bp;

  return NDEF_OK;
}

size_t ndef_create_uri(const char *uri, uint8_t *buffer, size_t buffer_size) {
  size_t uri_len = strlen(uri);

  if (buffer_size < (uri_len + NDEF_MESSAGE_URI_OVERHEAD)) {
    return 0;  // Not enough room to create URI
  }

  *buffer = 0x3;  // TLV header
  buffer++;

  // NDEF message length
  *buffer = uri_len + 5;  // uri + record header;
  buffer++;

  *buffer = 0xD1;  // NDEF record Header
  buffer++;

  *buffer = 0x1;  // Type length
  buffer++;

  *buffer = uri_len;  // Payload length
  buffer++;

  *buffer = 0x55;  // URI type
  buffer++;

  *buffer = 0x1;  // URI abreviation
  buffer++;

  for (uint8_t i = 0; i < uri_len; i++) {
    *buffer = uri[i];
    buffer++;
  }

  *buffer = 0xFE;  // TLV termination

  return uri_len + NDEF_MESSAGE_URI_OVERHEAD;  // return buffer len
}

#endif
