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

// nRF co-processor image verification against the founder model tree, and the
// gate deciding whether an image is safe to push to the nRF. Design:
// docs/core/embed-arch/firmware-merkle-tree.md.
//
// Must match the nRF's MCUboot
// (bootloader/mcuboot/boot/bootutil/src/image_pq.c) and the host signer
// (tools/trezor_core_tools/nrf_tree.py) byte for byte; tests/fw_merkle
// cross-validates all three.

// Secure-mode only on device; the cross-validation harness compiles it too.
#if defined(SECURE_MODE) || defined(BOOT_HEADER_MERKLE_SHIMMED)

// The harness supplies these through its shim header.
#ifndef BOOT_HEADER_MERKLE_SHIMMED
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/boot_header.h>
#include <sec/image_hash_conf.h>
#include <sec/root_keys.h>

#include <ed25519-donna/ed25519.h>
#endif

#include <io/nrf_image.h>

#include "nrf_image_internal.h"

#ifndef BOOT_HEADER_MERKLE_SHIMMED
_Static_assert(NRF_PQ_SLH_SIG_LEN == BOOT_HEADER_PQ_SIGNATURE_LEN,
               "nRF PQ signature record must match the boot header's");
_Static_assert(NRF_PQ_EC_SIG_LEN == BOOT_HEADER_EC_SIGNATURE_LEN,
               "nRF EC signature record must match the boot header's");
#endif

// Fold a slot built around an image hash the caller already holds (the
// update-required hint arrives before the image). Builds the 44-byte TRZP slot
// (coproc_slot_t) and folds leaf = H(0x00 || slot) up to modelRoot.
// model/kind/index come from this build, never from the image or the wire.
secbool nrf_image_verify_hash_in_tree(
    const uint8_t image_hash[SHA256_DIGEST_LENGTH],
    const merkle_proof_node_t* proof, size_t proof_count,
    const merkle_proof_node_t* trusted_model_root) {
  if (image_hash == NULL) {
    return secfalse;
  }
  coproc_slot_t slot = {0};
  memcpy(slot.tag, COPROC_SLOT_TAG, sizeof(slot.tag));
  memcpy(slot.model, MODEL_INTERNAL_NAME, sizeof(slot.model));
  slot.kind = (uint8_t)COPROC_KIND_NRF;
  slot.index = 0;
  memcpy(slot.digest, image_hash, sizeof(slot.digest));
  return boot_header_verify_slot((const uint8_t*)&slot, sizeof(slot), proof,
                                 proof_count, trusted_model_root);
}

// Defined below with the layout parser.
static uint16_t nrf_image_find_prot_tlv(const uint8_t* image, size_t image_len,
                                        uint16_t want, const uint8_t** out_val);

// Model id (TLV 0x00A3) from the protected area only; an unprotected copy is
// attacker-controlled. Defence in depth: the folded slot pins the model too.
bool nrf_image_model_id(const uint8_t* image, size_t image_len,
                        uint8_t out[NRF_IMAGE_MODEL_ID_LEN]) {
  const uint8_t* val = NULL;
  uint16_t len =
      nrf_image_find_prot_tlv(image, image_len, NRF_MCUBOOT_TLV_MODEL_ID, &val);
  if (len != NRF_IMAGE_MODEL_ID_LEN || val == NULL) {
    return false;
  }
  memcpy(out, val, NRF_IMAGE_MODEL_ID_LEN);
  return true;
}

// MCUboot image layout, parsed exactly as the nRF's pq_parse_layout does:
// magic @0, hdr_size @8 (u16), protect_tlv_size @10 (u16), img_size @12 (u32).
// Everything is read from the untrusted image; fields inside the hashed range
// are self-checking through the fold, the unprotected extent is not and is
// bounds-checked at every use (nrf_image_unprot_shape_ok constrains it).
typedef struct {
  uint32_t prot_end;  // end of the image-hash range (hdr + payload + prot TLVs)
  uint32_t unprot_end;  // declared end of the unprotected TLV area
  bool has_unprot;
} nrf_image_layout_t;

