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
// Reserved space for boot header
#define BOOT_HEADER_MAXSIZE (2 * 8192)
/** Length of PQ signature in bytes */
#define BOOT_HEADER_PQ_SIGNATURE_LEN (7856)
/** Length of EC signature in bytes */
#define BOOT_HEADER_EC_SIGNATURE_LEN (64)
/** Number of reserved slots for Merkle proof */
#define BOOT_HEADER_MERKLE_PROOF_MAXLEN (256)
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
 * Authenticated part of the boot header
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
  /** Minimum version that the device can be downgraded to without
   * erasing storage. */
  boot_header_version_t fix_version;
  /** Minimum previous version that the device can be updated from when
   * installing this header. */
  boot_header_version_t min_prev_version;
  /** An integer which must not decrease between updates. */
  uint32_t monotonic_version;
  /** Size of the entire header header in bytes, including the Merkle proof
   * and signatures. It's calculated in the link time and must be
   * aligned to 8K boundary. */
  uint32_t header_size;
  /** Size of authenticated part of the header in bytes.
   * Final value is calculated in post-build step and includes
   * potential padding of the structure. */
  uint32_t auth_size;
  /** Size of the bootloader code in bytes */
  uint32_t code_size;
  /** Address of storage area for storage relocation purposes */
  uint32_t storage_address;
  /** Bitmask of keys used for signature verification.
   * Each bit corresponds to a public key in the BOOTLOADER_PQ_KEY and
   * BOOTLOADER_EC_KEY arrays. If the bit is set, the corresponding key
   * is used for signature verification. */
  uint32_t sigmask;
  /* Padding is automatically added by the post-build step to ensure that
   * the authenticated part of the header is maximized. */
  uint8_t padding[0];

} boot_header_t;

/**
 * Merkle proof node
 */
typedef struct {
  uint8_t bytes[32];
} merkle_proof_node_t;

/**
 * Merkle proof structure used in the boot header used to
 * calculate the root of merkle tree. It placed just after the
 * authenticated part of the boot header.
 *
 */
typedef struct __attribute__((packed)) {
  /** Number of nodes in the table below */
  uint32_t node_count;
  /** Merkle proof used for root calculation */
  merkle_proof_node_t nodes[0];

} boot_header_merkle_proof_t;

/**
 * Unauthenticated part of the boot header containing signatures and
 * other informatioin that need not (or must not) be authenticated.
 * It is placed right after the Merkle proof.
 */
typedef struct __attribute__((packed)) {
  /** First PQ signature */
  uint8_t slh_signature1[BOOT_HEADER_PQ_SIGNATURE_LEN];
  /** Second PQ signature */
  uint8_t slh_signature2[BOOT_HEADER_PQ_SIGNATURE_LEN];
  /** First EC signature */
  uint8_t ec_signature1[BOOT_HEADER_EC_SIGNATURE_LEN];
  /** Second EC signature */
  uint8_t ec_signature2[BOOT_HEADER_EC_SIGNATURE_LEN];

  // Firmware type (this field is modified by the bootloader during the
  // update process). It indicates the current firmware type (custom,
  // universal, bitcoin-only, etc.) and is used to determine whether
  // the storage should be erased before the update.
  uint8_t firmware_type;
  uint8_t padding[3];

} boot_header_unauth_t;

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
 * Gets the pointer to the Merkle proof in the boot header.
 *
 * @param hdr Pointer to the verifiedboot header
 * @return Pointer to the Merkle proof structure or NULL if the header is
 *         invalid.
 */
const boot_header_merkle_proof_t* boot_header_merkle_proof(
    const boot_header_t* hdr);

/**
 * Gets pointer to the unauthenticated part of the boot header.
 *
 * @param hdr Pointer to the verifiedboot header
 * @return Pointer to the unauthenticated part of the boot header or NULL if the
 *         header is invalid.
 */

const boot_header_unauth_t* boot_header_unauth(const boot_header_t* hdr);

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

/**
 * This function compares the boot header and the bootloader code
 * with the previous bootloader header and code. If they are the same,
 * it returns sectrue, otherwise secfalse.
 *
 * @param hdr Pointer to the current boot header
 * @param code_address Address of the bootloader code in flash memory
 * @return secbool indicating whether the boot header and code are unchanged
 */
secbool boot_header_is_unchanged(const boot_header_t* hdr,
                                 uint32_t code_address);
