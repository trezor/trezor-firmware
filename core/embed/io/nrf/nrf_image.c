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
 * Verification of the nRF co-processor's firmware image against the founder
 * MODEL tree, plus the checks that decide whether it is safe to PUSH one.
 *
 * Uses boot_header_merkle.c's fold primitive via boot_header_merkle_internal.h
 * -- a declaration, so there is no longer any include-order or
 * same-translation-unit requirement between the two.
 *
 * Lives in io/nrf, with the co-processor whose images these are. Everything
 * here is about the nRF's image FORMAT and the policy for pushing one; the only
 * part that was ever boot-header business is the fold, which stayed in sec as
 * the generic boot_header_verify_slot(). Nothing in sec/ uses this file, and
 * every caller is the bootloader's OTA path.
 *
 * A model without an nRF does not compile it at all, because io/nrf is gated on
 * the board having one -- previously it sat in sec/image and was merely
 * gc-sectioned away.
 *
 * What is here, in layers:
 *
 *   - MCUboot image layout: nrf_image_parse / nrf_image_hash. The hash
 *     over header + payload + protected TLVs IS the model-tree leaf value.
 *   - the fold: nrf_image_verify_in_tree -- leaf to modelRoot via the co-path.
 *   - the push gate: nrf_image_verify_for_push -- everything the co-processor's
 * own verifier will check that the fold does not, so the STM never erases the
 *     co-processor's only slot for an image it would refuse.
 *   - per-scheme acceptance: founder records byte-compared against the boot
 *     header, or (legacy) the co-processor's own Ed25519 signatures verified
 * with its per-model key pool.
 *
 * Every construction here MUST match the nRF's MCUboot
 * (bootloader/mcuboot/boot/bootutil/src/image_pq.c) and the host signer
 * (tools/trezor_core_tools/nrf_tree.py) BYTE-FOR-BYTE. A mismatch is silent --
 * images simply stop verifying -- so all three are cross-validated against
 * shared vectors in tests/fw_merkle.
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

typedef struct __attribute__((packed)) {
  uint32_t ih_magic;
  uint32_t ih_load_addr;
  uint16_t ih_hdr_size;
  uint16_t ih_protect_tlv_size;
  uint32_t ih_img_size;
  uint32_t ih_flags;
  struct __attribute__((packed)) {
    uint8_t major;
    uint8_t minor;
    uint16_t revision;
    uint32_t build_num;
  } ih_ver;
  uint32_t _pad1;
} nrf_image_header_t;

/**
 * @brief Read one TLV value from the protected or unprotected TLV area.
 *
 * Bounds-checked against @p image_len throughout.
 *
 * @param image      the signed MCUboot image
 * @param image_len  its length in bytes
 * @param tlv_type   TLV type to look for
 * @param protected_area  true to search the protected area, false the
 * unprotected
 * @param out_val    [out] set to the value on success
 * @return the value length, or 0 if absent or malformed
 */
static uint16_t nrf_image_find_tlv(const uint8_t* image, size_t image_len,
                                   uint16_t tlv_type, const uint8_t** out_val) {
  if (image_len < sizeof(nrf_image_header_t)) {
    return 0;
  }
  nrf_image_header_t hdr;
  memcpy(&hdr, image, sizeof(hdr));
  if (hdr.ih_magic != NRF_MCUBOOT_IMAGE_MAGIC) {
    return 0;
  }
  size_t prot_off = (size_t)hdr.ih_hdr_size + hdr.ih_img_size;

  /* Two TLV areas: protected (size ih_protect_tlv_size, incl. its 4-byte info
   * header) then unprotected (its own 4-byte info header + payload). */
  for (int area = 0; area < 2; area++) {
    size_t start, end;
    if (area == 0) {
      if (hdr.ih_protect_tlv_size == 0) {
        continue;
      }
      start = prot_off + 4; /* skip the protected TLV-info header */
      end = prot_off + hdr.ih_protect_tlv_size;
    } else {
      size_t unprot_off = prot_off + hdr.ih_protect_tlv_size;
      if (unprot_off + 4 > image_len) {
        break;
      }
      uint16_t info_magic, info_len;
      memcpy(&info_magic, image + unprot_off, 2);
      memcpy(&info_len, image + unprot_off + 2, 2);
      if (info_magic != NRF_MCUBOOT_TLV_INFO_MAGIC) {
        break;
      }
      start = unprot_off + 4;
      end = unprot_off + info_len;
    }
    if (end > image_len) {
      end = image_len;
    }
    size_t p = start;
    while (p + 4 <= end) {
      uint16_t t, ln;
      memcpy(&t, image + p, 2);
      memcpy(&ln, image + p + 2, 2);
      if (p + 4 + ln > end) {
        break;
      }
      if (t == tlv_type) {
        *out_val = image + p + 4;
        return ln;
      }
      p += 4 + ln;
    }
  }
  return 0;
}