static secbool nrf_image_parse(const uint8_t* image, size_t image_len,
                               nrf_image_layout_t* out) {
  if (image == NULL || out == NULL || image_len < NRF_MCUBOOT_HDR_MIN_LEN) {
    return secfalse;
  }
  uint32_t magic = 0;
  uint16_t hdr_size = 0;
  uint16_t prot_tlv_size = 0;
  uint32_t img_size = 0;
  memcpy(&magic, image, sizeof(magic));
  memcpy(&hdr_size, image + 8, sizeof(hdr_size));
  memcpy(&prot_tlv_size, image + 10, sizeof(prot_tlv_size));
  memcpy(&img_size, image + 12, sizeof(img_size));
  if (magic != NRF_MCUBOOT_IMAGE_MAGIC || hdr_size < NRF_MCUBOOT_HDR_MIN_LEN) {
    return secfalse;
  }
  // Widths are 16+32+16 bits summed into 64, so this cannot overflow.
  uint64_t prot_end =
      (uint64_t)hdr_size + (uint64_t)img_size + (uint64_t)prot_tlv_size;
  if (prot_end == 0 || prot_end > (uint64_t)image_len) {
    return secfalse;
  }
  out->prot_end = (uint32_t)prot_end;
  out->unprot_end = (uint32_t)prot_end;
  out->has_unprot = false;

  if (prot_end + 4u > (uint64_t)image_len) {
    return sectrue;  // no room for an unprotected area
  }
  uint16_t info_magic = 0;
  uint16_t info_len = 0;
  memcpy(&info_magic, image + (size_t)prot_end, sizeof(info_magic));
  memcpy(&info_len, image + (size_t)prot_end + 2, sizeof(info_len));
  if (info_magic != NRF_MCUBOOT_TLV_INFO_MAGIC) {
    return sectrue;  // no unprotected area
  }
  uint64_t end = prot_end + (uint64_t)info_len;
  if (end > (uint64_t)image_len) {
    // Reject, do not clamp: MCUboot walks the area with the declared length
    // unclamped and refuses such an image, so a clamping STM would mispredict.
    return secfalse;
  }
  out->unprot_end = (uint32_t)end;
  out->has_unprot = true;
  return sectrue;
}

// MCUboot's own image hash (TLV 0x10): SHA-256 over header + payload +
// protected TLVs. The digest field of the nRF's model-tree slot; it does not
// cover the unprotected TLV area.
secbool nrf_image_hash(const uint8_t* image, size_t image_len,
                       uint8_t out[SHA256_DIGEST_LENGTH]) {
  nrf_image_layout_t layout;
  if (nrf_image_parse(image, image_len, &layout) != sectrue) {
    return secfalse;
  }
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, image, layout.prot_end);
  IMAGE_HASH_FINAL(&ctx, out);
  return sectrue;
}

// Fold the image's leaf up through `proof` to the trusted modelRoot. There is
// no separate nRF signature: the boot-header signature over modelRoot covers
// it.
secbool nrf_image_verify_in_tree(
    const uint8_t* image, size_t image_len, const merkle_proof_node_t* proof,
    size_t proof_count, const merkle_proof_node_t* trusted_model_root) {
  uint8_t image_hash[SHA256_DIGEST_LENGTH];
  if (nrf_image_hash(image, image_len, image_hash) != sectrue) {
    return secfalse;
  }
  return nrf_image_verify_hash_in_tree(image_hash, proof, proof_count,
                                       trusted_model_root);
}

// The push gate. The leaf stops at the protected TLVs, so the fold says nothing
// about the unprotected area where both schemes keep their signature records;
// the nRF has no dual slot, so an image its own MCUboot refuses bricks it. Each
// image is gated against its own scheme: (1) fold with the proof from the
// image's TLV, (2) founder records byte-equal to the boot header's (or the
// classic Ed25519 records verified with the model's nRF key pool), (3) the
// unprotected area is exactly the expected records, (4) TLV 0x10 matches.

