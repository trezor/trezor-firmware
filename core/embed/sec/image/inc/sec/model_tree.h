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

#include <trezor_types.h>

#include <sec/merkle.h>

/** Upper bound on a model-tree co-path (MODEL_TREE_DEPTH is 4 today). Bounds
 *  an UNTRUSTED proof_count before size arithmetic; the single definition. */
#define MODEL_TREE_MAX_PROOF_NODES 32U

/**
 * Co-processor slot value: what a co-processor's model-tree leaf commits to.
 * The fold sorts pairs (no position), so the role lives in the leaf value.
 * `kind`/`index` come from the verifier's build config, never from the image
 * or the wire; `digest` must exclude the region holding the founder material.
 */
#define COPROC_SLOT_TAG "TRZP"
#define COPROC_SLOT_MODEL_LEN 4
/* SHA-256 width; literal because this header depends only on trezor_types.h */
#define COPROC_SLOT_DIGEST_LEN 32

/** Co-processor kind (a field, not part of the tag). */
typedef enum {
  COPROC_KIND_NRF = 1,
} coproc_kind_t;

typedef struct __attribute__((packed)) {
  uint8_t tag[4];                         /**< COPROC_SLOT_TAG */
  uint8_t model[COPROC_SLOT_MODEL_LEN];   /**< MODEL_INTERNAL_NAME, 4 ASCII */
  uint8_t kind;                           /**< coproc_kind_t (build config) */
  uint8_t index;                          /**< instance of that kind (build
                                               config), 0 today */
  uint8_t reserved[2];                    /**< zero */
  uint8_t digest[COPROC_SLOT_DIGEST_LEN]; /**< per-kind image digest */
} coproc_slot_t;

_Static_assert(sizeof(coproc_slot_t) == 44,
               "coproc_slot_t must be 44 bytes -- it is a leaf preimage shared "
               "with the signer and the nRF's MCUboot");

/**
 * @brief Fold a MODEL-tree slot value (e.g. a coproc_slot_t) up to
 *        `trusted_model_root`. Proves commitment only; identity must be
 *        inside the value.
 *
 * @param slot_value   the committed value (coproc_slot_t for a co-processor)
 * @param slot_len     its length in bytes
 * @param proof        co-path from the slot up to modelRoot
 * @param proof_count  number of co-path nodes (<= MODEL_TREE_MAX_PROOF_NODES)
 * @param trusted_model_root modelRoot recomputed from the verified boot header
 * @return sectrue iff the fold reaches `trusted_model_root`
 */
secbool model_tree_verify_slot(const uint8_t* slot_value, size_t slot_len,
                               const merkle_proof_node_t* proof,
                               size_t proof_count,
                               const merkle_proof_node_t* trusted_model_root);
