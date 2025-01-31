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

#include <pb.h>

#define MAX_PACKET_SIZE 256

typedef struct {
  // identifier of the interface used for polling communication events
  uint8_t poll_iface_id;
  // size of TX packet
  size_t tx_packet_size;
  // size of RX packet
  size_t rx_packet_size;

  // write function pointer
  bool (*write)(uint8_t *data, size_t size);
  // read function pointer
  int (*read)(uint8_t *buffer, size_t buffer_size);

  // RSOD function pointer
  void (*error)(void);
} wire_iface_t;

secbool codec_parse_header(const uint8_t *buf, uint16_t *msg_id,
                           size_t *msg_size);

secbool codec_send_msg(wire_iface_t *iface, uint16_t msg_id,
                       const pb_msgdesc_t *fields, const void *msg);

secbool codec_recv_message(wire_iface_t *iface, uint32_t msg_size, uint8_t *buf,
                           const pb_msgdesc_t *fields, void *msg);

void codec_flush(wire_iface_t *iface, uint32_t msg_size, uint8_t *buf);