// True iff the image carries PQ founder material (i.e. is PQ-native).
static secbool nrf_image_pq_material_present(const uint8_t* image,
                                             size_t image_len) {
  nrf_image_layout_t layout;
  if (nrf_image_parse(image, image_len, &layout) != sectrue ||
      !layout.has_unprot) {
    return secfalse;
  }
  // Walk rather than trust a length; the unprotected extent is unsigned.
  uint64_t p = (uint64_t)layout.prot_end + 4u;
  while (p + 4u <= (uint64_t)layout.unprot_end) {
    uint16_t type = 0;
    uint16_t len = 0;
    memcpy(&type, image + (size_t)p, sizeof(type));
    memcpy(&len, image + (size_t)p + 2, sizeof(len));
    if (p + 4u + (uint64_t)len > (uint64_t)layout.unprot_end) {
      return secfalse;  // malformed record: not a well-formed PQ image
    }
    if (type >= NRF_PQ_TLV_FIRST && type <= NRF_PQ_TLV_LAST) {
      return sectrue;
    }
    p += 4u + (uint64_t)len;
  }
  return secfalse;
}

// Also compiled in the host harness, which cross-checks the mapping.
#if defined(MODEL_NRF_LEGACY_KEYS_PRODUCTION) || \
    defined(BOOT_HEADER_MERKLE_SHIMMED)
// Which two pool keys a classic sigmask names. A bespoke 2-of-3 map mirroring
// the nRF's image_validate.c, not the founder "i-th set bit" rule; must match.
secbool nrf_image_legacy_sig_slots(uint8_t sigmask, uint32_t key_count,
                                   int out_idx[2]) {
  if (out_idx == NULL || key_count == 0) {
    return secfalse;
  }
  // Exactly two keys named, none outside the pool -- the nRF's own checks.
  if (__builtin_popcount((unsigned)sigmask) != 2) {
    return secfalse;
  }
  if ((sigmask & (uint8_t)~((1u << key_count) - 1u)) != 0) {
    return secfalse;
  }
  int i0 = (sigmask & (1u << 0)) ? 0 : 1;
  int i1 = (sigmask & (1u << 2)) ? 2 : 1;
  if (i0 == i1) {  // the nRF rejects this too
    return secfalse;
  }
  if ((uint32_t)i0 >= key_count || (uint32_t)i1 >= key_count) {
    return secfalse;
  }
  out_idx[0] = i0;
  out_idx[1] = i1;
  return sectrue;
}
#endif  // legacy sigmask mapping needed

// Classic acceptance needs the model's key pool and an Ed25519 implementation;
// the harness opts in with NRF_LEGACY_ED25519_HOST.
#if defined(MODEL_NRF_LEGACY_KEYS_PRODUCTION) && \
    (!defined(BOOT_HEADER_MERKLE_SHIMMED) || defined(NRF_LEGACY_ED25519_HOST))
#define NRF_LEGACY_PREDICATE_AVAILABLE 1
#endif

#ifdef NRF_LEGACY_PREDICATE_AVAILABLE
// This model's nRF Ed25519 key pool (MODEL_NRF_LEGACY_KEYS_* in model_<M>.h);
// absent for a model whose nRF is PQ-native.
static const uint8_t* const NRF_LEGACY_KEYS[] = {
#if BOOTLOADER_DEVEL
    MODEL_NRF_LEGACY_KEYS_DEVEL
#else
    MODEL_NRF_LEGACY_KEYS_PRODUCTION
#endif
};
#define NRF_LEGACY_KEY_N (sizeof(NRF_LEGACY_KEYS) / sizeof(NRF_LEGACY_KEYS[0]))
#endif  // NRF_LEGACY_PREDICATE_AVAILABLE

