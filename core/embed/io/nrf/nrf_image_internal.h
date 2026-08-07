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

/**
 * @file
 * @brief nrf_image.c internals, exposed only for cross-validation.
 *
 * INTERNAL to io/nrf -- deliberately not under inc/io/, so it is not part of
 * the module's API.
 *
 * These are the points the cross-validation harness compares against the nRF's
 * own implementation and the host signer's. Reaching them through
 * nrf_image_verify_in_tree would only yield pass/fail; the harness needs the
 * intermediate VALUES, because a leaf or an image hash that differs by one byte
 * from the nRF's is exactly the failure that is otherwise silent.
 *
 * They are declared rather than static purely so that comparison can happen. No
 * production caller outside nrf_image.c uses them.
 */

#pragma once

/* ---- the MCUboot image format ------------------------------------------
 * Here rather than in inc/io/ because nothing outside this module parses
 * these images; the harness needs them to build fixtures and to assert the
 * expected record set. */

/** MCUboot image header magic */
#define NRF_MCUBOOT_IMAGE_MAGIC 0x96F3B83DU
/** TLV-info magic marking the UNPROTECTED area */
#define NRF_MCUBOOT_TLV_INFO_MAGIC 0x6907U
/** TLV-info magic marking the PROTECTED area (inside the image hash) */
#define NRF_MCUBOOT_TLV_PROT_INFO_MAGIC 0x6908U
/** SHA-256 over header + payload + protected TLVs; this value IS the model-tree
 *  slot value for an nRF image */
#define NRF_MCUBOOT_TLV_IMAGE_HASH 0x10U
/** Custom TLV: 4-byte model tag, e.g. "T3W1" (protected) */
#define NRF_MCUBOOT_TLV_MODEL_ID 0x00A3U

/** Smallest header that can be parsed at all: magic..ih_img_size */
#define NRF_MCUBOOT_HDR_MIN_LEN 16U

/**
 * Founder TLV type range (MCUboot vendor range).
 *
 * These records carry the founder signature over modelRoot and the co-path,
 * i.e. material that DEPENDS on the leaf, so they live in the UNPROTECTED TLV
 * area -- outside the MCUboot image hash, which is what the leaf commits to.
 * Their order and position within that area carry no meaning: the leaf boundary
 * is MCUboot's own, not something derived from these types.
 * @{
 */
#define NRF_PQ_TLV_FIRST 0x00A4U     /**< first founder record type */
#define NRF_PQ_TLV_SLH_SIG_0 0x00A4U /**< SLH-DSA over modelRoot, slot 0 */
#define NRF_PQ_TLV_SLH_SIG_1 0x00A5U /**< SLH-DSA over modelRoot, slot 1 */
#define NRF_PQ_TLV_EC_SIG_0 0x00A6U  /**< Ed25519 over H(modelRoot || slh) */
#define NRF_PQ_TLV_EC_SIG_1 0x00A7U  /**< Ed25519, slot 1 */
#define NRF_PQ_TLV_MERKLE_PROOF \
  0x00A8U                       /**< co-path from the leaf to modelRoot */
#define NRF_PQ_TLV_LAST 0x00A8U /**< last founder record type */
/** @} */

/** SLH-DSA signature length in an nRF PQ record. Same value as the boot
 * header's; asserted equal where the real headers are present. */
#define NRF_PQ_SLH_SIG_LEN 7856U
/** Ed25519 signature length in an nRF PQ record. */
#define NRF_PQ_EC_SIG_LEN 64U

/* ---- implementation points the harness cross-validates ----------------- */

/**
 * @brief MCUboot's own image hash: SHA-256 over header + payload + protected
 * TLVs.
 *
 * This value IS the model-tree slot value for an nRF image, i.e. the founder
 * leaf's preimage.
 *
 * @param image      the signed MCUboot image
 * @param image_len  its length in bytes
 * @param out        [out] the 32-byte hash
 * @return sectrue on success; secfalse if the image does not parse
 */
secbool nrf_image_hash(const uint8_t* image, size_t image_len,
                       uint8_t out[SHA256_DIGEST_LENGTH]);

/**
 * @brief Which pool keys a CLASSIC sigmask names.
 *
 * A bespoke 2-of-3 map, NOT the founder scheme's "i-th lowest set bit". Getting
 * it wrong makes the STM mispredict the nRF's verdict, so the harness
 * cross-checks it over all 256 masks.
 *
 * @param sigmask    the image's protected sigmask byte
 * @param key_count  size of this model's nRF key pool
 * @param out_idx    [out] the two key indices, in slot order
 * @return sectrue iff @p sigmask is a legal selection for the pool
 */
secbool nrf_image_legacy_sig_slots(uint8_t sigmask, uint32_t key_count,
                                   int out_idx[2]);

/**
 * @brief Read one TLV from the UNPROTECTED area only.
 *
 * Internal because a caller that wanted a TLV without caring which area it came
 * from would be asking the wrong question: a protected copy must never stand in
 * for an unprotected record.
 *
 * @param image      the signed MCUboot image
 * @param image_len  its length in bytes
 * @param want       TLV type to look for
 * @param out_val    [out] set to the value on success
 * @return the value length, or 0 if absent or malformed
 */
uint16_t nrf_image_find_unprot_tlv(const uint8_t* image, size_t image_len,
                                   uint16_t want, const uint8_t** out_val);
