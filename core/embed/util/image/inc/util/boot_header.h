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
/** Number of PQ/EC signatures */
#define BOOT_HEADER_SIGNATURE_COUNT 2
/** Length of PQ signature in bytes */
#define BOOT_HEADER_PQ_SIGNATURE_LEN (7856)
/** Length of EC signature in bytes */
#define BOOT_HEADER_EC_SIGNATURE_LEN (64)
/** Number of reserved slots for Merkle proof */
#define BOOT_HEADER_MERKLE_PROOF_MAXLEN (256)

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
 * Merkle proof node (SHA-256 digest)
 */
typedef struct {
  uint8_t bytes[32];
} merkle_proof_node_t;

/**
 * Authenticated part of the boot header
 *
 * This structure can be extended in future versions if needed.
 * Just make sure to add new fields at the end of the structure.
 * Never remove or reorder existing fields.
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
  uint8_t monotonic_version;
  /** Bitmask of keys used for signature verification.
   * Each bit corresponds to a public key in the BOOTLOADER_PQ_KEY and
   * BOOTLOADER_EC_KEY arrays. If the bit is set, the corresponding key
   * is used for signature verification. */
  uint8_t sigmask;
  /* Reserved bytes (alignment) */
  uint8_t reserved[2];
  /** Size of the entire header in bytes, including the Merkle proof
   * and signatures. It's calculated at link time and must be
   * aligned to 8K boundary. */
  uint32_t header_size;
  /** Size of the authenticated part of the header in bytes.
   * Final value is calculated in post-build step and includes
   * potential padding of the structure. */
  uint32_t auth_size;
  /** Size of the bootloader code in bytes */
  uint32_t code_size;
  /** Address of storage area for storage relocation purposes */
  uint32_t storage_address;
  /* Firmware Merkle tree root */
  merkle_proof_node_t firmware_root;
  /* Padding is automatically added by the post-build step to ensure that
   * the authenticated part of the header is maximized. */
  uint8_t padding[0];

} boot_header_auth_t;

/**
 * Merkle proof structure used in the boot header to calculate the root
 * of the Merkle tree. It is placed just after the authenticated part
 * of the boot header.
 *
 * WARNING: This struct must not change, otherwise old boardloaders will
 * not interpret the header correctly. Any new unauthenticated fields
 * must be added at the end of `boot_header_unauth_t`.
 */
typedef struct __attribute__((packed)) {
  /** Number of nodes in the array below */
  uint32_t node_count;
  /** Merkle proof used for root calculation */
  merkle_proof_node_t nodes[0];

} boot_header_merkle_proof_t;

/**
 * Unauthenticated part of the boot header containing signatures and
 * other information that need not (or must not) be authenticated.
 * It is placed right after the Merkle proof.
 */
typedef struct __attribute__((packed)) {
  /** PQ signatures */
  uint8_t slh_signature[BOOT_HEADER_SIGNATURE_COUNT]
                       [BOOT_HEADER_PQ_SIGNATURE_LEN];
  /** EC signatures */
  uint8_t ec_signature[BOOT_HEADER_SIGNATURE_COUNT]
                      [BOOT_HEADER_EC_SIGNATURE_LEN];

  /* Firmware type
   * This field is modified by the bootloader during the
   * update process). It indicates the current firmware type (custom,
   * universal, bitcoin-only, etc.) and is used to determine whether
   * the storage should be erased before the update.
   */
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
const boot_header_auth_t* boot_header_auth_get(uint32_t address);

/**
 * Gets pointer to the unauthenticated part of the boot header.
 *
 * @param hdr Pointer to the authenticated part of the boot header
 * @return Pointer to the unauthenticated part of the boot header or NULL if the
 *         header is invalid.
 */
const boot_header_unauth_t* boot_header_unauth_get(
    const boot_header_auth_t* hdr);

/**
 *  Calculates the Merkle root for signature verification.
 *
 * The result includes the bootloader code, authenticated part of the
 * boot header and the Merkle tree path.
 *
 * @param hdr Pointer to the boot header
 * @param code_address Address of the bootloader code in flash memory
 * @param root Pointer to the output Merkle root node
 */
void boot_header_calc_merkle_root(const boot_header_auth_t* hdr,
                                  uint32_t code_address,
                                  merkle_proof_node_t* root);

/**
 * Checks the signature in the boot header against the public keys.
 *
 * This function checks the signatures of the boot header using the
 * bootloader public keys. It uses the Merkle root calculated from
 * the boot header and bootloader code to perform the verification.
 *
 * @param hdr Pointer to the boot header
 * @param merkle_root Pointer to the Merkle root
 * @return secbool indicating whether the signature verification was successful.
 */
secbool boot_header_check_signature(const boot_header_auth_t* hdr,
                                    const merkle_proof_node_t* merkle_root);

/**
 * This function compares the boot header and the bootloader code
 * with the installed bootloader header and code. If they are different,
 * it returns sectrue, otherwise secfalse.
 *
 * @param hdr Pointer to the new boot header
 * @param code_address Address of the new bootloader code in flash memory
 * @return secbool indicating whether the boot header and code need update
 */
secbool bootloader_area_needs_update(const boot_header_auth_t* hdr,
                                     uint32_t code_address);