// Locate one TLV in the protected area only: an unprotected copy is outside
// the image hash, hence attacker-controlled.
static uint16_t nrf_image_find_prot_tlv(const uint8_t* image, size_t image_len,
                                        uint16_t want,
                                        const uint8_t** out_val) {
  nrf_image_layout_t layout;
  if (out_val == NULL ||
      nrf_image_parse(image, image_len, &layout) != sectrue) {
    return 0;
  }
  uint16_t hdr_size = 0;
  uint16_t prot_size = 0;
  uint32_t img_size = 0;
  memcpy(&hdr_size, image + 8, sizeof(hdr_size));
  memcpy(&prot_size, image + 10, sizeof(prot_size));
  memcpy(&img_size, image + 12, sizeof(img_size));
  if (prot_size == 0) {
    return 0;
  }
  uint64_t start = (uint64_t)hdr_size + (uint64_t)img_size;
  uint64_t end = start + (uint64_t)prot_size;
  if (end > (uint64_t)image_len) {
    return 0;
  }
  // Validate the protected TLV-info header; the fold may not have run yet.
  uint16_t prot_magic = 0;
  memcpy(&prot_magic, image + (size_t)start, sizeof(prot_magic));
  if (prot_magic != NRF_MCUBOOT_TLV_PROT_INFO_MAGIC) {
    return 0;
  }
  uint64_t p = start + 4u;  // past the protected TLV-info header
  while (p + 4u <= end) {
    uint16_t type = 0;
    uint16_t len = 0;
    memcpy(&type, image + (size_t)p, sizeof(type));
    memcpy(&len, image + (size_t)p + 2, sizeof(len));
    if (p + 4u + (uint64_t)len > end) {
      return 0;  // malformed record
    }
    if (type == want) {
      *out_val = image + (size_t)p + 4u;
      return len;
    }
    p += 4u + (uint64_t)len;
  }
  return 0;
}

// Classic image TLVs: Ed25519 signatures (unprotected), sigmask (protected).
#define NRF_LEGACY_TLV_SIG_0 0x00A0U
#define NRF_LEGACY_TLV_SIG_1 0x00A1U
#define NRF_LEGACY_TLV_SIGMASK 0x00A2U
#define NRF_LEGACY_SIG_LEN 64U

// Locate one TLV in the unprotected area only; 0 if absent or malformed.
uint16_t nrf_image_find_unprot_tlv(const uint8_t* image, size_t image_len,
                                   uint16_t want, const uint8_t** out_val) {
  const uint32_t image_magic = 0x96F3B83DU;
  const uint16_t tlv_info_magic = 0x6907U;
  if (image == NULL || image_len < 16) {
    return 0;
  }
  uint32_t magic = 0;
  uint16_t hdr_size = 0;
  uint16_t prot_size = 0;
  uint32_t img_size = 0;
  memcpy(&magic, image, sizeof(magic));
  memcpy(&hdr_size, image + 8, sizeof(hdr_size));
  memcpy(&prot_size, image + 10, sizeof(prot_size));
  memcpy(&img_size, image + 12, sizeof(img_size));
  if (magic != image_magic) {
    return 0;
  }
  uint64_t unprot_off =
      (uint64_t)hdr_size + (uint64_t)img_size + (uint64_t)prot_size;
  if (unprot_off + 4u > (uint64_t)image_len) {
    return 0;
  }
  uint16_t info_magic = 0;
  uint16_t info_len = 0;
  memcpy(&info_magic, image + (size_t)unprot_off, sizeof(info_magic));
  memcpy(&info_len, image + (size_t)unprot_off + 2, sizeof(info_len));
  if (info_magic != tlv_info_magic) {
    return 0;
  }
  uint64_t end = unprot_off + (uint64_t)info_len;
  if (end > (uint64_t)image_len) {
    end = (uint64_t)image_len;
  }
  uint64_t p = unprot_off + 4u;
  while (p + 4u <= end) {
    uint16_t type = 0;
    uint16_t len = 0;
    memcpy(&type, image + (size_t)p, sizeof(type));
    memcpy(&len, image + (size_t)p + 2, sizeof(len));
    if (p + 4u + (uint64_t)len > end) {
      return 0;  // malformed record
    }
    if (type == want) {
      *out_val = image + (size_t)p + 4u;
      return len;
    }
    p += 4u + (uint64_t)len;
  }
  return 0;
}

