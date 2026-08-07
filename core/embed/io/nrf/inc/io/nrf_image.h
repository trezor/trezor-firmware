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
 * @brief nRF firmware images: the API for deciding whether to trust one.
 *
 * Everything a caller outside io/nrf needs. The image FORMAT (magics, TLV
 * types, the founder records' allocation) is deliberately not here -- no caller
 * parses these images itself, and the one reader anybody wants is
 * nrf_image_model_id below. Those constants live in nrf_image_internal.h with
 * the implementation and its cross-validation harness.
 */

#pragma once

/* The cross-validation harness supplies these itself (tests/fw_merkle/shims.h),
 * so it can compile this module against host types and a host SHA-256. */
#ifndef BOOT_HEADER_MERKLE_SHIMMED
#include <trezor_types.h>

#include <sec/boot_header.h> /* merkle_proof_node_t, boot_header_verify_slot */
#endif

/** Length of an image's model tag ("T3W1"), the custom TLV 0x00A3 payload. */
#define NRF_IMAGE_MODEL_ID_LEN 4

/**
 * @brief Extract the 4-byte model id (TLV 0x00A3).
 *
 * @param image      the signed MCUboot image
 * @param image_len  its length in bytes
 * @param out        [out] the 4-byte model tag
 * @return true on success
 */
bool nrf_image_model_id(const uint8_t* image, size_t image_len,
                        uint8_t out[NRF_IMAGE_MODEL_ID_LEN]);

/**
 * @brief Is this nRF image committed in the founder MODEL tree?
 *
 * Fold
 * its leaf up through `proof` (the nRF's co-path) and compare to
 * `trusted_model_root` (recomputed by the caller from the boardloader-verified
 * boot header via boot_header_calc_merkle_root). No separate nRF signature --
 * the one boot-header signature over modelRoot covers the nRF leaf.
 *
 * The leaf is MCUboot's own image hash:
 *
 *     leaf = H(0x00 || SHA-256(header || payload || protected TLVs))
 *
 * Uniform for classic and PQ-native images -- no per-model branch, and a
 * malformed image is rejected. That hash stops at the protected TLVs, so the
 * fold says NOTHING about the unprotected TLV area, which is where both schemes
 * keep their signature records. A caller about to OVERWRITE a working nRF must
 * therefore check that area itself: the nRF has no dual slot, so an image its
 * own MCUboot rejects leaves no valid app at all. See
 * nrf_image_verify_for_push.
 *
 * The caller MUST ALSO check the image's model id (MCUboot TLV) against the
 * device, because every model's nRF shares modelRoot so the fold alone does not
 * pin the model.
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
 * @brief Will the nRF accept this image? Gate before OVERWRITING a working one.
 *
 * The fold (nrf_image_verify_in_tree) proves the CODE is founder-authentic, but
 * the leaf is MCUboot's image hash, which stops at the protected TLVs -- so the
 * fold says nothing about the unprotected TLV area where the signature records
 * live. The nRF has no dual slot, so pushing an image its own MCUboot then
 * refuses leaves it with no valid app at all; on a BLE-only device that is the
 * host link, i.e. a remote-triggerable brick. This checks everything MCUboot
 * will check that the fold does not already cover:
 *
 *   1. the fold, using the Merkle proof from the IMAGE's TLV -- the copy
 * MCUboot itself uses, which could otherwise disagree with the OTA wrapper's;
 *   2. the PQ signature records equal the ones this boot header carries, byte
 * for byte (no crypto needed: the founder signature is a function of modelRoot
 *      alone and there is one signing operation per release, so an image
 * folding to THIS modelRoot necessarily carries these bytes; a mismatch means a
 * different ceremony -- fail closed and rebuild the release);
 *   3. the unprotected area is EXACTLY the expected records. A rogue TLV there
 *      leaves leaf, modelRoot and signature intact, so the fold AND a full
 *      signature re-verify both pass -- yet MCUboot rejects it on its
 *      unprotected-TLV whitelist. Only a shape check catches it.
 *
 * The sigmask needs no check: it is a PROTECTED TLV, so it is inside the leaf
 * and already covered by the fold.
 *
 * A CLASSIC (non-PQ-native) image is gated the same way, against ITS scheme:
 * the shape check above with the classic record set, then the two Ed25519
 * records verified with the keys its protected sigmask names, from this model's
 * nRF key pool (MODEL_NRF_LEGACY_KEYS_*). Both layers matter -- a rogue record
 * out there does not change the image hash the signatures cover, so only the
 * shape check sees it, and the co-processor would reject it on its own
 * allow-list after the slot was already erased. A model whose nRF is PQ-native
 * has no such pool and therefore REFUSES classic images rather than accepting
 * them unverified.
 *
 * The four expected signatures come from the boot header that
 * `trusted_model_root` was derived from: the STAGED header during an OTA (phase
 * 1), the INSTALLED one when the boot-time resume driver pushes.
 *
 * @return sectrue iff it is safe to overwrite the nRF with this image.
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
