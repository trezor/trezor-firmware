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

// Magic number at the start of the boot header
#define BOOT_HEADER_MAGIC_TRZQ 0x515A5254  // TRZQ
/** Length of PQ signature in bytes */
#define BOOT_HEADER_PQ_SIGNATURE_LEN (7856)
/** Length of EC signature in bytes */
#define BOOT_HEADER_EC_SIGNATURE_LEN (64)
/** Number of reserved slots for Merkle path */
#define BOOT_HEADER_MERKLE_PATH_MAX_LEN (14)
/** Maximum accepted size of the bootloader code in bytes */
#define BOOT_HEADER_CODE_MAXSIZE (1024 * 1024)

/**
 * SHA-256 fingerprint of the boot header
 */
typedef struct {
  uint8_t bytes[32];
} boot_header_fingerprint_t;

/**
 * 4-byte version structure used in the boot header
 */
typedef struct __attribute__((packed)) {
  uint8_t major;
  uint8_t minor;
  uint8_t patch;
  uint8_t build;
} boot_header_version_t;

/**
 * Signed part of the boot header
 */
typedef struct __attribute__((packed)) {
  /** Magic constant 'TRZQ' */
  uint32_t magic;
  /** Hardware model, e.g. 'T3W1'. */
  uint32_t hw_model;
  /** Hardware revision, e.g. 1 */
  uint32_t hw_revision;
  /** Bootloader version */
  boot_header_version_t version;
  /** Bootloader fix version */
  boot_header_version_t fix_version;
  /** Minimum previous version taht the device can be updated from */
  boot_header_version_t min_prev_version;
  /** Bootloader monotonic version */
  uint32_t monotonic_version;
  /** Size of this header in bytes */
  uint32_t header_size;
  /** Size of the bootloader code in bytes */
  uint32_t code_size;
  /** Address of storage area for storage relocation purposes */
  uint32_t storage_address;

  /** Bitmask of keys used for signature verification.
   * Each bit corresponds to a public key in the BOOTLOADER_PQ_KEY and
   * BOOTLOADER_EC_KEY arrays. If the bit is set, the corresponding key
   * was used for signature verification.
   */
  uint32_t sigmask;

  uint8_t reserved[20];
} boot_header_signed_t;

/**
 * Unsigned part of the boot header
 */
typedef struct __attribute__((packed)) {
  // Firmware type (this field is modified by the bootloader during the
  // update process). It indicates the current firmware type (custom,
  // universal, bitcoin-only, etc.) and is used to determine whether
  // the storage should be erased before the update.
  uint8_t firmware_type;
  uint8_t reserved[27];

  /** First PQ signature */
  uint8_t slh_signature1[BOOT_HEADER_PQ_SIGNATURE_LEN];
  /** Second PQ signature */
  uint8_t slh_signature2[BOOT_HEADER_PQ_SIGNATURE_LEN];
  /** First EC signature */
  uint8_t ec_signature1[BOOT_HEADER_EC_SIGNATURE_LEN];
  /** Second EC signature */
  uint8_t ec_signature2[BOOT_HEADER_EC_SIGNATURE_LEN];

  /** Number of nodes in the table below */
  uint32_t merkle_path_len;
  /** Merkle tree nodes used for root calculation */
  uint8_t merkle_path[32][BOOT_HEADER_MERKLE_PATH_MAX_LEN];

} boot_header_unsigned_t;

/**
 * Structure of boot header
 */
typedef struct __attribute__((packed)) {
  /** Signed part of boot header */
  boot_header_signed_t sig;
  /** Unsigned part of the boot header */
  boot_header_unsigned_t uns;
} boot_header_t;

_Static_assert(sizeof(boot_header_t) == 16384,
               "Boot header size doesn't match with the expected size.");

/**
 * Verifies the integrity of the boot header.
 *
 * Checks the magic number, header size, code size, hardware model and revision
 *
 * @param address Address of the boot header in flash memory
 * @return Pointer to the boot header if valid, NULL otherwise.
 */
const boot_header_t* boot_header_check_integrity(uint32_t address);

/**
 * Calculates the fingerprint of the boot header.
 *
 * The fingerprint includes the bootloader code, signed part of the
 * boot header and the Merkle tree path.
 *
 * @param hdr Pointer to the boot header
 * @param code_address Address of the bootloader code in flash memory
 * @param fp Pointer to the output fingerprint structure
 */
void boot_header_calc_fingerprint(const boot_header_t* hdr,
                                  uint32_t code_address,
                                  boot_header_fingerprint_t* fp);

/**
 * Checks the signature in the boot header against the public keys.
 *
 * This function checks the signatures of the boot header using the
 * bootloader public keys. It uses the calculated fingerprint of the boot header
 * to perform the verification.
 *
 * @param header Pointer to the boot header
 * @param fp Pointer to the fingerprint of the boot header
 * @return secbool indicating whether the signature verification was successful.
 */
secbool boot_header_check_signature(const boot_header_t* header,
                                    const boot_header_fingerprint_t* fp);

/**
 * Checks if the hardware model in the boot header matches the expected one
 *
 * @param hdr Pointer to the boot header
 * @return secbool indicating whether the hardware model matches the expected
 */
secbool boot_header_check_model(const boot_header_t* hdr);
