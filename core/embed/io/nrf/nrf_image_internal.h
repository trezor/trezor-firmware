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
 * @brief nrf_image.c internals, exposed only for the cross-validation harness
 * (tests/fw_merkle). Not part of the io/nrf API.
 */

#pragma once

/* ---- the MCUboot image format ------------------------------------------ */

/** MCUboot image header magic */
#define NRF_MCUBOOT_IMAGE_MAGIC 0x96F3B83DU
/** TLV-info magic marking the UNPROTECTED area */
#define NRF_MCUBOOT_TLV_INFO_MAGIC 0x6907U
/** TLV-info magic marking the PROTECTED area (inside the image hash) */
#define NRF_MCUBOOT_TLV_PROT_INFO_MAGIC 0x6908U
/** SHA-256 over header + payload + protected TLVs (the slot's digest field) */
#define NRF_MCUBOOT_TLV_IMAGE_HASH 0x10U
/** Custom TLV: 4-byte model tag, e.g. "T3W1" (protected) */
#define NRF_MCUBOOT_TLV_MODEL_ID 0x00A3U

/** Smallest header that can be parsed at all: magic..ih_img_size */
#define NRF_MCUBOOT_HDR_MIN_LEN 16U

/**
 * Founder TLV types (MCUboot vendor range); unprotected, since they depend on
 * the leaf. Order within the area carries no meaning.
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

/** SLH-DSA signature length in an nRF PQ record; asserted == boot header's. */
#define NRF_PQ_SLH_SIG_LEN 7856U
/** Ed25519 signature length in an nRF PQ record. */
#define NRF_PQ_EC_SIG_LEN 64U

/* ---- implementation points the harness cross-validates ----------------- */

/**
 * @brief MCUboot's own image hash: SHA-256 over header + payload + protected
 * TLVs (the digest field of the model-tree slot, not the leaf itself).
 *
 * @param image      the signed MCUboot image
 * @param image_len  its length in bytes
 * @param out        [out] the 32-byte hash
 * @return sectrue on success; secfalse if the image does not parse
 */
secbool nrf_image_hash(const uint8_t* image, size_t image_len,
                       uint8_t out[SHA256_DIGEST_LENGTH]);

/**
 * @brief Which pool keys a classic sigmask names (a bespoke 2-of-3 map, not the
 * founder "i-th set bit" rule; cross-checked over all 256 masks).
 *
 * @param sigmask    the image's protected sigmask byte
 * @param key_count  size of this model's nRF key pool
 * @param out_idx    [out] the two key indices, in slot order
 * @return sectrue iff @p sigmask is a legal selection for the pool
 */
secbool nrf_image_legacy_sig_slots(uint8_t sigmask, uint32_t key_count,
                                   int out_idx[2]);

/**
 * @brief Read one TLV from the unprotected area only.
 *
 * @param image      the signed MCUboot image
 * @param image_len  its length in bytes
 * @param want       TLV type to look for
 * @param out_val    [out] set to the value on success
 * @return the value length, or 0 if absent or malformed
 */
uint16_t nrf_image_find_unprot_tlv(const uint8_t* image, size_t image_len,
                                   uint16_t want, const uint8_t** out_val);
