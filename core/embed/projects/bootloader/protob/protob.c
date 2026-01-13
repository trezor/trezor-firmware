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

#include <sec/unit_properties.h>
#include <util/image.h>

#if LOCKABLE_BOOTLOADER
#include <sec/secret.h>
#endif

#ifdef USE_POWER_MANAGER
#include <io/power_manager.h>
#endif

#include "memzero.h"
#include "pb/messages.pb.h"
#include "protob.h"
#include "protob_common.h"
#include "version.h"
#include "wire/codec_v1.h"

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

secbool send_msg_features(protob_io_t *iface, const fw_info_t *fw) {
  MSG_SEND_INIT(Features);
  MSG_SEND_ASSIGN_STRING(vendor, "trezor.io");
  MSG_SEND_ASSIGN_REQUIRED_VALUE(major_version, VERSION_MAJOR);
  MSG_SEND_ASSIGN_REQUIRED_VALUE(minor_version, VERSION_MINOR);
  MSG_SEND_ASSIGN_REQUIRED_VALUE(patch_version, VERSION_PATCH);
  MSG_SEND_ASSIGN_VALUE(build_version, VERSION_BUILD);
  MSG_SEND_ASSIGN_VALUE(bootloader_mode, true);
  MSG_SEND_ASSIGN_STRING(model, MODEL_NAME);
  MSG_SEND_ASSIGN_STRING(internal_model, MODEL_INTERNAL_NAME);
  if (fw != NULL && fw->hdr != NULL && fw->header_present == sectrue) {
    MSG_SEND_ASSIGN_VALUE(firmware_present, true);
    MSG_SEND_ASSIGN_VALUE(fw_major, (fw->hdr->version & 0xFF));
    MSG_SEND_ASSIGN_VALUE(fw_minor, ((fw->hdr->version >> 8) & 0xFF));
    MSG_SEND_ASSIGN_VALUE(fw_patch, ((fw->hdr->version >> 16) & 0xFF));
    MSG_SEND_ASSIGN_VALUE(fw_build, ((fw->hdr->version >> 24) & 0xFF));
    MSG_SEND_ASSIGN_STRING_LEN(fw_vendor, fw->vhdr.vstr, fw->vhdr.vstr_len);
    MSG_SEND_ASSIGN_VALUE(firmware_corrupted, sectrue != fw->firmware_present);
  } else {
    MSG_SEND_ASSIGN_VALUE(firmware_present, false);
    MSG_SEND_ASSIGN_VALUE(firmware_corrupted, false);
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

#if LOCKABLE_BOOTLOADER
  MSG_SEND_ASSIGN_VALUE(bootloader_locked,
                        (secret_bootloader_locked() == sectrue));
#endif

#ifdef USE_POWER_MANAGER
  pm_state_t state = {0};
  if (PM_OK == pm_get_state(&state)) {
    MSG_SEND_ASSIGN_VALUE(soc, state.soc);
    MSG_SEND_ASSIGN_VALUE(usb_connected, state.usb_connected);
    MSG_SEND_ASSIGN_VALUE(wireless_connected, state.wireless_connected);
  }
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