// One expected unprotected record; len 0 means a non-empty multiple of `unit`,
// at most `max_units` of them (only the Merkle proof is variable).
typedef struct {
  uint16_t type;
  uint16_t len;
  uint16_t unit;
  uint16_t max_units;
} nrf_image_unprot_spec_t;

// The unprotected area must be exactly the expected records: each once, at its
// length, no rogue types and no slack. Nothing else constrains the area, and
// a rogue record passes the fold yet fails MCUboot's allow-list
// (pq_region_shape_ok in image_pq.c). Tables are per scheme.
static secbool nrf_image_unprot_shape_ok(
    const uint8_t* image, size_t image_len,
    const nrf_image_unprot_spec_t* expected, uint32_t n_expected) {
  const uint32_t all_seen =
      (n_expected >= 32u) ? 0xFFFFFFFFu : ((1u << n_expected) - 1u);

  nrf_image_layout_t layout;
  if (nrf_image_parse(image, image_len, &layout) != sectrue ||
      !layout.has_unprot) {
    return secfalse;
  }

  uint32_t seen = 0;
  uint64_t p = (uint64_t)layout.prot_end + 4u;  // past the TLV-info header
  const uint64_t tlv_end = (uint64_t)layout.unprot_end;
  while (p < tlv_end) {
    if (p + 4u > tlv_end) {
      return secfalse;  // trailing stub too small to be a record
    }
    uint16_t type = 0;
    uint16_t len = 0;
    memcpy(&type, image + (size_t)p, sizeof(type));
    memcpy(&len, image + (size_t)p + 2, sizeof(len));
    if (p + 4u + (uint64_t)len > tlv_end) {
      return secfalse;  // record overruns the area
    }

    // Expected type, not a repeat, right length.
    bool matched = false;
    for (uint32_t i = 0; i < n_expected; i++) {
      if (type != expected[i].type) {
        continue;
      }
      if (seen & (1u << i)) {
        return secfalse;  // duplicate
      }
      if (expected[i].len != 0) {
        if (len != expected[i].len) {
          return secfalse;
        }
      } else {
        // Variable: whole units, non-empty, bounded.
        if (len == 0 || expected[i].unit == 0 ||
            (len % expected[i].unit) != 0 ||
            (len / expected[i].unit) > expected[i].max_units) {
          return secfalse;
        }
      }
      seen |= (1u << i);
      matched = true;
      break;
    }
    if (!matched) {
      return secfalse;  // rogue or unexpected record
    }
    p += 4u + (uint64_t)len;
  }

  // All present; the loop leaves no slack before tlv_end.
  return (seen == all_seen) ? sectrue : secfalse;
}

// Founder (PQ-native) images: the image hash plus the founder records.
static secbool nrf_image_pq_shape_ok(const uint8_t* image, size_t image_len) {
  static const nrf_image_unprot_spec_t expected[] = {
      {NRF_MCUBOOT_TLV_IMAGE_HASH, SHA256_DIGEST_LENGTH, 0, 0},
      {NRF_PQ_TLV_SLH_SIG_0, NRF_PQ_SLH_SIG_LEN, 0, 0},
      {NRF_PQ_TLV_SLH_SIG_1, NRF_PQ_SLH_SIG_LEN, 0, 0},
      {NRF_PQ_TLV_EC_SIG_0, NRF_PQ_EC_SIG_LEN, 0, 0},
      {NRF_PQ_TLV_EC_SIG_1, NRF_PQ_EC_SIG_LEN, 0, 0},
      {NRF_PQ_TLV_MERKLE_PROOF, 0, (uint16_t)sizeof(merkle_proof_node_t),
       MODEL_TREE_MAX_PROOF_NODES},
  };
  return nrf_image_unprot_shape_ok(
      image, image_len, expected,
      (uint32_t)(sizeof(expected) / sizeof(expected[0])));
}

