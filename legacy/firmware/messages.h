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

#define MSG_IN_SIZE (15 * 1024)

#define MSG_OUT_SIZE (3 * 1024)

#define msg_read(buf, len) msg_read_common('n', (buf), (len))
#define msg_write(id, ptr) msg_write_common('n', (id), (ptr))
const uint8_t *msg_out_data(void);

#if DEBUG_LINK

#define MSG_DEBUG_OUT_SIZE (2 * 1024)

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
