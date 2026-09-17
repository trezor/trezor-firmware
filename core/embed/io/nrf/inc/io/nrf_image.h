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
 * @brief nRF co-processor image verification against the founder model tree.
 * Format constants live in nrf_image_internal.h; design in
 * docs/core/embed-arch/firmware-merkle-tree.md.
 */

#pragma once

/* The cross-validation harness supplies these (tests/fw_merkle/shims.h). */
#ifndef BOOT_HEADER_MERKLE_SHIMMED
#include <trezor_types.h>

#include <sec/boot_header.h> /* merkle_proof_node_t, boot_header_verify_slot */
#endif

/** Length of an image's model tag ("T3W1"), the custom TLV 0x00A3 payload. */
#define NRF_IMAGE_MODEL_ID_LEN 4

/**
 * @brief Extract the 4-byte model id (TLV 0x00A3) from the protected TLV area.
 *
 * @param image      the signed MCUboot image
 * @param image_len  its length in bytes
 * @param out        [out] the 4-byte model tag
 * @return true on success
 */
bool nrf_image_model_id(const uint8_t* image, size_t image_len,
                        uint8_t out[NRF_IMAGE_MODEL_ID_LEN]);

/**
 * @brief Fold a slot built around a caller-held image hash (the update-required
 * hint); a hint that does not fold rejects the upload.
 */
secbool nrf_image_verify_hash_in_tree(
    const uint8_t image_hash[SHA256_DIGEST_LENGTH],
    const merkle_proof_node_t* proof, size_t proof_count,
    const merkle_proof_node_t* trusted_model_root);

/**
 * @brief Is this nRF image committed in the founder model tree?
 *
 * slot = "TRZP" | model | kind | index | reserved(2) | image_hash (44 bytes),
 * leaf = H(0x00 || slot); model/kind/index come from this build, never the
 * image. The fold does not cover the unprotected TLV area, so before
 * overwriting a working nRF use nrf_image_verify_for_push.
 *
 * @param image        the signed MCUboot image
 * @param image_len    its length in bytes
 * @param proof        the nRF's co-path, leaf -> modelRoot
 * @param proof_count  co-path length (bounded by MODEL_TREE_MAX_PROOF_NODES)
 * @param trusted_model_root modelRoot recomputed from the verified boot header
 * @return sectrue iff the fold reaches @p trusted_model_root
 */
secbool nrf_image_verify_in_tree(const uint8_t* image, size_t image_len,
                                 const merkle_proof_node_t* proof,
                                 size_t proof_count,
                                 const merkle_proof_node_t* trusted_model_root);

/**
 * @brief Will the nRF's own MCUboot accept this image? Gate before overwriting
 * a working nRF, which has no dual slot.
 *
 * Each image is gated against its own scheme: PQ-native by shape, TLV 0x10,
 * the fold with the image's own proof and byte-equal founder records; classic
 * by shape and the two Ed25519 records under the protected sigmask's keys.
 * A PQ-native model refuses classic images.
 *
 * @param image        the signed MCUboot image about to be pushed
 * @param image_len    its length in bytes
 * @param trusted_model_root modelRoot recomputed from the verified boot header
 * @param expected_slh_sig0  founder SLH-DSA signature slot 0, from that header
 * @param expected_slh_sig1  founder SLH-DSA signature slot 1
 * @param expected_ec_sig0   founder Ed25519 signature slot 0
 * @param expected_ec_sig1   founder Ed25519 signature slot 1
 * @return sectrue iff the co-processor's own verifier would accept the image
 */
secbool nrf_image_verify_for_push(const uint8_t* image, size_t image_len,
                                  const merkle_proof_node_t* trusted_model_root,
                                  const uint8_t* expected_slh_sig0,
                                  const uint8_t* expected_slh_sig1,
                                  const uint8_t* expected_ec_sig0,
                                  const uint8_t* expected_ec_sig1);