// Classic images: the image hash plus the two Ed25519 records (the sigmask is
// protected). Stricter than the nRF's own allow-list, which is the safe
// direction; matches what imgtool + insert_signatures.py emit.
static secbool nrf_image_legacy_shape_ok(const uint8_t* image,
                                         size_t image_len) {
  static const nrf_image_unprot_spec_t expected[] = {
      {NRF_MCUBOOT_TLV_IMAGE_HASH, SHA256_DIGEST_LENGTH, 0, 0},
      {NRF_LEGACY_TLV_SIG_0, NRF_LEGACY_SIG_LEN, 0, 0},
      {NRF_LEGACY_TLV_SIG_1, NRF_LEGACY_SIG_LEN, 0, 0},
  };
  return nrf_image_unprot_shape_ok(
      image, image_len, expected,
      (uint32_t)(sizeof(expected) / sizeof(expected[0])));
}

#ifdef NRF_LEGACY_PREDICATE_AVAILABLE
// Predict the nRF's verdict on a classic image: verify both Ed25519 records
// over the image hash with the keys the protected sigmask names.
static secbool nrf_image_legacy_accept_ok(const uint8_t* image,
                                          size_t image_len) {
  uint8_t image_hash[SHA256_DIGEST_LENGTH];
  if (nrf_image_hash(image, image_len, image_hash) != sectrue) {
    return secfalse;
  }

  // Sigmask from the protected area only.
  const uint8_t* mask_val = NULL;
  if (nrf_image_find_prot_tlv(image, image_len, NRF_LEGACY_TLV_SIGMASK,
                              &mask_val) != 1 ||
      mask_val == NULL) {
    return secfalse;
  }
  int idx[2] = {-1, -1};
  if (nrf_image_legacy_sig_slots(*mask_val, NRF_LEGACY_KEY_N, idx) != sectrue) {
    return secfalse;
  }

  const uint16_t sig_tlv[2] = {NRF_LEGACY_TLV_SIG_0, NRF_LEGACY_TLV_SIG_1};
  for (int i = 0; i < 2; i++) {
    const uint8_t* sig = NULL;
    if (nrf_image_find_unprot_tlv(image, image_len, sig_tlv[i], &sig) !=
            NRF_LEGACY_SIG_LEN ||
        sig == NULL) {
      return secfalse;
    }
    if (ed25519_sign_open(image_hash, sizeof(image_hash),
                          NRF_LEGACY_KEYS[idx[i]], sig) != 0) {
      return secfalse;
    }
  }
  return sectrue;
}
#endif  // NRF_LEGACY_PREDICATE_AVAILABLE

// TLV 0x10 must carry the computed hash. The fold does not reach it, and
// nrf_update_required compares the live chip against it, so a corrupt record
// would push (and brick) on every boot. Both schemes.
static secbool nrf_image_hash_tlv_ok(const uint8_t* image, size_t image_len) {
  uint8_t computed[SHA256_DIGEST_LENGTH];
  if (nrf_image_hash(image, image_len, computed) != sectrue) {
    return secfalse;
  }
  const uint8_t* published = NULL;
  if (nrf_image_find_unprot_tlv(image, image_len, NRF_MCUBOOT_TLV_IMAGE_HASH,
                                &published) != SHA256_DIGEST_LENGTH ||
      published == NULL) {
    return secfalse;
  }
  return memcmp(published, computed, SHA256_DIGEST_LENGTH) == 0 ? sectrue
                                                                : secfalse;
}