/**
 * @brief Extract the 4-byte model id (TLV 0x00A3).
 *
 * @param image      the signed MCUboot image
 * @param image_len  its length in bytes
 * @param out        [out] the 4-byte model tag
 * @return true on success
 */
bool nrf_image_model_id(const uint8_t* image, size_t image_len,
                        uint8_t out[NRF_IMAGE_MODEL_ID_LEN]) {
  const uint8_t* val = NULL;
  uint16_t len =
      nrf_image_find_tlv(image, image_len, NRF_MCUBOOT_TLV_MODEL_ID, &val);
  if (len != NRF_IMAGE_MODEL_ID_LEN || val == NULL) {
    return false;
  }
  memcpy(out, val, NRF_IMAGE_MODEL_ID_LEN);
  return true;
}

// MCUboot's own image hash IS the founder leaf value:
//
//     image_hash = SHA-256(header || payload || protected TLVs)
//     leaf       = H(0x00 || image_hash)
//
// That range -- everything except the unprotected TLV area -- is exactly the
// boundary the founder material needs: it signs modelRoot, so it cannot lie
// inside its own preimage. MCUboot defines that boundary and publishes the hash
// in TLV 0x10, so this code, the nRF's image_pq.c and the host signer commit to
// the same bytes without having to agree on a private rule, and neither
// verifier hashes the image twice.
//
// Committing a collision-resistant hash commits the bytes, so this is no weaker
// than hashing the range directly. What the leaf does NOT reach is the
// unprotected TLV area -- anything a caller must trust there has to be checked
// explicitly; see nrf_image_verify_for_push.
//
// All fields are read from the very image being verified, i.e. UNTRUSTED. Those
// inside the hashed range are self-checking: a lie changes the hash, hence the
// leaf, hence the fold. The unprotected area's declared extent is NOT covered,
// so it is bounds-checked at every use; the widths (16+32+16 bits summed into
// uint64) cannot overflow.
//
// tests/fw_merkle cross-validates all of this against the host (nrf_tree.py)
// for BOTH image shapes.
//
// The format constants come from nrf_image_internal.h -- ONE definition,
// shared with the model-id reader below and with the harness. This parse is
// deliberately its own: it is the one the LEAF depends on, so it must agree
// with the nRF's pq_parse_layout byte for byte and trust nothing it has not
// bounds-checked. Offsets: magic @0, hdr_size @8 (u16), protect_tlv_size @10
// (u16), img_size @12 (u32).

// Where the protected region ends / the unprotected TLV area lives.
// `unprot_end` is the DECLARED extent, already clamped to image_len -- it comes
// from the unprotected TLV-info header, which no signature covers, so it is
// advisory and must never be used as a bound in its own right (see
// nrf_image_pq_shape_ok, which is what actually constrains this area).
typedef struct {
  uint32_t
      prot_end;  // hdr + payload + protected TLVs: what the image hash covers
  uint32_t unprot_end;  // end of the unprotected TLV area (== prot_end if none)
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
    // REJECT rather than clamp. Clamping is safe against an over-read here, but
    // it is not safe against a BRICK: MCUboot's generic validate walks the area
    // with tlv_end taken straight from it_tlv_tot (bootutil_tlv_iter_begin does
    // not clamp), so it reads past the image into the slot and refuses the
    // image. An STM that clamped would predict "the nRF accepts this", erase
    // the co-processor's only slot, and be wrong. A well-formed image has
    // prot_end + it_tlv_tot == image_len exactly, so nothing legitimate is
    // refused.
    return secfalse;
  }
  out->unprot_end = (uint32_t)end;
  out->has_unprot = true;
  return sectrue;
}

