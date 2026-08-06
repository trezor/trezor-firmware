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

/*
 * Firmware Merkle tree math + module/type helpers, shared verbatim by the
 * embedded build (boot_header.c) and the host cross-validation harness
 * (tests/fw_merkle/crossvalidate.c). One source guarantees the on-device and
 * host implementations are byte-identical.
 *
 * NOTE: this header contains function DEFINITIONS. Include it in exactly one
 * translation unit per program (boot_header.c on device; the harness on host).
 *
 * Dependencies (types, IMAGE_HASH_* macros, memcmp, secbool) are pulled from
 * the real headers below so an IDE resolves the symbols. The host harness
 * defines BOOT_HEADER_MERKLE_SHIMMED and supplies its own minimal shims to
 * avoid dragging in the embedded include tree.
 */

/* The whole file is secure-mode only on device, exactly as boot_header.c is.
 * The cross-validation harness compiles it too, against shimmed types and a
 * host SHA-256, which is what makes it cross-validation rather than a
 * reimplementation
 * -- hence the second arm. */
#if defined(SECURE_MODE) || defined(BOOT_HEADER_MERKLE_SHIMMED)

/* Under the harness these come from its shim header, forced in on the command
 * line; on device from the real ones. */
#ifndef BOOT_HEADER_MERKLE_SHIMMED
#include <string.h>

#include <sec/boot_header.h>
#include <sec/image_hash_conf.h>
#endif

// Combines two nodes into their parent: H(0x01 || min(a,b) || max(a,b)).
static void boot_header_internal_node(const merkle_proof_node_t* a,
                                      const merkle_proof_node_t* b,
                                      merkle_proof_node_t* out) {
  static const uint8_t prefix1[] = {0x01};
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix1, sizeof(prefix1));

// Combines two nodes into their parent: H(0x01 || min(a,b) || max(a,b)).
static void boot_header_internal_node(const merkle_proof_node_t* a,
                                      const merkle_proof_node_t* b,
                                      merkle_proof_node_t* out) {
  static const uint8_t prefix1[] = {0x01};
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix1, sizeof(prefix1));
  if (memcmp(a->bytes, b->bytes, sizeof(a->bytes)) < 0) {
    IMAGE_HASH_UPDATE(&ctx, a->bytes, sizeof(a->bytes));
    IMAGE_HASH_UPDATE(&ctx, b->bytes, sizeof(b->bytes));
  } else {
    IMAGE_HASH_UPDATE(&ctx, b->bytes, sizeof(b->bytes));
    IMAGE_HASH_UPDATE(&ctx, a->bytes, sizeof(a->bytes));
  }
  IMAGE_HASH_FINAL(&ctx, out->bytes);
}

// Computes the variant leaf: H(0x00 || manifest). The manifest (a firmware
// directory) is the per-variant node of the firmware tree; this leaf folds via
// the firmware Merkle proof up to the signed firmware_root.
static void boot_header_variant_leaf(const firmware_manifest_t* manifest,
                                     size_t len, merkle_proof_node_t* leaf) {
  static const uint8_t prefix0[] = {0x00};
  const uint8_t* base = (const uint8_t*)manifest;
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix0, sizeof(prefix0));
  IMAGE_HASH_UPDATE(&ctx, base, len);
  IMAGE_HASH_FINAL(&ctx, leaf->bytes);
}

secbool firmware_manifest_authentic(const firmware_manifest_t* manifest,
                                    size_t manifest_len,
                                    const merkle_proof_node_t* proof,
                                    size_t proof_count,
                                    const merkle_proof_node_t* trusted_root) {
  if (manifest->magic != FW_MANIFEST_MAGIC) {
    return secfalse;
  }
  if (manifest->module_count == 0 ||
      manifest->module_count > BOOT_HEADER_MAX_MODULES) {
    return secfalse;
  }
  // Sanity: the passed length must match the manifest's declared size.
  if (manifest_len != firmware_manifest_size(manifest)) {
    return secfalse;
  }

  // The variant leaf folds (via the proof) up to the signed firmware_root.
  merkle_proof_node_t node;
  boot_header_variant_leaf(manifest, manifest_len, &node);
  for (size_t i = 0; i < proof_count; i++) {
    boot_header_internal_node(&node, &proof[i], &node);
  }
  return (memcmp(node.bytes, trusted_root->bytes, sizeof(node.bytes)) == 0)
             ? sectrue
             : secfalse;
}

