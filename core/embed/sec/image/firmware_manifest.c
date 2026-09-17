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

/*
 * Firmware manifest authentication, layout and module integrity, shared
 * verbatim by the device build and host tests. Pure layout and hash math over
 * caller-supplied buffers, so not secure-mode gated. The internals kept
 * non-static for the tests are declared in firmware_manifest_internal.h.
 */

// In a host test build these come from its shim header.
#ifndef SEC_IMAGE_SHIMMED
#include <string.h>

#include <sec/firmware_manifest.h>
#include <sec/image_hash_conf.h>

#include "firmware_manifest_internal.h"
#endif

// Variant leaf H(0x00 || manifest). For the CUSTOM variant the creator-owned
// fields -- firmware_version and the APP entry's size + code_hash tail -- are
// hashed as zero, so any creator app folds to the one founder-signed custom
// slot. The only place this substitution happens; must match the Python
// signer.
static void firmware_manifest_variant_leaf(const firmware_manifest_t* manifest,
                                           size_t len,
                                           merkle_proof_node_t* leaf) {
  static const uint8_t prefix0[] = {0x00};
  static const uint8_t zeros[sizeof(firmware_manifest_entry_t)] = {0};
  const uint8_t* base = (const uint8_t*)manifest;
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix0, sizeof(prefix0));

  // Non-custom variants: hash the manifest verbatim.
  if (manifest->firmware_variant != FW_VARIANT_SEC_CUSTOM) {
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
  // Zeroed regions: firmware_version, and the app entry's [size .. end).
  size_t v_off = (size_t)((const uint8_t*)manifest->firmware_version - base);
  size_t v_len = sizeof(manifest->firmware_version);
  size_t a_off = app ? (size_t)((const uint8_t*)&app->size - base) : len;
  size_t a_len =
      app ? (size_t)((const uint8_t*)(app + 1) - (const uint8_t*)&app->size)
          : 0;

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
      manifest->module_count > FW_MANIFEST_MAX_MODULES) {
    return secfalse;
  }
  // The passed length must match the manifest's declared size.
  if (manifest_len != firmware_manifest_size(manifest)) {
    return secfalse;
  }

  // Fold the variant leaf through the proof to the signed firmware_root.
  merkle_proof_node_t node;
  firmware_manifest_variant_leaf(manifest, manifest_len, &node);
  for (size_t i = 0; i < proof_count; i++) {
    merkle_node_hash(&node, &proof[i], &node);
  }
  return (memcmp(node.bytes, trusted_root->bytes, sizeof(node.bytes)) == 0)
             ? sectrue
             : secfalse;
}

// Smart-hashing chain (must match firmware_module.module_code_hash() in the
// Python signer byte-for-byte):
//   seed = H(0x01 || size_le32);  H = seed
//   for k = n-1 .. 0:  H = H(0x02 || H || chunk_k)   (n = ceil(size/cs))
//   code_hash = H
// Folded last -> first so chunk 0 is outermost and an OTA can verify forward.
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
// h_prev).
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

void firmware_module_code_hash(uintptr_t base, uint32_t addr, uint32_t size,
                               uint32_t chunk_size, uint8_t* out) {
  firmware_module_chain_seed(size, out);
  // ceil(size / chunk_size) without the (size + chunk_size - 1) form, which
  // overflows uint32_t for a large chunk_size. k * chunk_size < size, no wrap.
  uint32_t n = (chunk_size != 0)
                   ? size / chunk_size + ((size % chunk_size != 0) ? 1u : 0u)
                   : 0;
  for (uint32_t k = n; k-- > 0;) {
    uint32_t off = k * chunk_size;
    uint32_t clen = (size - off < chunk_size) ? (size - off) : chunk_size;
    firmware_module_chain_step(out, (const uint8_t*)(base + addr + off), clen,
                               out);
  }
}

secbool firmware_verify_manifest_entry(const firmware_manifest_entry_t* entry,
                                       uintptr_t firmware_base) {
  // For the CUSTOM app the code_hash is the creator's, so this is a corruption
  // check only; every other entry is founder-authenticated by the manifest.
  uint8_t digest[IMAGE_HASH_DIGEST_LENGTH];
  firmware_module_code_hash(firmware_base, entry->addr, entry->size,
                            entry->chunk_size, digest);
  return (memcmp(digest, entry->code_hash.bytes, IMAGE_HASH_DIGEST_LENGTH) == 0)
             ? sectrue
             : secfalse;
}

secbool firmware_manifest_layout_valid(const firmware_manifest_t* manifest,
                                       uint32_t capacity) {
  // The CUSTOM app size is zeroed for the fold, so a tampered on-flash size
  // still authenticates -- bound every region before anything hashes or
  // writes it. Bound module_count first: entries[] is read below.
  // Alignment is not checked here (FLASH_BLOCK_SIZE is MCU-specific).
  if (manifest->module_count == 0 ||
      manifest->module_count > FW_MANIFEST_MAX_MODULES) {
    return secfalse;
  }
  uint32_t prev_end =
      FW_MANIFEST_REGION;  // first module starts after the header
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
  // 1. Authenticity: variant leaf (+ proof) == firmware_root.
  if (sectrue != firmware_manifest_authentic(manifest, manifest_len, proof,
                                             proof_count, trusted_root)) {
    return secfalse;
  }

  // 2. Integrity: every module hashes to its entry's code_hash (the custom app
  //    against the creator's hash -- no entry is skipped).
  for (size_t i = 0; i < manifest->module_count; i++) {
    const firmware_manifest_entry_t* e = &manifest->entries[i];
    if (sectrue != firmware_verify_manifest_entry(e, firmware_base)) {
      return secfalse;
    }
  }

  return sectrue;
}