secbool nrf_image_verify_for_push(const uint8_t* image, size_t image_len,
                                  const merkle_proof_node_t* trusted_model_root,
                                  const uint8_t* expected_slh_sig0,
                                  const uint8_t* expected_slh_sig1,
                                  const uint8_t* expected_ec_sig0,
                                  const uint8_t* expected_ec_sig1) {
  if (image == NULL || trusted_model_root == NULL ||
      expected_slh_sig0 == NULL || expected_slh_sig1 == NULL ||
      expected_ec_sig0 == NULL || expected_ec_sig1 == NULL) {
    return secfalse;
  }
  // Classic image: gate it against its own scheme.
  if (nrf_image_pq_material_present(image, image_len) != sectrue) {
    // (3) shape first: the only check that sees a rogue unprotected record.
    if (nrf_image_legacy_shape_ok(image, image_len) != sectrue) {
      return secfalse;
    }
    if (nrf_image_hash_tlv_ok(image, image_len) != sectrue) {
      return secfalse;
    }
#ifdef NRF_LEGACY_PREDICATE_AVAILABLE
    return nrf_image_legacy_accept_ok(image, image_len);
#elif defined(BOOT_HEADER_MERKLE_SHIMMED)
    // Host build without Ed25519: the shape layer is all that can be checked.
    return sectrue;
#else
    // PQ-native nRF: no classic key pool, so refuse rather than guess.
    return secfalse;
#endif
  }

  // (3) shape first: cheapest, and it bounds what the reads below can see.
  if (nrf_image_pq_shape_ok(image, image_len) != sectrue) {
    return secfalse;
  }
  if (nrf_image_hash_tlv_ok(image, image_len) != sectrue) {
    return secfalse;
  }

  // (1) fold with the co-path from the IMAGE, which is the copy MCUboot uses.
  const uint8_t* proof = NULL;
  uint16_t proof_len = nrf_image_find_unprot_tlv(
      image, image_len, NRF_PQ_TLV_MERKLE_PROOF, &proof);
  if (proof_len == 0 || (proof_len % sizeof(merkle_proof_node_t)) != 0) {
    return secfalse;
  }
  if (nrf_image_verify_in_tree(image, image_len,
                               (const merkle_proof_node_t*)(const void*)proof,
                               proof_len / sizeof(merkle_proof_node_t),
                               trusted_model_root) != sectrue) {
    return secfalse;
  }

  // The security counter (IMAGE_TLV_SEC_CNT) is a protected TLV, inside the
  // leaf, so the fold above already covers it; the signature records are
  // unprotected and are not.
  // (2) the signature records must be the ones this boot header carries.
  const struct {
    uint16_t type;
    const uint8_t* expected;
    uint16_t len;
  } sigs[] = {
      {NRF_PQ_TLV_SLH_SIG_0, expected_slh_sig0, NRF_PQ_SLH_SIG_LEN},
      {NRF_PQ_TLV_SLH_SIG_1, expected_slh_sig1, NRF_PQ_SLH_SIG_LEN},
      {NRF_PQ_TLV_EC_SIG_0, expected_ec_sig0, NRF_PQ_EC_SIG_LEN},
      {NRF_PQ_TLV_EC_SIG_1, expected_ec_sig1, NRF_PQ_EC_SIG_LEN},
  };
  for (uint32_t i = 0; i < sizeof(sigs) / sizeof(sigs[0]); i++) {
    const uint8_t* val = NULL;
    uint16_t len =
        nrf_image_find_unprot_tlv(image, image_len, sigs[i].type, &val);
    if (len != sigs[i].len || val == NULL ||
        memcmp(val, sigs[i].expected, len) != 0) {
      return secfalse;
    }
  }
  return sectrue;
}

#endif  // SECURE_MODE || shimmed
