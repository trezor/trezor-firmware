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
//
// CUSTOM variant (firmware_variant == FW_VARIANT_CUSTOM): EVERYTHING the creator
// controls is substituted with ZERO before hashing, so ANY creator app (any
// code, size, or version) authenticates to the ONE founder-signed custom slot:
//   * the manifest firmware_version (the creator's app version), and
//   * the app (FW_MODULE_APP) entry's size + code_hash (the contiguous tail of
//     the entry).
// The app entry's module_type/flags/addr and the ENTIRE secmon entry stay real
// -- the founder still binds the secmon and the app's role + placement. This is
// the SINGLE place the zero-for-fold substitution happens (device + Python signer
// in lockstep); the on-flash values are used only for integrity/display.
static void boot_header_variant_leaf(const firmware_manifest_t* manifest,
                                     size_t len, merkle_proof_node_t* leaf) {
  static const uint8_t prefix0[] = {0x00};
  static const uint8_t zeros[sizeof(firmware_manifest_entry_t)] = {0};
  const uint8_t* base = (const uint8_t*)manifest;
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix0, sizeof(prefix0));

  // Non-custom variants: hash the manifest verbatim.
  if (manifest->firmware_variant != FW_VARIANT_CUSTOM) {
    IMAGE_HASH_UPDATE(&ctx, base, len);
    IMAGE_HASH_FINAL(&ctx, leaf->bytes);
    return;
  }

  const firmware_manifest_entry_t* app = NULL;
  for (size_t i = 0; i < manifest->module_count; i++) {
    if (manifest->entries[i].module_type == FW_MODULE_APP) {
      app = &manifest->entries[i];
      break;
    }
  }
  // Region 1: firmware_version. Region 2: app entry [size .. end-of-entry]
  // (size + code_hash are the entry's contiguous tail).
  size_t v_off = (size_t)((const uint8_t*)manifest->firmware_version - base);
  size_t v_len = sizeof(manifest->firmware_version);
  size_t a_off = app ? (size_t)((const uint8_t*)&app->size - base) : len;
  size_t a_len =
      app ? (size_t)((const uint8_t*)(app + 1) - (const uint8_t*)&app->size) : 0;

  if (app == NULL || a_off + a_len > len || a_off < v_off + v_len) {
    // Malformed custom manifest -> hash verbatim; it won't match a signed leaf.
    IMAGE_HASH_UPDATE(&ctx, base, len);
    IMAGE_HASH_FINAL(&ctx, leaf->bytes);
    return;
  }
  // [0,v_off) 0(v_len) [v_off+v_len, a_off) 0(a_len) [a_off+a_len, len)
  IMAGE_HASH_UPDATE(&ctx, base, v_off);
  IMAGE_HASH_UPDATE(&ctx, zeros, v_len);
  IMAGE_HASH_UPDATE(&ctx, base + v_off + v_len, a_off - (v_off + v_len));
  IMAGE_HASH_UPDATE(&ctx, zeros, a_len);
  IMAGE_HASH_UPDATE(&ctx, base + a_off + a_len, len - (a_off + a_len));
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

  // The variant leaf folds (via the proof) to the signed firmware_root. For the
  // custom variant the leaf helper zeroes the app code_hash (see above).
  merkle_proof_node_t node;
  boot_header_variant_leaf(manifest, manifest_len, &node);
  for (size_t i = 0; i < proof_count; i++) {
    boot_header_internal_node(&node, &proof[i], &node);
  }
  return (memcmp(node.bytes, trusted_root->bytes, sizeof(node.bytes)) == 0)
             ? sectrue
             : secfalse;
}

secbool firmware_verify_manifest_entry(const firmware_manifest_entry_t* entry,
                                       uintptr_t firmware_base) {
  // Integrity: the whole module code at firmware_base + entry->addr
  // (entry->size bytes) must hash to the entry's code_hash. For an official
  // variant the entry is founder-authenticated (firmware_manifest_authentic),
  // so this proves the code is both founder-committed and non-corrupt. For the
  // CUSTOM variant the app's code_hash is the creator's (NOT founder-signed --
  // zeroed in the authenticity fold), so for the app this is a corruption check
  // only; the secmon's code_hash is still founder-signed. (The image is written
  // in full before boot, so the code is verified as one module-sized hash; no
  // sub-module/per-chunk streaming verification.)
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
                                 const merkle_proof_node_t* trusted_root) {
  // 1. Authenticity: variant leaf (+ proof) == firmware_root. The variant leaf
  //    covers the whole manifest -- incl. firmware_variant + the secmon's
  //    code_hash -- so the secmon and manifest structure are ALWAYS founder-
  //    authenticated. For the custom variant the app code_hash is zeroed in the
  //    leaf (firmware_manifest_authentic), so the app is not founder-bound.
  if (sectrue != firmware_manifest_authentic(manifest, manifest_len, proof,
                                             proof_count, trusted_root)) {
    return secfalse;
  }

  // 2. Integrity: every module's code hashes to its directory entry's code_hash.
  //    For official variants that hash is founder-signed; for the custom app it
  //    is the creator's (corruption check). No entry is skipped -- the custom
  //    app is still verified against its own (creator) hash.
  for (size_t i = 0; i < manifest->module_count; i++) {
    const firmware_manifest_entry_t* e = &manifest->entries[i];
    if (sectrue != firmware_verify_manifest_entry(e, firmware_base)) {
      return secfalse;
    }
  }

  return sectrue;
}

uint8_t firmware_type_compose(uint32_t variant) {
  // firmware_type IS the variant byte -- custom-ness is FW_VARIANT_CUSTOM, not a
  // flag. The variant is authenticated (manifest leaf) before this is persisted.
  return (uint8_t)variant;
}

uint32_t firmware_type_variant(uint8_t firmware_type) {
  return (uint32_t)firmware_type;
}

secbool firmware_type_is_custom(uint8_t firmware_type) {
  return (firmware_type == (uint8_t)FW_VARIANT_CUSTOM) ? sectrue : secfalse;
}

secbool firmware_type_is_official(uint8_t firmware_type) {
  // Positive allow-list: official ONLY for a recognized founder variant that is
  // not custom. A glitched/unknown byte falls through to secfalse (restricted).
  switch (firmware_type) {
    case FW_VARIANT_UNIVERSAL:
    case FW_VARIANT_BITCOIN_ONLY:
    case FW_VARIANT_PRODTEST:
      return sectrue;
    default:
      return secfalse;  // custom, none, or unknown -> not official
  }
}