// MCUboot's own image hash: SHA-256 over header + payload + protected TLVs --
// exactly what bootutil_img_hash covers and what TLV 0x10 carries.
//
// This is the nRF's model-tree LEAF VALUE. That range is precisely "everything
// except the unprotected TLV area", which is the boundary the founder material
// needs: it signs modelRoot, so it cannot lie inside its own preimage. MCUboot
// defines that boundary, so committing through this hash replaces a rule
// derived from TLV types with the definition it was derived from. Committing a
// collision-resistant hash commits the bytes, so nothing is weakened.
//
// Being 32 bytes, it is also what lets a device learn WHICH nRF a release
// expects without holding the image: fold H(0x00 || hash) to modelRoot, then
// compare against the live chip's reported hash.
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

// Verify an nRF (co-processor) image is committed in the founder MODEL tree:
// fold its leaf up through `proof` (its co-path) and compare to the trusted
// modelRoot (recomputed by the caller from the boardloader-verified boot header
// via boot_header_calc_merkle_root). This is the STM-side founder gate checked
// at OTA install -- there is NO separate nRF founder signature; the ONE
// boot-header signature over modelRoot covers the nRF leaf.
//
// leaf = H(0x00 || mcuboot_image_hash(image)) -- see nrf_image_hash for
// why the image is committed through its hash rather than a byte range.
//
// The nRF's own MCUboot image signature is verified by the nRF at boot. Because
// every model's nRF hangs under the same modelRoot, the fold alone does NOT pin
// an image to a model -- the caller MUST also check the image's model id
// (MCUboot TLV) against the device (see the OTA workflow). Mirrors the
// firmware-variant fold (firmware_manifest_authentic), one tree level up.
secbool nrf_image_verify_in_tree(
    const uint8_t* image, size_t image_len, const merkle_proof_node_t* proof,
    size_t proof_count, const merkle_proof_node_t* trusted_model_root) {
  uint8_t image_hash[SHA256_DIGEST_LENGTH];
  if (nrf_image_hash(image, image_len, image_hash) != sectrue) {
    return secfalse;
  }
  /* The fold itself is not nRF-specific -- it is boot-header tree math on the
   * boot-header trust anchor, so it stays in sec. All this adds is WHICH bytes
   * become the slot value. */
  return boot_header_verify_slot(image_hash, proof, proof_count,
                                 trusted_model_root);
}

// ---------------------------------------------------------------------------
// The push gate (phase 3)
//
// Scheme-agnostic entry point: nrf_image_verify_for_push dispatches on whether
// the image carries founder material, then applies THAT scheme's shape
// whitelist and acceptance check. Both schemes need one, for the same reason --
// the leaf is the MCUboot image hash, so neither scheme's signature records are
// covered by the fold.
//
// For a PQ-NATIVE image the founder material lives OUTSIDE the leaf (it
// commits to modelRoot, so it cannot sit inside the leaf that produces it). The
// fold therefore proves the CODE is authentic but says nothing about that
// material -- and the nRF has no dual slot, so pushing an image its own MCUboot
// then refuses leaves it with no valid app at all. On a BLE-only device that is
// the host link, i.e. a remote-triggerable brick.
//
// So before OVERWRITING a working nRF, the STM must check everything MCUboot
// will check that the fold does not already cover. Three things, and none of
// them is implied by the others:
//
//   1. fold with the co-path from the IMAGE's TLV -- MCUboot uses that copy,
//   not
//      the one in the OTA wrapper, and two copies could disagree;
//   2. the PQ signature records equal the boot header's, byte for byte;
//   3. the uncovered region is EXACTLY the expected records -- a rogue TLV
//   leaves
//      leaf, modelRoot and signature all intact (so both the fold AND a full
//      signature re-verify pass) yet MCUboot rejects it on its unprotected-TLV
//      whitelist. Only a shape check sees it.
//
// (2) needs no crypto, and is not a shortcut: the founder signature is a
// function of modelRoot ALONE and there is exactly one signing operation per
// release, so an image that folds to THIS modelRoot necessarily carries the
// same signature bytes this boot header carries. A mismatch means a different
// signing ceremony -- reject and let the release be rebuilt. That fails closed,
// whereas re-implementing the hybrid verify here would duplicate
// boot_header_check_signature's logic and its key policy for no gain.
//
// The sigmask needs no check: it is a PROTECTED TLV, hence inside the leaf,
// hence already covered by the fold.
//
// A CLASSIC image takes none of this path -- it carries no founder material at
// all. It is gated instead by nrf_image_legacy_accept_ok, which predicts its
// own MCUboot's verdict directly: the two Ed25519 records verified against this
// model's nRF key pool, with the keys the PROTECTED sigmask names.
// nrf_image_pq_material_present() is the discriminator.

