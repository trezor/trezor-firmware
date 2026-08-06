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
