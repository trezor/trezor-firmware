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

// Computes a single module's Merkle leaf: H(0x00 || header).
//
// The leaf commits only to the module's authenticated header. The header
// carries the per-chunk hashes of the code, so the code is covered
// transitively (signature -> root -> header -> chunk hashes -> code) yet the
// code itself is NOT hashed here -- it is verified separately, per chunk,
// during streaming install/boot. This keeps signature verification
// header-only: cheap and independent of the (large) code.
static void boot_header_module_leaf(const boot_header_module_t* module,
                                    merkle_proof_node_t* leaf) {
  static const uint8_t prefix0[] = {0x00};
  IMAGE_HASH_CTX ctx;

  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix0, sizeof(prefix0));
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t*)module->hdr,
                    firmware_module_header_size(module->hdr));
  IMAGE_HASH_FINAL(&ctx, leaf->bytes);
}

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

secbool boot_header_calc_firmware_root(const boot_header_module_t* modules,
                                       size_t module_count,
                                       const merkle_proof_node_t* proof,
                                       size_t proof_count,
                                       merkle_proof_node_t* root) {
  if (module_count == 0 || module_count > BOOT_HEADER_MAX_MODULES) {
    return secfalse;
  }
  if (proof_count > 0 && proof == NULL) {
    return secfalse;
  }

  // --- Phase 1: build the on-device subtree from the modules ---------------

  // Compute the leaf of each module.
  merkle_proof_node_t level[BOOT_HEADER_MAX_MODULES];
  for (size_t i = 0; i < module_count; i++) {
    boot_header_module_leaf(&modules[i], &level[i]);
  }

  // Order leaves by hash (matches trezorlib MerkleTree; only the bottom level
  // is sorted, upper levels are paired left-to-right). Insertion sort.
  for (size_t i = 1; i < module_count; i++) {
    merkle_proof_node_t key = level[i];
    size_t j = i;
    while (j > 0 &&
           memcmp(level[j - 1].bytes, key.bytes, sizeof(key.bytes)) > 0) {
      level[j] = level[j - 1];
      j--;
    }
    level[j] = key;
  }

  // Pair up levels until a single subtree root remains; carry an odd node up.
  size_t count = module_count;
  while (count > 1) {
    size_t out = 0;
    size_t i = 0;
    for (; i + 1 < count; i += 2) {
      boot_header_internal_node(&level[i], &level[i + 1], &level[out]);
      out++;
    }
    if (i < count) {
      level[out] = level[i];  // odd node carried up
      out++;
    }
    count = out;
  }

  // --- Phase 2: fold the proof path (off-device siblings) ------------------

  merkle_proof_node_t node = level[0];
  for (size_t i = 0; i < proof_count; i++) {
    boot_header_internal_node(&node, &proof[i], &node);
  }

  *root = node;
  return sectrue;
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

secbool firmware_module_verify_code(const boot_header_module_t* module) {
  const firmware_module_header_t* hdr = module->hdr;
  // Single SHA-256 over the whole module code == hdr->code_hash. (The image is
  // written in full before boot, so the code is always verified as one
  // module-sized hash; no sub-module/per-chunk streaming verification.)
  uint8_t digest[IMAGE_HASH_DIGEST_LENGTH];
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, (const uint8_t*)module->code_address, hdr->code_size);
  IMAGE_HASH_FINAL(&ctx, digest);
  return (memcmp(digest, hdr->code_hash.bytes, IMAGE_HASH_DIGEST_LENGTH) == 0)
             ? sectrue
             : secfalse;
}

secbool firmware_verify_headers(const boot_header_module_t* modules,
                                size_t count, const uint32_t* expected_roles,
                                const merkle_proof_node_t* proof,
                                size_t proof_count,
                                const merkle_proof_node_t* trusted_root) {
  // 1. Role-binding: each module must sit in its expected slot (and be a
  //    firmware module at all). This is a compile-time-fixed policy on-device.
  for (size_t i = 0; i < count; i++) {
    if (modules[i].hdr->magic != FW_MODULE_MAGIC) {
      return secfalse;
    }
    if (modules[i].hdr->module_type != expected_roles[i]) {
      return secfalse;
    }
  }

  // 2. Authenticity: recompute the firmware root from the module headers and
  //    compare to the trusted (signed) firmware_root from the bootloader
  //    header. This authenticates the headers (and the chunk hashes they commit
  //    to) WITHOUT reading the module code -- so it can run before any body is
  //    present, e.g. on the update preamble (headers only).
  merkle_proof_node_t root;
  if (sectrue != boot_header_calc_firmware_root(modules, count, proof,
                                                proof_count, &root)) {
    return secfalse;
  }
  if (memcmp(root.bytes, trusted_root->bytes, sizeof(root.bytes)) != 0) {
    return secfalse;
  }

  return sectrue;
}

secbool firmware_verify(const boot_header_module_t* modules, size_t count,
                        const uint32_t* expected_roles,
                        const merkle_proof_node_t* proof, size_t proof_count,
                        const merkle_proof_node_t* trusted_root) {
  // Header authenticity (role-binding + recomputed root == signed root).
  if (sectrue != firmware_verify_headers(modules, count, expected_roles, proof,
                                         proof_count, trusted_root)) {
    return secfalse;
  }

  // Integrity: each module's code must match its (now-trusted) chunk hashes.
  for (size_t i = 0; i < count; i++) {
    if (sectrue != firmware_module_verify_code(&modules[i])) {
      return secfalse;
    }
  }

  return sectrue;
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
  const firmware_module_header_t* hdr =
      (const firmware_module_header_t*)(firmware_base + entry->addr);
  if (hdr->magic != FW_MODULE_MAGIC) {
    return secfalse;
  }
  // Authenticity: the installed header must hash to this directory entry's
  // header_hash (which commits its module_type/size/chunk hashes). A CUSTOM
  // (unofficial) module skips this bind -- only self-consistency (its code
  // matches its OWN header, checked below) is required, so it may deviate from
  // the founder-committed module while still being non-corrupt. allow_custom is
  // gated by the caller (never set for the secmon).
  if (allow_custom != sectrue) {
    merkle_proof_node_t hh;
    IMAGE_HASH_CTX ctx;
    IMAGE_HASH_INIT(&ctx);
    IMAGE_HASH_UPDATE(&ctx, (const uint8_t*)hdr,
                      firmware_module_header_size(hdr));
    IMAGE_HASH_FINAL(&ctx, hh.bytes);
    if (memcmp(hh.bytes, entry->header_hash.bytes, sizeof(hh.bytes)) != 0) {
      return secfalse;
    }
  }
  boot_header_module_t m = {
      .hdr = hdr,
      .code_address = firmware_base + entry->addr + FW_MODULE_HEADER_REGION,
  };
  return firmware_module_verify_code(&m);
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

  // 2. Integrity: each module's TRZM header hashes to its directory entry's
  //    header_hash (which commits its chunk hashes), and its code matches --
  //    except that a CUSTOM (unofficial) install lets ONLY the non-secure app
  //    (FW_MODULE_APP) deviate (self-consistency only). Every other module type
  //    -- secmon AND prodtest -- is ALWAYS bound to the founder manifest: the
  //    secure monitor and the factory-test image must stay trusted.
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