// True iff the image carries PQ founder material (i.e. is PQ-native).
static secbool nrf_image_pq_material_present(const uint8_t* image,
                                             size_t image_len) {
  nrf_image_layout_t layout;
  if (nrf_image_parse(image, image_len, &layout) != sectrue ||
      !layout.has_unprot) {
    return secfalse;
  }
  // Any record in the founder range makes this a PQ-native image. Walking
  // rather than trusting a length: every bound below is checked before it is
  // used, since the unprotected area's extent is not covered by any signature.
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

// Compiled where the legacy predicate lives, plus in the host harness, which
// cross-checks this mapping exhaustively without needing Ed25519. A model whose
// nRF is PQ-native has no classic pool and needs neither.
#if defined(MODEL_NRF_LEGACY_KEYS_PRODUCTION) || \
    defined(BOOT_HEADER_MERKLE_SHIMMED)
// Which two of the nRF's OWN Ed25519 keys a classic image's sigmask names.
//
// PURE, and separated from the crypto on purpose: this mapping is the part that
// is easy to get wrong, and it is exhaustively cross-checked in
// tests/fw_merkle.
//
// It is NOT the founder scheme's "i-th lowest set bit". The nRF's legacy path
// uses a bespoke 2-of-3 map (image_validate.c, !CONFIG_BOOT_PQ_SECURE_BOOT):
//
//     sig0_idx = sigmask & (1 << 0) ? 0 : 1;
//     sig1_idx = sigmask & (1 << 2) ? 2 : 1;
//
// which for the three legal masks yields 0b011 -> {0,1}, 0b101 -> {0,2},
// 0b110 -> {1,2}. Mirrored EXACTLY: a divergence here would make the STM
// predict the wrong verdict -- false rejects at best, and at worst pushing an
// image the nRF refuses, which is the brick this predicate exists to prevent.
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

// Is the classic ACCEPTANCE predicate available in this build? It needs two
// things: the model's Ed25519 key pool, and an Ed25519 implementation to verify
// with. On device both arrive with the model. A host harness opts in by
// defining NRF_LEGACY_ED25519_HOST once it has linked one -- see
// tests/fw_merkle/nrf_crossvalidate.c, which does exactly that so the predicate
// is exercised end-to-end against real signatures rather than stubbed out.
#if defined(MODEL_NRF_LEGACY_KEYS_PRODUCTION) && \
    (!defined(BOOT_HEADER_MERKLE_SHIMMED) || defined(NRF_LEGACY_ED25519_HOST))
#define NRF_LEGACY_PREDICATE_AVAILABLE 1
#endif

#ifdef NRF_LEGACY_PREDICATE_AVAILABLE
/*
 * The nRF co-processor's own Ed25519 key pool for the classic signing scheme,
 * supplied PER MODEL (MODEL_NRF_LEGACY_KEYS_* in models/<M>/model_<M>.h)
 * because these keys belong to that model's nRF -- unlike the founder/root keys
 * in sec/root_keys.h, which are one ceremony covering every model.
 *
 * Absent for a model whose nRF is PQ-native: there is no classic pool to
 * predict against, and a classic image is refused rather than guessed at --
 * which is what leaves NRF_LEGACY_PREDICATE_AVAILABLE undefined there.
 */
static const uint8_t* const NRF_LEGACY_KEYS[] = {
#if BOOTLOADER_DEVEL
    MODEL_NRF_LEGACY_KEYS_DEVEL
#else
    MODEL_NRF_LEGACY_KEYS_PRODUCTION
#endif
};
// Locate one TLV in the PROTECTED area only. The sigmask must come from there:
// an unprotected copy is outside the image hash, hence outside the leaf, hence
// attacker-controlled. Only the legacy predicate needs this, so it lives inside
// the same guard.
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
  // Validate the protected TLV-info header before trusting the 4 bytes we skip.
  // The fold already commits these bytes (the protected area is inside the
  // image hash), but this parser does not get to assume the fold ran first: the
  // legacy path reads the sigmask through here, and the harness calls it on
  // arbitrary fixtures. Mirrors the check nrf_image_parse does for the
  // unprotected area.
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

#define NRF_LEGACY_KEY_N (sizeof(NRF_LEGACY_KEYS) / sizeof(NRF_LEGACY_KEYS[0]))
#endif  // NRF_LEGACY_PREDICATE_AVAILABLE

// The classic image's own TLVs: two Ed25519 signatures in the UNPROTECTED area,
// and the sigmask naming which keys signed in the PROTECTED one. Format
// constants, so unconditional -- the shape check below needs them on every
// model, including those with no classic key pool to verify against.
#define NRF_LEGACY_TLV_SIG_0 0x00A0U
#define NRF_LEGACY_TLV_SIG_1 0x00A1U
#define NRF_LEGACY_TLV_SIGMASK 0x00A2U
#define NRF_LEGACY_SIG_LEN 64U

// Locate one TLV in the UNPROTECTED area only (the PQ records live there; a
// protected copy of the same type must never be substituted for them). Returns
// 0 if absent/malformed, else the value length with *out_val set.
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

// One expected record in the unprotected TLV area.
//
// `len` is the exact value length; 0 means variable, in which case the length
// must be a non-zero multiple of `unit` and at most `max_units` of them. Only
// the founder Merkle proof is variable -- every classic record is fixed-size.
typedef struct {
  uint16_t type;
  uint16_t len;
  uint16_t unit;
  uint16_t max_units;
} nrf_image_unprot_spec_t;

// The unprotected TLV area must consist of EXACTLY the expected records: each
// one present once, at its declared length, with no rogue types, no duplicates
// and no slack before `tlv_end`.
//
// This is the only structural constraint on the area, because the leaf --
// MCUboot's image hash -- stops at the protected TLVs and no signature covers
// the declared extent either. Exactness is what does the work: loosening it to
// "contains at least" would leave the length unconstrained, and a rogue record
// there keeps leaf, modelRoot and signature all intact, so the fold AND a full
// signature re-verify both pass while the co-processor's own allow-list rejects
// the image. Mirrors pq_region_shape_ok() in the nRF's MCUboot
// (boot/bootutil/src/image_pq.c), which is what actually rejects.
//
// Per SCHEME, not per model: what belongs in the area is a property of how the
// image was signed, and each scheme has its own table below.
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

    // Must be one of the expected records, and not a repeat. Anything else -- a
    // rogue type, a duplicate, a wrong length -- fails.
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

  // Every expected record present, and the last ended exactly at tlv_end (the
  // loop condition guarantees the latter -- no slack tolerated).
  return (seen == all_seen) ? sectrue : secfalse;
}

