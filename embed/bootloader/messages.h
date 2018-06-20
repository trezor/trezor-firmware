/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#ifndef __MESSAGES_H__
#define __MESSAGES_H__

#include <stdint.h>
#include "image.h"
#include "secbool.h"

#define USB_TIMEOUT       500
#define USB_PACKET_SIZE   64

#define FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT 2
extern const uint8_t firmware_sectors[FIRMWARE_SECTORS_COUNT];

secbool msg_parse_header(const uint8_t *buf, uint16_t *msg_id, uint32_t *msg_size);

void send_user_abort(uint8_t iface_num, const char *msg);

void process_msg_Initialize(uint8_t iface_num, uint32_t msg_size, uint8_t *buf, const vendor_header * const vhdr, const image_header * const hdr);
void process_msg_GetFeatures(uint8_t iface_num, uint32_t msg_size, uint8_t *buf, const vendor_header * const vhdr, const image_header * const hdr);
void process_msg_Ping(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_FirmwareErase(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
int process_msg_FirmwareUpload(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
int process_msg_WipeDevice(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_unknown(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);

#endif
