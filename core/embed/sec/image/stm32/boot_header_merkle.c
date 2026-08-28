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
 * Firmware Merkle tree math + module/type helpers, shared verbatim by the
 * embedded build (boot_header.c) and the host cross-validation harness
 * (tests/fw_merkle/crossvalidate.c). One source guarantees the on-device and
 * host implementations are byte-identical.
 *
 * The functions it exports are declared in sec/boot_header.h. The few kept
 * non-static so the harness can compare intermediate values are declared in
 * boot_header_merkle_internal.h.
 */

/* Deliberately NOT secure-mode gated, unlike boot_header.c. Everything here is
 * pure layout + hash math over a caller-supplied buffer -- no keys, no flash,
 * no MPU-gated regions -- so it is equally valid unprivileged. The coreapp
 * needs it to derive the interaction-less upgrade consent digest from a
 * preamble the host sent (check_firmware_header), and doing that parse
 * unprivileged is the SAFER placement: a wrong digest can only get the install
 * refused by the bootloader, which recomputes it independently. gc-sections
 * drops whatever a given binary does not call.
 *
 * The cross-validation harness compiles this file too, against shimmed types
 * and a host SHA-256, which is what makes it cross-validation rather than a
 * reimplementation. */

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
// CUSTOM variant (firmware_variant == FW_VARIANT_CUSTOM): EVERYTHING the
// creator controls is substituted with ZERO before hashing, so ANY creator app
// (any code, size, or version) authenticates to the ONE founder-signed custom
// slot:
//   * the manifest firmware_version (the creator's app version), and
//   * the app (FW_MODULE_APP) entry's size + code_hash (the contiguous tail of
//     the entry -- chunk_size sits BEFORE it and is NOT zeroed).
// The app entry's module_type/flags/addr/chunk_size and the ENTIRE secmon entry
// stay real -- the founder still binds the secmon and the app's role +
// placement + chunk_size (a layout param, not creator content). This is
// the SINGLE place the zero-for-fold substitution happens (device + Python
// signer in lockstep); the on-flash values are used only for integrity/display.
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

void firmware_module_code_hash(uintptr_t base, uint32_t addr, uint32_t size,
                               uint32_t chunk_size, uint8_t* out) {
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
  // (firmware_module_code_hash), chunked by the entry's own chunk_size. For an
  // official variant the entry is founder-authenticated
  // (firmware_manifest_authentic), so this proves the code is both founder-
  // committed and non-corrupt. For the CUSTOM variant the app's code_hash is
  // the creator's (NOT founder-signed -- zeroed in the authenticity fold), so
  // for the app this is a corruption check only; the secmon's code_hash is
  // still founder-signed.
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
  // (install) and the code hashing (install + EVERY boot). For an official
  // variant addr/size are founder-authenticated, but for the CUSTOM variant the
  // app entry's size is zeroed-for-fold (see boot_header_variant_leaf) -- so a
  // tampered on-flash app size still authenticates, yet
  // firmware_verify_manifest would hash `size` bytes at `addr`: an
  // out-of-bounds read past the firmware area if unbounded. Validate the layout
  // is well-formed + bounded FIRST:
  //   * at least one module; per entry a non-zero chunk_size (the code_hash
  //     chain modulus; the module need NOT be a whole number of chunks -- the
  //     last chunk may be partial) and a non-zero size;
  //   * modules ascending + non-overlapping, starting at/after the manifest
  //     region (module addr/size keep their natural FLASH_BLOCK_SIZE build
  //     alignment -- not enforced here, and NOT chunk-aligned);
  //   * wholly inside [.., capacity] (the firmware-area size), overflow-safe.
  // Shared by install (phase 1 pre-confirm, phase 2 pre-write) and boot
  // (firmware_verify_tree), so a malformed/hostile manifest is rejected before
  // any code read. Does NOT check chunk_size against the transport staging
  // buffer -- that is a streaming concern the install path checks separately.
  // Bound module_count BEFORE iterating entries[]: at boot this runs before
  // firmware_manifest_authentic's own module_count<=BOOT_HEADER_MAX_MODULES
  // check (which is inside firmware_verify_manifest, called after), and
  // firmware_manifest_size()'s `module_count * sizeof(entry)` can wrap 32-bit
  // for a crafted count -- so without this, iterating the raw count could read
  // entries[] past the manifest region.
  if (manifest->module_count == 0 ||
      manifest->module_count > BOOT_HEADER_MAX_MODULES) {
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
  // 1. Authenticity: variant leaf (+ proof) == firmware_root. The variant leaf
  //    covers the whole manifest -- incl. firmware_variant + the secmon's
  //    code_hash -- so the secmon and manifest structure are ALWAYS founder-
  //    authenticated. For the custom variant the app code_hash is zeroed in the
  //    leaf (firmware_manifest_authentic), so the app is not founder-bound.
  if (sectrue != firmware_manifest_authentic(manifest, manifest_len, proof,
                                             proof_count, trusted_root)) {
    return secfalse;
  }

  // 2. Integrity: every module's code reduces to its directory entry's
  // code_hash
  //    (via the smart-hashing chain, chunked by the entry's own chunk_size).
  //    For official variants that hash is founder-signed; for the custom app it
  //    is the creator's (corruption check). No entry is skipped -- the custom
  //    app is still verified against its own (creator) hash. A zero chunk_size
  //    is handled safely by firmware_module_code_hash (n=0 -> digest !=
  //    code_hash); the caller's firmware_manifest_layout_valid also rejects it
  //    up front.
  for (size_t i = 0; i < manifest->module_count; i++) {
    const firmware_manifest_entry_t* e = &manifest->entries[i];
    if (sectrue != firmware_verify_manifest_entry(e, firmware_base)) {
      return secfalse;
    }
  }

  return sectrue;
}

// Generic Merkle leaf hash H(0x00 || data). The firmware variant leaf
// (boot_header_variant_leaf) is the manifest-specific case; this is the plain
// leaf used for the nRF (over MCUboot's signed region) -- see
// nrf_image_verify_in_tree.
void merkle_leaf_hash(const uint8_t* data, size_t len,
                      merkle_proof_node_t* out) {
  static const uint8_t prefix0[] = {0x00};
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix0, sizeof(prefix0));
  IMAGE_HASH_UPDATE(&ctx, data, len);
  IMAGE_HASH_FINAL(&ctx, out->bytes);
}

