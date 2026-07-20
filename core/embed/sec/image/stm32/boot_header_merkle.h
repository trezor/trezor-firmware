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
static void boot_header_manifest_leaf(const uint8_t* manifest, size_t len,
                                      merkle_proof_node_t* leaf) {
  static const uint8_t prefix0[] = {0x00};
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix0, sizeof(prefix0));
  IMAGE_HASH_UPDATE(&ctx, manifest, len);
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

  // The variant leaf folds (via the proof) to the signed firmware_root.
  merkle_proof_node_t node;
  boot_header_manifest_leaf((const uint8_t*)manifest, manifest_len, &node);
  for (size_t i = 0; i < proof_count; i++) {
    boot_header_internal_node(&node, &proof[i], &node);
  }
  return (memcmp(node.bytes, trusted_root->bytes, sizeof(node.bytes)) == 0)
             ? sectrue
             : secfalse;
}

secbool firmware_verify_manifest_entry(const firmware_manifest_entry_t* entry,
                                       uintptr_t firmware_base,
                                       secbool allow_custom) {
  // A CUSTOM (unofficial) module skips the code_hash check: the app may be any
  // build, so no founder commitment is enforced on it. allow_custom is gated by
  // the caller (never set for the secmon). Corruption detection for custom app
  // code is out of scope here -- Mod 2 reworks this into a creator-supplied
  // integrity hash carried in the manifest.
  if (allow_custom == sectrue) {
    return sectrue;
  }
  // Integrity + authenticity in one hop: the whole module code at
  // firmware_base + entry->addr (entry->size bytes) must hash to the entry's
  // code_hash. The entry is authenticated by firmware_manifest_authentic (the
  // variant leaf folds to the signed firmware_root), so this single SHA-256
  // proves both that the code is founder-committed and that it is non-corrupt.
  // (The image is written in full before boot, so the code is verified as one
  // module-sized hash; no sub-module/per-chunk streaming verification.)
  uint8_t digest[IMAGE_HASH_DIGEST_LENGTH];
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t*)(firmware_base + entry->addr),
                    entry->size);
  IMAGE_HASH_FINAL(&ctx, digest);
  return (memcmp(digest, entry->code_hash.bytes, IMAGE_HASH_DIGEST_LENGTH) == 0)
             ? sectrue
             : secfalse;
}

secbool firmware_verify_manifest(const firmware_manifest_t* manifest,
                                 size_t manifest_len, uintptr_t firmware_base,
                                 const merkle_proof_node_t* proof,
                                 size_t proof_count,
                                 const merkle_proof_node_t* trusted_root,
                                 secbool custom) {
  // 1. Authenticity: variant leaf (+ proof) == firmware_root. The manifest is
  //    ALWAYS founder-authenticated, even for a custom install -- only an
  //    individual (non-secmon) module's code may deviate from it.
  if (sectrue != firmware_manifest_authentic(manifest, manifest_len, proof,
                                             proof_count, trusted_root)) {
    return secfalse;
  }

  // 2. Integrity: each module's code hashes to its directory entry's code_hash
  //    -- except that a CUSTOM (unofficial) install lets ONLY the non-secure
  //    app (FW_MODULE_APP) deviate (code_hash not enforced). Every other module
  //    type -- secmon AND prodtest -- is ALWAYS bound to the founder manifest:
  //    the secure monitor and the factory-test image must stay trusted.
  for (size_t i = 0; i < manifest->module_count; i++) {
    const firmware_manifest_entry_t* e = &manifest->entries[i];
    secbool allow_custom =
        (custom == sectrue && e->module_type == FW_MODULE_APP) ? sectrue
                                                               : secfalse;
    if (sectrue !=
        firmware_verify_manifest_entry(e, firmware_base, allow_custom)) {
      return secfalse;
    }
  }

  return sectrue;
}

uint8_t firmware_type_compose(uint32_t variant, secbool is_custom) {
  uint8_t t = (uint8_t)(variant & FW_TYPE_VARIANT_MASK);
  if (is_custom == sectrue) {
    t |= FW_TYPE_CUSTOM_FLAG;
  }
  return t;
}

uint32_t firmware_type_variant(uint8_t firmware_type) {
  return (uint32_t)(firmware_type & FW_TYPE_VARIANT_MASK);
}

secbool firmware_type_is_custom(uint8_t firmware_type) {
  return (firmware_type & FW_TYPE_CUSTOM_FLAG) ? sectrue : secfalse;
}
