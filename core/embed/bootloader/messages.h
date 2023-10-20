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

#ifndef __MESSAGES_H__
#define __MESSAGES_H__

#include <stdint.h>
#include "image.h"
#include "secbool.h"
#include TREZOR_BOARD

#define USB_TIMEOUT 500
#define USB_PACKET_SIZE 64

#define FIRMWARE_UPLOAD_CHUNK_RETRY_COUNT 2

enum {
  UPLOAD_OK = 0,
  UPLOAD_ERR_INVALID_CHUNK_SIZE = -1,
  UPLOAD_ERR_INVALID_VENDOR_HEADER = -2,
  UPLOAD_ERR_INVALID_VENDOR_HEADER_SIG = -3,
  UPLOAD_ERR_INVALID_IMAGE_HEADER = -4,
  UPLOAD_ERR_INVALID_IMAGE_MODEL = -5,
  UPLOAD_ERR_INVALID_IMAGE_HEADER_SIG = -6,
  UPLOAD_ERR_USER_ABORT = -7,
  UPLOAD_ERR_FIRMWARE_TOO_BIG = -8,
  UPLOAD_ERR_INVALID_CHUNK_HASH = -9,
  UPLOAD_ERR_BOOTLOADER_LOCKED = -10,
  UPLOAD_ERR_FIRMWARE_MISMATCH = -11,
  UPLOAD_ERR_NOT_FIRMWARE_UPGRADE = -12,
  UPLOAD_ERR_NOT_FULLTRUST_IMAGE = -13,
};

enum {
  WIPE_OK = 0,
  WIPE_ERR_CANNOT_ERASE = -1,
};

secbool msg_parse_header(const uint8_t *buf, uint16_t *msg_id,
                         uint32_t *msg_size);

void send_user_abort(uint8_t iface_num, const char *msg);

void process_msg_Initialize(uint8_t iface_num, uint32_t msg_size, uint8_t *buf,
                            const vendor_header *const vhdr,
                            const image_header *const hdr);
void process_msg_GetFeatures(uint8_t iface_num, uint32_t msg_size, uint8_t *buf,
                             const vendor_header *const vhdr,
                             const image_header *const hdr);
void process_msg_Ping(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_FirmwareErase(uint8_t iface_num, uint32_t msg_size,
                               uint8_t *buf);
int process_msg_FirmwareUpload(uint8_t iface_num, uint32_t msg_size,
                               uint8_t *buf);
int process_msg_WipeDevice(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);
void process_msg_unknown(uint8_t iface_num, uint32_t msg_size, uint8_t *buf);

#ifdef USE_OPTIGA
void process_msg_UnlockBootloader(uint8_t iface_num, uint32_t msg_size,
                                  uint8_t *buf);
#endif

secbool bootloader_WipeDevice(void);

#endif
