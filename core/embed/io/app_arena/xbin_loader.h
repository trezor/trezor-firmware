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

#include <trezor_types.h>

#include <sys/applet.h>

#define XBIN_HEADER_MAGIC 0x415A5254  // "TRZA" in ASCII

#define XBIN_TARGET_ARMV8M 0
#define XBIN_TARGET_X86_64 1

/** Header of an xbin file */
typedef struct {
  /** Magic number to identify the file format */
  uint32_t magic;
  /** Header size in bytes */
  uint32_t header_size;
  /** Unique identifier of the app */
  char id[32];
  /** App version as major.minor.patch.build bytes */
  uint32_t version;
  /** SDK version used to build the app. */
  uint8_t sdk_version[2];
  /** ABI version used to build the app. */
  uint8_t abi_version;
  /** Binary payload type */
  uint8_t payload_type;
  /** Size of the binary payload in bytes. */
  uint32_t payload_size;

  // TODO app_name
  // TODO vendor_name
  // TODO logo
  // TODO: app hash
  // TODO model
  // TODO bip32_paths

  uint32_t reserved[3];

} xbin_header_t;

/**
 * @brief Verifies the header of an application image
 *
 * Verifies the header of the image if it is a valid xbin image (e.g. correct
 * magic, supported ABI version, whether the sizes and offsets specified in the
 * header are valid given the image size, etc.)
 *
 * Verified header can be used in subsequent calls to other xbin_* functions to
 * load and run the applet.
 *
 * @param header Pointer to the xbin header to verify
 * @param image_size Size of the xbin image
 */
const xbin_header_t* xbin_verify_image(const void* image, size_t image_size);

/**
 * @brief Verifies the signature of an application image
 *
 * The signature can be verified before rodata relocations are applied (or
 * undone) because the signature is calculated over the image with the original
 * (unrelocated) rodata.
 *
 * @param header Pointer to the xbin header
 * @param proof Pointer to the Merkle proof data for signature verification
 * @param proof_size Size of the Merkle proof data in bytes
 *
 * @return ts_t Status code indicating success or failure
 */
ts_t xbin_verify_signature(const xbin_header_t* header, const void* proof,
                           size_t proof_size);

/**
 * @brief Initializes an applet structure for an application image
 *
 * Clears all applet rw memory and initializes .data section.
 *
 * @param applet Pointer to the applet structure to initialize
 * @param header Pointer to the application image header
 * @param rwmem Pointer to the memory allocated for the applet's RW section
 * @param rwmem_size Size of the allocated RW memory
 * @param applet Pointer to the applet structure to initialize
 *
 * @return ts_t Status code indicating success or failure
 */
ts_t xbin_prepare_applet(const xbin_header_t* header, void* rwmem,
                         size_t rwmem_size, applet_t* applet);
