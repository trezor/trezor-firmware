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

#endif  // SECURE_MODE || shimmed
