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

typedef struct __attribute__((packed)) {
  uint8_t version_major;
  uint8_t version_minor;
  uint8_t version_patch;
  uint8_t version_build;
} boardloader_version_t;

#ifdef SECURE_MODE

// Structure holding board capabilities.
// Older boardloaders can have it missing or reordered.
//
// Simple key-tag-length-value structure at fixed boardloader address.
//
//  header 4 bytes `TRZC`
//  each field is 4 bytes or multiple (because of alignment)
//  4 bytes are
//  1-byte tag+type - CapabilityTag
//  1 byte length - counting from next byte forward
//  0 or more bytes of data, doesn't have to be aligned
//
// Last tag must be terminator or all space used.

#define CAPABILITIES_HEADER "TRZC"

enum CapabilityTag {
  TAG_TERMINATOR = 0x00,
  TAG_CAPABILITY = 0x01,
  TAG_MODEL_NAME = 0x02,
  TAG_BOARDLOADER_VERSION = 0x03
};

typedef struct __attribute__((packed)) {
  uint8_t header[4];
  uint8_t model_tag;
  uint8_t model_length;
  uint32_t model_name;
  uint8_t version_tag;
  uint8_t version_length;
  boardloader_version_t version;
  uint8_t terminator_tag;
  uint8_t terminator_length;
} board_capabilities_t;

// Parses capabilities from boardloader into RAM
//
// This function must be called before any other function
// that uses the capabilities
void parse_boardloader_capabilities();

#endif  // SECURE_MODE

// Gets four bytes containing characters identifying the board
// (e.g. `T3T1` for Trezor Safe 5)
uint32_t get_board_name();

// Gets the boardloader version
void get_boardloader_version(boardloader_version_t* version);
