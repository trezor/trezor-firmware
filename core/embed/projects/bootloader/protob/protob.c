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

#include <util/image.h>
#include <util/unit_properties.h>

#if USE_OPTIGA
#include <sec/secret.h>
#endif

#include "memzero.h"
#include "pb/messages.pb.h"
#include "protob.h"
#include "version.h"
#include "wire/codec_v1.h"

#define MSG_SEND_INIT(TYPE) TYPE msg_send = TYPE##_init_default
#define MSG_SEND_ASSIGN_REQUIRED_VALUE(FIELD, VALUE) \
  { msg_send.FIELD = VALUE; }
#define MSG_SEND_ASSIGN_VALUE(FIELD, VALUE) \
  {                                         \
    msg_send.has_##FIELD = true;            \
    msg_send.FIELD = VALUE;                 \
  }
#define MSG_SEND_ASSIGN_STRING(FIELD, VALUE)                    \
  {                                                             \
    msg_send.has_##FIELD = true;                                \
    memzero(msg_send.FIELD, sizeof(msg_send.FIELD));            \
    strncpy(msg_send.FIELD, VALUE, sizeof(msg_send.FIELD) - 1); \
  }
#define MSG_SEND_ASSIGN_STRING_LEN(FIELD, VALUE, LEN)                     \
  {                                                                       \
    msg_send.has_##FIELD = true;                                          \
    memzero(msg_send.FIELD, sizeof(msg_send.FIELD));                      \
    strncpy(msg_send.FIELD, VALUE, MIN(LEN, sizeof(msg_send.FIELD) - 1)); \
  }
#define MSG_SEND_ASSIGN_BYTES(FIELD, VALUE, LEN)                  \
  {                                                               \
    msg_send.has_##FIELD = true;                                  \
    memzero(msg_send.FIELD.bytes, sizeof(msg_send.FIELD.bytes));  \
    memcpy(msg_send.FIELD.bytes, VALUE,                           \
           MIN(LEN, sizeof(msg_send.FIELD.bytes)));               \
    msg_send.FIELD.size = MIN(LEN, sizeof(msg_send.FIELD.bytes)); \
  }
#define MSG_SEND(TYPE)                                                       \
  codec_send_msg(iface->wire, MessageType_MessageType_##TYPE, TYPE##_fields, \
                 &msg_send)

#define MSG_RECV_INIT(TYPE) TYPE msg_recv = TYPE##_init_default
#define MSG_RECV_CALLBACK(FIELD, CALLBACK, ARGUMENT) \
  {                                                  \
    msg_recv.FIELD.funcs.decode = &CALLBACK;         \
    msg_recv.FIELD.arg = (void *)ARGUMENT;           \
  }
#define MSG_RECV(TYPE)                                                        \
  codec_recv_message(iface->wire, iface->msg_size, iface->buf, TYPE##_fields, \
                     &msg_recv)

secbool send_user_abort(protob_io_t *iface, const char *msg) {
  MSG_SEND_INIT(Failure);
  MSG_SEND_ASSIGN_VALUE(code, FailureType_Failure_ActionCancelled);
  MSG_SEND_ASSIGN_STRING(message, msg);
  return MSG_SEND(Failure);
}

secbool send_msg_failure(protob_io_t *iface, FailureType type,
                         const char *msg) {
  MSG_SEND_INIT(Failure);
  MSG_SEND_ASSIGN_VALUE(code, type);
  MSG_SEND_ASSIGN_STRING(message, msg);
  return MSG_SEND(Failure);
}

secbool send_msg_success(protob_io_t *iface, const char *msg) {
  MSG_SEND_INIT(Success);
  if (msg != NULL) {
    MSG_SEND_ASSIGN_STRING(message, msg);
  }
  return MSG_SEND(Success);
}

secbool send_msg_features(protob_io_t *iface, const vendor_header *const vhdr,
                          const image_header *const hdr) {
  MSG_SEND_INIT(Features);
  MSG_SEND_ASSIGN_STRING(vendor, "trezor.io");
  MSG_SEND_ASSIGN_REQUIRED_VALUE(major_version, VERSION_MAJOR);
  MSG_SEND_ASSIGN_REQUIRED_VALUE(minor_version, VERSION_MINOR);
  MSG_SEND_ASSIGN_REQUIRED_VALUE(patch_version, VERSION_PATCH);
  MSG_SEND_ASSIGN_VALUE(bootloader_mode, true);
  MSG_SEND_ASSIGN_STRING(model, MODEL_NAME);
  MSG_SEND_ASSIGN_STRING(internal_model, MODEL_INTERNAL_NAME);
  if (vhdr && hdr) {
    MSG_SEND_ASSIGN_VALUE(firmware_present, true);
    MSG_SEND_ASSIGN_VALUE(fw_major, (hdr->version & 0xFF));
    MSG_SEND_ASSIGN_VALUE(fw_minor, ((hdr->version >> 8) & 0xFF));
    MSG_SEND_ASSIGN_VALUE(fw_patch, ((hdr->version >> 16) & 0xFF));
    MSG_SEND_ASSIGN_STRING_LEN(fw_vendor, vhdr->vstr, vhdr->vstr_len);
  } else {
    MSG_SEND_ASSIGN_VALUE(firmware_present, false);
  }
  if (unit_properties()->color_is_valid) {
    MSG_SEND_ASSIGN_VALUE(unit_color, unit_properties()->color);
  }
  if (unit_properties()->packaging_is_valid) {
    MSG_SEND_ASSIGN_VALUE(unit_packaging, unit_properties()->packaging);
  }
  if (unit_properties()->btconly_is_valid) {
    MSG_SEND_ASSIGN_VALUE(unit_btconly, unit_properties()->btconly);
  }

#if USE_OPTIGA
  MSG_SEND_ASSIGN_VALUE(bootloader_locked,
                        (secret_bootloader_locked() == sectrue));
#endif
  return MSG_SEND(Features);
}