// Fold a MODEL-tree slot value up to modelRoot.
//
// A slot value is the 32 bytes a co-processor (or anything else sharing the
// model tree) is committed by; this hashes it into a leaf and folds the
// co-path. Nothing here knows what produced the value -- which is the point:
// every slot folds identically, so adding a second co-processor needs no new
// fold.
//
// The caller must ALSO pin the value to the right device where that matters:
// every model's slot hangs under the same modelRoot, so a passing fold proves
// founder-commitment, not identity. Mirrors the firmware-variant fold
// (firmware_manifest_authentic), one tree level up.
secbool boot_header_verify_slot(const uint8_t* slot_value,
                                const merkle_proof_node_t* proof,
                                size_t proof_count,
                                const merkle_proof_node_t* trusted_model_root) {
  if (slot_value == NULL || trusted_model_root == NULL) {
    return secfalse;
  }
  merkle_proof_node_t node;
  merkle_leaf_hash(slot_value, IMAGE_HASH_DIGEST_LENGTH, &node);
  for (size_t i = 0; i < proof_count; i++) {
    boot_header_internal_node(&node, &proof[i], &node);
  }
  return (memcmp(node.bytes, trusted_model_root->bytes, sizeof(node.bytes)) ==
          0)
             ? sectrue
             : secfalse;
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

// Display identity for a firmware_type byte. ONE definition shared by every
// binary that has to name a firmware: the secmon for the INSTALLED image
// (firmware_get_vendor), the coreapp for an OFFERED one
// (check_firmware_header). So the string the user confirms before rebooting is
// the string the device reports afterwards.
//
// FIH: assume UNSAFE. Only a POSITIVE custom == secfalse AND a known official
// variant name a trusted vendor; a glitch or an unknown variant stays UNSAFE.
const char* firmware_vendor_str(uint8_t firmware_type) {
  if (firmware_type_is_custom(firmware_type) != secfalse) {
    return "UNSAFE, DO NOT USE!";
  }
  switch (firmware_type_variant(firmware_type)) {
    case FW_VARIANT_PRODTEST:
      // Founder-signed but factory-only -- must never be used in the field.
      return "UNSAFE, FACTORY TEST ONLY";
    case FW_VARIANT_BITCOIN_ONLY:
      return "Trezor Bitcoin-only";
    case FW_VARIANT_UNIVERSAL:
      return "Trezor";
    default:
      return "UNSAFE, DO NOT USE!";
  }
}

// --- Interaction-less upgrade consent -------------------------------------
// Lives here rather than in boot_header.c because it is pure layout + hash math
// (no keys, no flash), and because BOTH sides of the consent handshake -- the
// bootloader from a full header, firmware from just the prefix -- must compute
// bit-identical results. That is exactly what this file's cross-validation
// harness exists to prove.

secbool boot_header_prefix_extent(const uint8_t* data, size_t len,
                                  size_t* out_extent) {
  if (data == NULL || out_extent == NULL) {
    return secfalse;
  }
  if (len < sizeof(boot_header_auth_t)) {
    return secfalse;
  }

  const boot_header_auth_t* hdr = (const boot_header_auth_t*)data;
  if (hdr->magic != BOOT_HEADER_MAGIC_TRZQ) {
    return secfalse;
  }
  // Same floor boot_header_auth_get enforces: the authenticated part must cover
  // at least the struct this build knows about.
  if (hdr->auth_size < sizeof(boot_header_auth_t)) {
    return secfalse;
  }
  if (hdr->auth_size > len ||
      len - hdr->auth_size < sizeof(boot_header_merkle_proof_t)) {
    return secfalse;
  }

  // The Merkle proof sits immediately after the authenticated part.
  const boot_header_merkle_proof_t* proof =
      (const boot_header_merkle_proof_t*)(data + hdr->auth_size);
  if (proof->node_count > BOOT_HEADER_MERKLE_PROOF_MAXLEN) {
    return secfalse;
  }
  const size_t proof_size = boot_header_merkle_proof_size(proof);
  if (len - hdr->auth_size < proof_size) {
    return secfalse;
  }

  *out_extent = (size_t)hdr->auth_size + proof_size;
  return sectrue;
}

secbool boot_header_consent_digest(const uint8_t* prefix, size_t prefix_len,
                                   const uint8_t* manifest, size_t manifest_len,
                                   merkle_proof_node_t* out) {
  if (prefix == NULL || prefix_len == 0 || manifest == NULL ||
      manifest_len == 0 || out == NULL) {
    return secfalse;
  }

  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix, prefix_len);
  IMAGE_HASH_UPDATE(&ctx, manifest, manifest_len);
  IMAGE_HASH_FINAL(&ctx, out->bytes);

  return sectrue;
}
