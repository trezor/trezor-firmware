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

#include "bootloaders/bootloader_hashes.h"

#define MODEL_NAME "Safe 3"
#define MODEL_FULL_NAME "Trezor Safe 3"
#define MODEL_INTERNAL_NAME "T2B1"
#define MODEL_INTERNAL_NAME_TOKEN T2B1
#define MODEL_INTERNAL_NAME_QSTR MP_QSTR_T2B1
#define MODEL_USB_MANUFACTURER "SatoshiLabs"
#define MODEL_USB_PRODUCT "TREZOR"
#define MODEL_HOMESCREEN_MAXSIZE 16384

/*** PRODUCTION KEYS  ***/
#define MODEL_BOARDLOADER_KEYS \
  (const uint8_t *)"\x54\x9a\x45\x55\x70\x08\xd5\x51\x8a\x9a\x15\x1d\xc6\xa3\x56\x8c\xf7\x38\x30\xa7\xfe\x41\x9f\x26\x26\xd9\xf3\x0d\x02\x4b\x2b\xec", \
  (const uint8_t *)"\xc1\x6c\x70\x27\xf8\xa3\x96\x26\x07\xbf\x24\xcd\xec\x2e\x3c\xd2\x34\x4e\x1f\x60\x71\xe8\x26\x0b\x3d\xda\x52\xb1\xa5\x10\x7c\xb7", \
  (const uint8_t *)"\x87\x18\x0f\x93\x31\x78\xb2\x83\x2b\xee\x2d\x70\x46\xc7\xf4\xb9\x83\x00\xca\x7d\x7f\xb2\xe4\x56\x71\x69\xc8\x73\x0a\x1c\x40\x20",

#define MODEL_BOOTLOADER_KEYS \
  (const uint8_t *)"\xbf\x4e\x6f\x00\x4f\xcb\x32\xce\xc6\x83\xf2\x2c\x88\xc1\xa8\x6c\x15\x18\xc6\xde\x8a\xc9\x70\x02\xd8\x4a\x63\xbe\xa3\xe3\x75\xdd", \
  (const uint8_t *)"\xd2\xde\xf6\x91\xc1\xe9\xd8\x09\xd8\x19\x0c\xf7\xaf\x93\x5c\x10\x68\x8f\x68\x98\x34\x79\xb4\xee\x9a\xba\xc1\x91\x04\x87\x8e\xc1", \
  (const uint8_t *)"\x07\xc8\x51\x34\x94\x6b\xf8\x9f\xa1\x9b\xdc\x2c\x5e\x5f\xf9\xce\x01\x29\x65\x08\xee\x08\x63\xd0\xff\x6d\x63\x33\x1d\x1a\x25\x16",

#define IMAGE_CHUNK_SIZE (128 * 1024)
#define IMAGE_HASH_BLAKE2S

#define DISPLAY_JUMP_BEHAVIOR DISPLAY_RETAIN_CONTENT
#define RSOD_INFINITE_LOOP 1

#define NORCOW_SECTOR_SIZE (1 * 64 * 1024)  // 64 kB
#define NORCOW_MIN_VERSION 0x00000003

#include "memory.h"
