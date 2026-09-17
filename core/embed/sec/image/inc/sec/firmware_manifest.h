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
#include <sec/merkle.h>

/** Device-side bound on the untrusted manifest module_count. Not stored in
 *  any signed struct, so it can be raised freely. */
#define FW_MANIFEST_MAX_MODULES 8

/** Max firmware Merkle proof nodes in the manifest region (depth is
 *  ceil(log2(variants)); 4 covers 16 variants). Unauthenticated. */
#define FW_MANIFEST_PROOF_MAX_NODES 4

/** Reserved region at the start of the firmware image holding the manifest
 *  and its proof; the first module starts after it. Must match the
 *  `.manifest` reserve in the *_pq.ld scripts and the signer. */
#define FW_MANIFEST_REGION 0x400

/** Smart-hashing chunk size (== COREAPP_ALIGNMENT) the image build stamps into
 *  every manifest entry (manifest_header.c). Modules are not padded to it.
 *  Must match DEFAULT_CHUNK_SIZE in tools/trezor_core_tools/firmware_module.py.
 */
#define FW_CHUNK_SIZE 0x2000

/** Firmware module role, authenticated in the manifest entry. Only APP may
 *  deviate from the founder manifest in a CUSTOM install. */
typedef enum {
  FW_MODULE_SECMON = 1,
  FW_MODULE_APP = 2,  // non-secure application (kernel+coreapp)
  FW_MODULE_PRODTEST = 3,
} fw_module_type_t;

/** Magic at the start of a firmware manifest ('TRZD', little-endian u32). */
#define FW_MANIFEST_MAGIC 0x445A5254

/** Manifest entry `flags` bits. */
// The module the bootloader jumps to in secure mode; exactly one entry per
// manifest must set it (authenticated).
#define FW_MANIFEST_ENTRY_FLAG_BOOT 0x1

/**
 * One entry of a firmware manifest's module directory. `code_hash` is the
 * smart-hashing chain over `size` bytes at `addr` (offset from the firmware
 * region start), chunked by `chunk_size`. `chunk_size` precedes `size` so the
 * CUSTOM variant's zeroed tail (`size` + `code_hash`) leaves it authenticated.
 */
typedef struct __attribute__((packed)) {
  uint32_t module_type; /**< fw_module_type_t (role) */
  uint32_t flags;       /**< FW_MANIFEST_ENTRY_FLAG_* */
  uint32_t addr;       /**< module code offset from the firmware region start */
  uint32_t chunk_size; /**< smart-hashing chunk size; bounded only at install */
  uint32_t size;       /**< module code size */
  merkle_proof_node_t
      code_hash; /**< smart-hashing chain over the module code */
} firmware_manifest_entry_t;

/**
 * Firmware manifest -- the variant leaf H(0x00 || manifest), placed at the
 * start of the firmware image. The firmware Merkle proof follows it at
 * firmware_manifest_size, OUTSIDE the leaf. Layout must match
 * tools/trezor_core_tools/firmware_module.py byte-for-byte.
 */
typedef struct __attribute__((packed)) {
  uint32_t magic;                        /**< FW_MANIFEST_MAGIC */
  fw_variant_sec_t firmware_variant;     /**< hardened variant codeword */
  uint8_t firmware_version[4];           /**< major, minor, patch, build */
  merkle_proof_node_t translations_root; /**< translations root, or 0 */
  uint32_t module_count;                 /**< number of directory entries */
  firmware_manifest_entry_t entries[];   /**< module_count directory entries */
} firmware_manifest_t;

/** Total size of a manifest (fixed part + entries) -- the span the variant
 *  leaf covers. An out-of-range `module_count` saturates to SIZE_MAX, so a
 *  size comparison rejects it instead of the product wrapping in 32 bits;
 *  entries may still only be read after a bound check. */
static inline size_t firmware_manifest_size(const firmware_manifest_t* m) {
  if (m->module_count == 0 || m->module_count > FW_MANIFEST_MAX_MODULES) {
    return SIZE_MAX;
  }
  return sizeof(firmware_manifest_t) +
         (size_t)m->module_count * sizeof(firmware_manifest_entry_t);
}

/**
 * Firmware Merkle proof: co-path from the variant leaf to firmware_root, placed
 * right after the manifest within FW_MANIFEST_REGION (outside the leaf).
 * Unauthenticated -- verified by folding. node_count 0 means the variant leaf
 * is firmware_root. Layout must match firmware_module.py.
 */
typedef struct __attribute__((packed)) {
  uint32_t node_count; /**< proof nodes (<= FW_MANIFEST_PROOF_MAX_NODES) */
  merkle_proof_node_t nodes[]; /**< node_count co-path nodes */
} firmware_manifest_proof_t;

/** Bytes of the manifest region taken by a manifest with `n` entries plus a
 *  proof of FW_MANIFEST_PROOF_MAX_NODES nodes. The image build emits only the
 *  manifest (manifest_header.c); the linker pads `.manifest` to
 *  FW_MANIFEST_REGION, and the zeroed gap is the empty proof (node_count 0)
 *  the signer fills in place. */
#define FW_MANIFEST_REGION_USED(n)                                         \
  (sizeof(firmware_manifest_t) + (n) * sizeof(firmware_manifest_entry_t) + \
   sizeof(firmware_manifest_proof_t) +                                     \
   FW_MANIFEST_PROOF_MAX_NODES * sizeof(merkle_proof_node_t))