// FOUNDER (PQ-native) images: the image hash plus the founder material. This is
// check (3) of the push gate. Every record's value is independently pinned once
// the shape holds: TLV 0x10 by MCUboot comparing it against the hash it
// computed (and that hash is what the fold commits), the four signature records
// by the push gate's byte-comparison against the boot header, and the proof by
// the fold reaching modelRoot.
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

// CLASSIC images: the image hash plus the two Ed25519 signature records, whose
// values nrf_image_legacy_accept_ok then verifies. The sigmask is NOT here --
// it is a protected TLV, hence inside the image hash and already covered by the
// fold.
//
// The set is EXACT, and deliberately stricter than the co-processor's own
// allowed_unprot_tlvs (which also tolerates KEYHASH, PUBKEY, other digests and
// the encryption TLVs). Confirmed against what the signer actually emits:
// imgtool is invoked WITHOUT a key, so it contributes only the hash TLV, and
// insert_signatures.py appends exactly 0x00A0 and 0x00A1 -- nothing else. Being
// stricter can only refuse an image the nRF would have taken, never accept one
// it would refuse, and refusing is the safe direction here: the alternative is
// erasing the co-processor's only slot for an image it then rejects.
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
// Will the nRF's own MCUboot accept this CLASSIC image? Answered by doing what
// it will do: verify the two Ed25519 records over the image hash, with the keys
// the protected sigmask names.
//
// Needed because the leaf is the image hash, which stops at the protected TLVs
// -- so the fold says nothing about the signature records in the unprotected
// area. A host could swap them while leaving header, payload and protected TLVs
// intact: the fold would pass, the STM would erase the nRF's only slot, and the
// nRF would then refuse the image. Predicting acceptance directly is strictly
// stronger than what the old whole-image leaf gave us ("these bytes were
// signed" -> "the nRF will accept these bytes").
//
// The signatures cover exactly the image hash, which is already computed here
// as the leaf value, so this costs two Ed25519 verifications and nothing else.
static secbool nrf_image_legacy_accept_ok(const uint8_t* image,
                                          size_t image_len) {
  uint8_t image_hash[SHA256_DIGEST_LENGTH];
  if (nrf_image_hash(image, image_len, image_hash) != sectrue) {
    return secfalse;
  }

  // Sigmask from the PROTECTED area only: it is inside the image hash, hence
  // inside the leaf, hence covered by the fold. An unprotected copy would be
  // attacker-controlled.
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
  // Classic image: the fold covers only up to the protected TLVs, so it does
  // NOT prove the unprotected signature records are intact. Predict the nRF's
  // verdict instead -- the same two layers the founder path gets, against ITS
  // scheme.
  if (nrf_image_pq_material_present(image, image_len) != sectrue) {
    // (3) shape first, exactly as below: cheapest, needs no crypto, and it is
    // the only thing that catches a rogue record out here. Without it the
    // signatures would verify (they cover the image hash, which a rogue TLV
    // does not change), the fold would pass, the STM would erase the nRF's only
    // slot -- and the nRF would then refuse the image on its own
    // unprotected-TLV allow-list.
    if (nrf_image_legacy_shape_ok(image, image_len) != sectrue) {
      return secfalse;
    }
#ifdef NRF_LEGACY_PREDICATE_AVAILABLE
    return nrf_image_legacy_accept_ok(image, image_len);
#elif defined(BOOT_HEADER_MERKLE_SHIMMED)
    // A host build without an Ed25519 implementation: the shape layer above is
    // all this scheme can check here.
    return sectrue;
#else
    // This model's nRF is PQ-native, so there is no classic key pool to predict
    // against. Refuse rather than guess: a classic image here is either the
    // wrong artifact or an attempt to sidestep founder verification, and
    // pushing it would erase the nRF's only slot for something we cannot vouch
    // for.
    return secfalse;
#endif
  }

  // (3) shape first: cheapest, and it bounds what the reads below can see.
  if (nrf_image_pq_shape_ok(image, image_len) != sectrue) {
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

  // NOT checked here, deliberately: the nRF image's security counter
  // (IMAGE_TLV_SEC_CNT, the release's monotonic_version). It is a PROTECTED
  // TLV, so it lies INSIDE the leaf -- and the fold above already proved that
  // leaf reaches this boot header's modelRoot. An image that folds is therefore
  // the one signed alongside THIS bootloader, carrying the counter the signer
  // stamped from THIS header; a tampered counter simply fails the fold. Nor can
  // the nRF refuse the push on rollback grounds: that needs the nRF's floor
  // above the pushed counter, which needs the bootloader downgraded first,
  // which check_bootloader_min_version already refuses.
  //
  // That is exactly why the signature records below DO need checking: they are
  // UNPROTECTED, outside the leaf, so the fold says nothing about them. If the
  // counter ever moves out of the protected area, it joins them.
  //
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
