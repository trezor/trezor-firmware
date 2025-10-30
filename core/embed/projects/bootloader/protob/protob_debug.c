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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <pb.h>
#include <pb_decode.h>

#include "protob_common.h"

#include "pb/messages-debug.pb.h"
#include "pb/messages.pb.h"
#include "protob.h"

typedef struct {
  void (*cb)(size_t len, void *ctx);
  void *ctx;
  uint8_t *buffer;
  size_t buffer_size;
} payload_ctx_t;

static bool read_payload(pb_istream_t *stream, const pb_field_t *field,
                         void **arg) {
  payload_ctx_t *payload_ctx = (payload_ctx_t *)*arg;

  if (stream->bytes_left > payload_ctx->buffer_size) {
    return false;
  }

#define BUFSIZE 32768

  uint32_t bytes_written = 0;

  while (stream->bytes_left) {
    uint32_t received =
        stream->bytes_left > BUFSIZE ? BUFSIZE : stream->bytes_left;

    // read data
    if (!pb_read(stream, (pb_byte_t *)(payload_ctx->buffer + bytes_written),
                 (received))) {
      return false;
    }
    bytes_written += received;
  }

  return true;
}

secbool recv_msg_debug_link_get_state(protob_io_t *iface,
                                      DebugLinkGetState *msg) {
  MSG_RECV_INIT(DebugLinkGetState);
  secbool result = MSG_RECV(DebugLinkGetState);
  memcpy(msg, &msg_recv, sizeof(DebugLinkGetState));
  return result;
}

secbool recv_msg_debug_link_decision(protob_io_t *iface,
                                     DebugLinkDecision *msg) {
  MSG_RECV_INIT(DebugLinkDecision);
  secbool result = MSG_RECV(DebugLinkDecision);
  memcpy(msg, &msg_recv, sizeof(DebugLinkDecision));
  return result;
}

secbool recv_msg_debug_link_screen_record(protob_io_t *iface,
                                          DebugLinkRecordScreen *msg,
                                          uint8_t *buffer, size_t buffer_size) {
  payload_ctx_t payload_ctx = {.buffer = buffer, .buffer_size = buffer_size};

  MSG_RECV_INIT(DebugLinkRecordScreen);
  MSG_RECV_CALLBACK(target_directory, read_payload, &payload_ctx);
  secbool result = MSG_RECV(DebugLinkRecordScreen);
  memcpy(msg, &msg_recv, sizeof(DebugLinkRecordScreen));
  return result;
}

secbool send_msg_debug_link_state(protob_io_t *iface) {
  MSG_SEND_INIT(DebugLinkState);

  return MSG_SEND(DebugLinkState);
}