// Smart-hashing "chain" code hash: the module code is split into chunk_size
// chunks and folded into a single hash, so an OTA can authenticate each chunk
// against code_hash as it streams (see docs). Here (boot / whole-module) we
// recompute the whole chain over the placed code and compare to code_hash.
//
// Domain-tagged and length-bound, folded LAST chunk -> FIRST (variant A, so
// chunk 0 ends up outermost -> forward-order streaming). Two DISTINCT tags
// separate the two constructions: 0x01 for the seed, 0x02 for each fold step:
//   seed = H(0x01 || size_le32);  H = seed
//   for k = n-1 .. 0:  H = H(0x02 || H || chunk_k)         (n = ceil(size/cs))
//   code_hash = H
// Mirrors firmware_module.module_code_hash() in the Python signer
// byte-for-byte. Chain seed = H(0x01 || size_le32) -- binds the total length
// into the base.
void firmware_module_chain_seed(uint32_t size, uint8_t* out) {
  static const uint8_t tag[1] = {0x01};
  const uint8_t size_le[4] = {(uint8_t)size, (uint8_t)(size >> 8),
                              (uint8_t)(size >> 16), (uint8_t)(size >> 24)};
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, tag, sizeof(tag));
  IMAGE_HASH_UPDATE(&ctx, size_le, sizeof(size_le));
  IMAGE_HASH_FINAL(&ctx, out);
}

// One chain fold: out = H(0x02 || h_prev || data). In-place safe (out ==
// h_prev): h_prev is absorbed by UPDATE before FINAL overwrites out.
void firmware_module_chain_step(const uint8_t* h_prev, const uint8_t* data,
                                size_t len, uint8_t* out) {
  static const uint8_t tag[1] = {0x02};
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, tag, sizeof(tag));
  IMAGE_HASH_UPDATE(&ctx, h_prev, IMAGE_HASH_DIGEST_LENGTH);
  IMAGE_HASH_UPDATE(&ctx, data, len);
  IMAGE_HASH_FINAL(&ctx, out);
}

void firmware_module_code_hash(uintptr_t base, uint32_t addr,
                                      uint32_t size, uint32_t chunk_size,
                                      uint8_t* out) {
  // seed, then fold chunks last -> first (variant A) with the shared step, so
  // the whole-module recompute and the streaming per-chunk verify use identical
  // primitives.
  firmware_module_chain_seed(size, out);
  uint32_t n = (chunk_size != 0) ? (size + chunk_size - 1) / chunk_size : 0;
  for (uint32_t k = n; k-- > 0;) {
    uint32_t off = k * chunk_size;
    uint32_t clen = (size - off < chunk_size) ? (size - off) : chunk_size;
    firmware_module_chain_step(out, (const uint8_t*)(base + addr + off), clen,
                               out);
  }
}

secbool firmware_verify_manifest_entry(const firmware_manifest_entry_t* entry,
                                       uintptr_t firmware_base) {
  // Integrity: the module code at firmware_base + entry->addr (entry->size
  // bytes) must reduce to the entry's code_hash via the smart-hashing chain
  // (firmware_module_code_hash), chunked by the entry's own chunk_size. When the
  // entry is founder-authenticated (firmware_manifest_authentic), this proves
  // the code is both founder-committed and non-corrupt.
  uint8_t digest[IMAGE_HASH_DIGEST_LENGTH];
  firmware_module_code_hash(firmware_base, entry->addr, entry->size,
                            entry->chunk_size, digest);
  return (memcmp(digest, entry->code_hash.bytes, IMAGE_HASH_DIGEST_LENGTH) == 0)
             ? sectrue
             : secfalse;
}

