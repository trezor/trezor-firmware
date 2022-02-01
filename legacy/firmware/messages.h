/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __MESSAGES_H__
#define __MESSAGES_H__

#include <stdbool.h>
#include <stdint.h>
#include "trezor.h"
#include "usb.h"

// The size of the message header "?##<2 bytes msg_id><4 bytes msg_size>".
#define MSG_HEADER_SIZE 9

// Maximum size of an incoming protobuf-encoded message without headers.
#define MSG_IN_ENCODED_SIZE (16 * 1024)

// Maximum size of a C struct containing a decoded incoming message.
#define MSG_IN_DECODED_SIZE (16 * 1024)

// Buffer size for outgoing USB packets with headers.
#define MSG_OUT_BUFFER_SIZE (3 * 1024)

// Maximum size of an outgoing protobuf-encoded message without headers.
// (Continuation packets have a one byte "?" header.)
#define MSG_OUT_ENCODED_SIZE               \
  (MSG_OUT_BUFFER_SIZE - MSG_HEADER_SIZE - \
   ((MSG_OUT_BUFFER_SIZE / USB_PACKET_SIZE) - 1))

// Maximum size of a C struct containing a decoded outgoing message.
#define MSG_OUT_DECODED_SIZE (3 * 1024)

#define msg_read(buf, len) msg_read_common('n', (buf), (len))
#define msg_write(id, ptr) msg_write_common('n', (id), (ptr))
const uint8_t *msg_out_data(void);

#if DEBUG_LINK

// Buffer size for outgoing debuglink USB packets with headers.
#define MSG_DEBUG_OUT_BUFFER_SIZE (2 * 1024)

// Maximum size of an outgoing protobuf-encoded debug message without headers.
// (Continuation packets have a one byte "?" header.)
#define MSG_DEBUG_OUT_ENCODED_SIZE               \
  (MSG_DEBUG_OUT_BUFFER_SIZE - MSG_HEADER_SIZE - \
   ((MSG_DEBUG_OUT_BUFFER_SIZE / USB_PACKET_SIZE) - 1))

#define msg_debug_read(buf, len) msg_read_common('d', (buf), (len))
#define msg_debug_write(id, ptr) msg_write_common('d', (id), (ptr))
const uint8_t *msg_debug_out_data(void);

#endif

void msg_read_common(char type, const uint8_t *buf, uint32_t len);
bool msg_write_common(char type, uint16_t msg_id, const void *msg_ptr);

void msg_read_tiny(const uint8_t *buf, int len);
extern uint8_t msg_tiny[128];
extern uint16_t msg_tiny_id;

#endif