secbool recv_msg_initialize(protob_io_t *iface, Initialize *msg) {
  MSG_RECV_INIT(Initialize);
  secbool result = MSG_RECV(Initialize);
  memcpy(msg, &msg_recv, sizeof(Initialize));
  return result;
}

secbool recv_msg_get_features(protob_io_t *iface, GetFeatures *msg) {
  MSG_RECV_INIT(GetFeatures);
  secbool result = MSG_RECV(GetFeatures);
  memcpy(msg, &msg_recv, sizeof(GetFeatures));
  return result;
}

secbool recv_msg_wipe_device(protob_io_t *iface, WipeDevice *msg) {
  MSG_RECV_INIT(WipeDevice);
  secbool result = MSG_RECV(WipeDevice);
  memcpy(msg, &msg_recv, sizeof(WipeDevice));
  return result;
}

secbool recv_msg_ping(protob_io_t *iface, Ping *msg) {
  MSG_RECV_INIT(Ping);
  secbool result = MSG_RECV(Ping);
  memcpy(msg, &msg_recv, sizeof(Ping));
  return result;
}

secbool recv_msg_firmware_erase(protob_io_t *iface, FirmwareErase *msg) {
  MSG_RECV_INIT(FirmwareErase);
  secbool result = MSG_RECV(FirmwareErase);
  memcpy(msg, &msg_recv, sizeof(FirmwareErase));
  return result;
}

secbool send_msg_request_firmware(protob_io_t *iface, uint32_t offset,
                                  uint32_t length) {
  MSG_SEND_INIT(FirmwareRequest);
  MSG_SEND_ASSIGN_REQUIRED_VALUE(offset, offset);
  MSG_SEND_ASSIGN_REQUIRED_VALUE(length, length);
  return MSG_SEND(FirmwareRequest);
}

typedef struct {
  void (*cb)(size_t len, void *ctx);
  void *ctx;
  uint8_t *buffer;
  size_t buffer_size;
} payload_ctx_t;

/* we don't use secbool/sectrue/secfalse here as it is a nanopb api */
static bool read_payload(pb_istream_t *stream, const pb_field_t *field,
                         void **arg) {
  payload_ctx_t *payload_ctx = (payload_ctx_t *)*arg;
#define BUFSIZE 32768

  if (stream->bytes_left > payload_ctx->buffer_size) {
    return false;
  }

  uint32_t bytes_written = 0;

  while (stream->bytes_left) {
    uint32_t received =
        stream->bytes_left > BUFSIZE ? BUFSIZE : stream->bytes_left;

    // notify of received data
    payload_ctx->cb(received, payload_ctx->ctx);

    // read data
    if (!pb_read(stream, (pb_byte_t *)(payload_ctx->buffer + bytes_written),
                 (received))) {
      return false;
    }
    bytes_written += received;
  }

  return true;
}

secbool recv_msg_firmware_upload(protob_io_t *iface, FirmwareUpload *msg,
                                 void *ctx,
                                 void (*data_cb)(size_t len, void *ctx),
                                 uint8_t *buffer, size_t buffer_size) {
  payload_ctx_t payload_ctx = {
      .cb = data_cb, .ctx = ctx, .buffer = buffer, .buffer_size = buffer_size};

  MSG_RECV_INIT(FirmwareUpload);
  MSG_RECV_CALLBACK(payload, read_payload, &payload_ctx);
  secbool result = MSG_RECV(FirmwareUpload);
  memcpy(msg, &msg_recv, sizeof(FirmwareUpload));
  return result;
}

void recv_msg_unknown(protob_io_t *iface) {
  codec_flush(iface->wire, iface->msg_size, iface->buf);
  send_msg_failure(iface, FailureType_Failure_UnexpectedMessage,
                   "Unexpected message");
}

void protob_init(protob_io_t *iface, wire_iface_t *wire) {
  memset(iface, 0, sizeof(protob_io_t));
  iface->wire = wire;
}

uint32_t protob_get_iface_flag(protob_io_t *iface) {
  return iface->wire->poll_iface_id;
}

secbool protob_get_msg_header(protob_io_t *iface, uint16_t *msg_id) {
  iface->wire->read(iface->buf, iface->wire->rx_packet_size);
  return codec_parse_header(iface->buf, msg_id, &iface->msg_size);
}