secbool firmware_manifest_layout_valid(const firmware_manifest_t* manifest,
                                       uint32_t capacity) {
  // The module code regions (addr/size) drive both the streamed erase+write
  // (install) and the code hashing (install + EVERY boot). firmware_verify_
  // manifest would hash `size` bytes at `addr`, so a malformed/hostile manifest
  // must be rejected FIRST to avoid an out-of-bounds read past the firmware
  // area. Validate the layout is well-formed + bounded:
  //   * at least one module; per entry a non-zero chunk_size (the code_hash
  //     chain modulus; the module need NOT be a whole number of chunks -- the
  //     last chunk may be partial) and a non-zero size;
  //   * modules ascending + non-overlapping, starting at/after the manifest
  //     region (module addr/size keep their natural FLASH_BLOCK_SIZE build
  //     alignment -- not enforced here, and NOT chunk-aligned);
  //   * wholly inside [.., capacity] (the firmware-area size), overflow-safe.
  // Shared by install (phase 1 pre-confirm, phase 2 pre-write) and boot
  // (firmware_verify_tree). Bound module_count BEFORE iterating entries[]:
  // firmware_manifest_size()'s `module_count * sizeof(entry)` can wrap 32-bit
  // for a crafted count -- so without this, iterating the raw count could read
  // entries[] past the manifest region.
  if (manifest->module_count == 0 ||
      manifest->module_count > BOOT_HEADER_MAX_MODULES) {
    return secfalse;
  }
  uint32_t prev_end = FW_MANIFEST_REGION;  // first module starts after the header
  for (size_t i = 0; i < manifest->module_count; i++) {
    const firmware_manifest_entry_t* e = &manifest->entries[i];
    const uint32_t cs = e->chunk_size;  // per-module chunk size (chain modulus)
    if (cs == 0 || e->size == 0 || e->addr < prev_end || e->addr > capacity ||
        e->size > capacity - e->addr) {
      return secfalse;
    }
    prev_end = e->addr + e->size;  // no overflow: e->size <= capacity - e->addr
  }
  return sectrue;
}

secbool firmware_verify_manifest(const firmware_manifest_t* manifest,
                                 size_t manifest_len, uintptr_t firmware_base,
                                 const merkle_proof_node_t* proof,
                                 size_t proof_count,
                                 const merkle_proof_node_t* trusted_root) {
  // 1. Authenticity: variant leaf (+ proof) == firmware_root. The variant leaf
  //    covers the whole manifest -- incl. firmware_variant + every module's
  //    code_hash -- so the modules and manifest structure are founder-
  //    authenticated.
  if (sectrue != firmware_manifest_authentic(manifest, manifest_len, proof,
                                             proof_count, trusted_root)) {
    return secfalse;
  }

  // 2. Integrity: every module's code reduces to its directory entry's
  //    code_hash (via the smart-hashing chain, chunked by the entry's own
  //    chunk_size). A zero chunk_size is handled safely by
  //    firmware_module_code_hash (n=0 -> digest != code_hash); the caller's
  //    firmware_manifest_layout_valid also rejects it up front.
  for (size_t i = 0; i < manifest->module_count; i++) {
    const firmware_manifest_entry_t* e = &manifest->entries[i];
    if (sectrue != firmware_verify_manifest_entry(e, firmware_base)) {
      return secfalse;
    }
  }

  return sectrue;
}

uint8_t firmware_type_compose(uint32_t variant) {
  // firmware_type IS the variant byte -- custom-ness is FW_VARIANT_CUSTOM, not
  // a flag. The variant is authenticated (manifest leaf) before this is
  // persisted.
  return (uint8_t)variant;
}

uint32_t firmware_type_variant(uint8_t firmware_type) {
  return (uint32_t)firmware_type;
}

#endif  // SECURE_MODE || shimmed
