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

#include <rtl/crypto_helpers.h>

#define APP_HEADER_MAGIC 0x415A5254  // "TRZA" in ASCII

#define APP_TARGET_ARMV8M 0
#define APP_TARGET_X86_64 1

#define APP_HEADER_MAX_ID_LEN 32
#define APP_HEADER_MAX_NAME_LEN 32
#define APP_HEADER_MAX_VENDOR_LEN 32

#define APP_HEADER_MAX_SIZE 256

/** Header of an app file */
typedef struct {
  /** Magic number to identify the file format */
  uint32_t magic;
  /** Header size in bytes */
  uint32_t header_size;
  /** Unique identifier of the app (utf-8 encoded, zero-padded) */
  char id[APP_HEADER_MAX_ID_LEN];
  /** App name (utf-8 encoded, zero-padded) */
  char app_name[APP_HEADER_MAX_NAME_LEN];
  /** Vendor name (utf-8 encoded, zero-padded) */
  char vendor_name[APP_HEADER_MAX_VENDOR_LEN];
  /** Target model identifier (or zeros for universal apps) */
  uint8_t model[4];
  /** App version as major.minor.patch.build bytes */
  uint32_t version;
  /** SDK version used to build the app. */
  uint32_t sdk_version;
  /** ABI version used to build the app. */
  uint8_t abi_version;
  /** Binary payload type */
  uint8_t payload_type;
  /** Reserved for future use */
  uint16_t reserved1;
  /** Size of the binary payload in bytes. */
  uint32_t payload_size;
  /** Chain hash of payload chunks processed in reverse order */
  sha256_digest_t payload_hash;
  /** Size of each chunk of the payload in bytes */
  uint16_t chunk_size;
  /** Reserved for future use */
  uint16_t reserved2;

  // TODO logo
  // TODO bip32_paths

  // uint32_t padding[1];

} app_header_t;

/**
 * @brief Verifies the header of an application image for integrity and
 * correctness.
 *
 * Verifies the header of the image if it is a valid (e.g. correct
 * magic, supported ABI version, etc.)
 *
 * @param header_ptr Pointer to the application header to verify
 * @param header_size Size of the application header in bytes
 *
 * @return const app_header_t* Pointer to the verified header, or NULL if the
 * header is invalid.
 */
const app_header_t* app_header_verify(const void* header_ptr,
                                      size_t header_size);
