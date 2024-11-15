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

#ifndef __TREZORHAL_BOARD_CAPABILITIES_H__
#define __TREZORHAL_BOARD_CAPABILITIES_H__

/*
Simple key-tag-length-value structure at fixed boardloader address.

* header 4 bytes `TRZC`
* each field is 4 bytes or multiple (because of alignment)
* 4 bytes are
  * 1-byte tag+type - CapabilityTag
  * 1 byte length - counting from next byte forward
  * 0 or more bytes of data, doesn't have to be aligned

Last tag must be terminator or all space used.
*/

#include <trezor_types.h>

#ifdef KERNEL_MODE

#define CAPABILITIES_HEADER "TRZC"

enum CapabilityTag {
  TAG_TERMINATOR = 0x00,
  TAG_CAPABILITY = 0x01,
  TAG_MODEL_NAME = 0x02,
  TAG_BOARDLOADER_VERSION = 0x03
};

typedef struct __attribute__((packed)) BoardloaderVersion {
  uint8_t version_major;
  uint8_t version_minor;
  uint8_t version_patch;
  uint8_t version_build;
} boardloader_version_t;

/*
 * Structure of current boardloader. Older boardloaders can have it missing,
 * reordered.
 */
struct __attribute__((packed)) BoardCapabilities {
  uint8_t header[4];
  uint8_t model_tag;
  uint8_t model_length;
  uint32_t model_name;
  uint8_t version_tag;
  uint8_t version_length;
  struct BoardloaderVersion version;
  enum CapabilityTag terminator_tag;
  uint8_t terminator_length;
};

/*
 * Parse capabilities into RAM. Use while boardloader is accessible,
 * before MPU is active.
 */
void parse_boardloader_capabilities();

const uint32_t get_board_name();
const boardloader_version_t* get_boardloader_version();

#endif  // KERNEL_MODE

#endif
