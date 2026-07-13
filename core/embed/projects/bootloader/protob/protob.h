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

#include <sec/image.h>

#include "pb/messages.pb.h"

#include "fw_check.h"
#include "wire/codec_v1.h"

typedef struct {
  wire_iface_t *wire;
  uint8_t buf[MAX_PACKET_SIZE];
  size_t msg_size;

} protob_io_t;

typedef struct {
  protob_io_t ifaces[2];
  size_t count;
} protob_ios_t;

secbool send_user_abort(protob_io_t *iface, const char *msg);

secbool send_msg_features(protob_io_t *iface, const fw_info_t *fw);

secbool send_msg_failure(protob_io_t *iface, FailureType type, const char *msg);

secbool send_msg_success(protob_io_t *iface, const char *msg);

secbool send_msg_request_firmware(protob_io_t *iface, uint32_t offset,
                                  uint32_t length);

secbool recv_msg_initialize(protob_io_t *iface, Initialize *msg);

secbool recv_msg_get_features(protob_io_t *iface, GetFeatures *msg);

secbool recv_msg_wipe_device(protob_io_t *iface, WipeDevice *msg);

secbool recv_msg_ping(protob_io_t *iface, Ping *msg);

secbool recv_msg_firmware_erase(protob_io_t *iface, FirmwareErase *msg);

#ifdef PQ_SECURE_BOOT
// Receives a FirmwareBegin: the boot header (into bh_buf) and module headers
// (into mh_buf) are decoded via nanopb callbacks; their lengths are returned in
// *bh_len / *mh_len. `msg` receives the scalar fields (code_length).
secbool recv_msg_firmware_begin(protob_io_t *iface, FirmwareBegin *msg,
                                uint8_t *bh_buf, size_t bh_size, size_t *bh_len,
                                uint8_t *mh_buf, size_t mh_size,
                                size_t *mh_len);
#endif

secbool recv_msg_firmware_upload(protob_io_t *iface, FirmwareUpload *msg,
                                 void *ctx,
                                 void (*data_cb)(size_t len, void *ctx),
                                 uint8_t *buffer, size_t buffer_size);

void recv_msg_unknown(protob_io_t *iface);

void protob_init(protob_io_t *iface, wire_iface_t *wire);

uint32_t protob_get_iface_flag(protob_io_t *iface);

secbool protob_get_msg_header(protob_io_t *iface, uint16_t *msg_id);