/** A linker-defined absolute symbol's value (e.g. a module offset or size) as
 *  a manifest field initializer. Device builds only: needs 32-bit pointers. */
#define FW_MANIFEST_LINKER_VALUE(sym) ((uint32_t)(uintptr_t)(sym))

/** Pointer to the embedded proof. No bounds check -- use
 *  firmware_manifest_read_proof for untrusted input. */
static inline const firmware_manifest_proof_t* firmware_manifest_proof(
    const firmware_manifest_t* m) {
  return (const firmware_manifest_proof_t*)((const uint8_t*)m +
                                            firmware_manifest_size(m));
}

/**
 * Bounds-checked read of the embedded proof; `avail` is the number of bytes
 * available from the manifest start. Fails closed with cleared outputs;
 * *out_nodes is NULL when node_count == 0.
 */
static inline secbool firmware_manifest_read_proof(
    const firmware_manifest_t* m, size_t avail,
    const merkle_proof_node_t** out_nodes, size_t* out_count) {
  *out_nodes = NULL;
  *out_count = 0;
  // Bound module_count before firmware_manifest_size can wrap.
  if (m->module_count == 0 || m->module_count > FW_MANIFEST_MAX_MODULES) {
    return secfalse;
  }
  size_t manifest_len = firmware_manifest_size(m);
  if (avail < manifest_len + sizeof(uint32_t)) {
    return secfalse;
  }
  const firmware_manifest_proof_t* p = firmware_manifest_proof(m);
  uint32_t count = p->node_count;
  if (count > FW_MANIFEST_PROOF_MAX_NODES) {
    return secfalse;
  }
  if (avail < manifest_len + sizeof(uint32_t) +
                  (size_t)count * sizeof(merkle_proof_node_t)) {
    return secfalse;
  }
  *out_count = count;
  *out_nodes = (count > 0) ? p->nodes : NULL;
  return sectrue;
}

/**
 * Header-only manifest authenticity: variant leaf folded through `proof` must
 * equal `trusted_root`. Reads no module code. For CUSTOM the leaf hashes
 * firmware_version and the APP entry's size + code_hash as zero.
 *
 * @param manifest Manifest bytes
 * @param manifest_len Manifest length (firmware_manifest_size)
 * @param proof Firmware Merkle proof (variant leaf -> firmware_root); may be
 * NULL
 * @param proof_count Number of proof nodes
 * @param trusted_root The signed firmware_root to check against
 * @return sectrue iff the manifest authenticates against the root
 */
secbool firmware_manifest_authentic(const firmware_manifest_t* manifest,
                                    size_t manifest_len,
                                    const merkle_proof_node_t* proof,
                                    size_t proof_count,
                                    const merkle_proof_node_t* trusted_root);

/**
 * @brief Checks the module layout: >= 1 module; non-zero chunk_size and size;
 *        ascending, non-overlapping, at/after FW_MANIFEST_REGION, inside
 *        `capacity`. FLASH_BLOCK_SIZE alignment is NOT checked here (sec/
 *        cannot see it); the bootloader enforces it alongside.
 *
 * @param manifest  Manifest at the start of the firmware image
 * @param capacity  Size of the firmware area the modules must fit inside
 * @return sectrue iff the layout is well-formed and within capacity
 */
secbool firmware_manifest_layout_valid(const firmware_manifest_t* manifest,
                                       uint32_t capacity);

/**
 * @brief Full firmware verification: firmware_manifest_authentic, then every
 *        module's code must hash to its entry's code_hash (for the CUSTOM app
 *        that is the creator's hash -- integrity only).
 *
 * @param manifest Manifest at the start of the firmware image
 * @param manifest_len Manifest length in bytes (firmware_manifest_size)
 * @param firmware_base Base address the manifest `addr` offsets are relative to
 * @param proof Firmware Merkle proof (variant leaf -> firmware_root)
 * @param proof_count Number of proof nodes
 * @param trusted_root The signed firmware_root to check against
 * @return sectrue iff authenticity and integrity all hold
 */
secbool firmware_verify_manifest(const firmware_manifest_t* manifest,
                                 size_t manifest_len, uintptr_t firmware_base,
                                 const merkle_proof_node_t* proof,
                                 size_t proof_count,
                                 const merkle_proof_node_t* trusted_root);

/**
 * Integrity check of ONE manifest entry: `size` bytes at `firmware_base +
 * addr` must hash to `code_hash`. The manifest must already be authenticated.
 *
 * @param entry One (authenticated) manifest directory entry
 * @param firmware_base Base address the entry `addr` offset is relative to
 * @return sectrue iff the module code matches the entry's code_hash
 */
secbool firmware_verify_manifest_entry(const firmware_manifest_entry_t* entry,
                                       uintptr_t firmware_base);

/** Smart-hashing chain primitives (whole-module recompute + streaming
 *  installer): seed = H(0x01 || size_le32), step = H(0x02 || h || chunk),
 *  folded last chunk -> first (docs/core/embed-arch/firmware-merkle-tree.md).
 */
void firmware_module_chain_seed(uint32_t size, uint8_t* out);
void firmware_module_chain_step(const uint8_t* h_prev, const uint8_t* data,
                                size_t len, uint8_t* out);
