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

#include <sec/fw_variant.h>
#include <sec/image_hash_conf.h>
#include <sec/merkle.h>

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
 * Orders two boot header versions, most significant component first.
 *
 * @return <0 if `a` precedes `b`, 0 if they are equal, >0 if `a` follows `b`
 */
static inline int boot_header_version_compare(boot_header_version_t a,
                                              boot_header_version_t b) {
  if (a.major != b.major) return (int)a.major - (int)b.major;
  if (a.minor != b.minor) return (int)a.minor - (int)b.minor;
  if (a.patch != b.patch) return (int)a.patch - (int)b.patch;
  return (int)a.build - (int)b.build;
}

/** Whether a version field is set; 0.0.0.0 means "no constraint". */
static inline bool boot_header_version_is_set(boot_header_version_t v) {
  return (v.major | v.minor | v.patch | v.build) != 0;
}

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
  /** Release version: the universal / bitcoin-only firmware_version of the
   * release this header was signed in, stamped by the signer. The
   * bootloader's own version is the compile-time VERSION_* (intro screen,
   * Features). */
  boot_header_version_t version;
  /** Minimum release version that the device can be downgraded to without
   * erasing storage. */
  boot_header_version_t fix_version;
  /** Minimum installed release version that this header may be installed
   * over; 0.0.0.0 = no floor. */
  boot_header_version_t min_prev_version;
  /** An integer which must not decrease between updates. A bootloader
   * compile constant, unlike the release versions above. */
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
   * Copied from the authenticated manifest variant; trusted only because the
   * bootloader is the sole writer of this write-protected region.
   */
  fw_variant_sec_t firmware_type;

  /* The firmware Merkle proof is NOT stored here; it lives in the firmware
   * image (firmware_manifest_proof_t). New unauth fields go at the END. */

} boot_header_unauth_t;

/**
 * Verifies the integrity of the boot header.
 *
 * Checks the magic number, header size, code size, hardware model and revision
 *
 * @param header Address of the boot header (any readable buffer)
 * @return Pointer to the boot header if valid, NULL otherwise.
 */
const boot_header_auth_t* boot_header_auth_get(uintptr_t header);

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
 * @param code Address of the bootloader code
 * @param root Pointer to the output Merkle root node
 */
void boot_header_calc_merkle_root(const boot_header_auth_t* hdr, uintptr_t code,
                                  merkle_proof_node_t* root);

/**
 * As boot_header_calc_merkle_root, but takes H(code) instead of the code, so
 * the signature can be checked before the code arrives. The caller must still
 * recompute the digest over the real bytes once they land.
 *
 * @param hdr Pointer to the boot header
 * @param code_hash IMAGE_HASH_DIGEST_LENGTH bytes, the digest of the code
 * @param root Pointer to the output Merkle root node
 */
void boot_header_calc_merkle_root_from_hash(
    const boot_header_auth_t* hdr,
    const uint8_t code_hash[IMAGE_HASH_DIGEST_LENGTH],
    merkle_proof_node_t* root);

/** Size in bytes of a boot header Merkle proof (fixed part + nodes). */
static inline size_t boot_header_merkle_proof_size(
    const boot_header_merkle_proof_t* proof) {
  return sizeof(boot_header_merkle_proof_t) +
         (size_t)proof->node_count * sizeof(proof->nodes[0]);
}

/**
 * @brief Extent of the boot header PREFIX: authenticated part + Merkle proof,
 *        excluding the unauthenticated part (which need not be present).
 *
 * @param data Start of a boot header, or of a prefix of one
 * @param len Bytes available at `data`
 * @param out_extent Receives auth_size + proof size
 * @return sectrue iff the prefix is well-formed within `len`
 */
secbool boot_header_prefix_extent(const uint8_t* data, size_t len,
                                  size_t* out_extent);

/**
 * @brief Consent digest of an interaction-less upgrade:
 *        H(header prefix || firmware manifest). Firmware and bootloader must
 *        both use this. The unauth part is excluded on purpose (signatures,
 *        and firmware_type, which the bootloader rewrites). Known gap: the
 *        bootloader CODE is not pinned, only its auth part.
 *
 * @param prefix Boot header prefix (auth part + Merkle proof)
 * @param prefix_len Its length, from `boot_header_prefix_extent`
 * @param manifest Firmware manifest bytes as received
 * @param manifest_len Manifest length (`firmware_manifest_size`)
 * @param out Receives the digest
 * @return sectrue on success
 */
secbool boot_header_consent_digest(const uint8_t* prefix, size_t prefix_len,
                                   const uint8_t* manifest, size_t manifest_len,
                                   merkle_proof_node_t* out);

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
 * @param code Address of the new bootloader code
 * @param prev_header Address of the installed boot header; the installed code
 *        is taken to follow it, at its own `header_size`
 * @return secbool indicating whether the boot header and code need update
 */
secbool bootloader_area_needs_update(const boot_header_auth_t* hdr,
                                     uintptr_t code, uintptr_t prev_header);
