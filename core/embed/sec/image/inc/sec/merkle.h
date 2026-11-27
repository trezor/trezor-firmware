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

/**
 * Merkle proof node (SHA-256 digest)
 */
typedef struct {
  uint8_t bytes[32];
} merkle_proof_node_t;

/**
 * @brief Merkle LEAF hash H(0x00 || data); counterpart of the 0x01-tagged
 *        internal node.
 *
 * @param data  bytes to commit
 * @param len   length of @p data
 * @param out   [out] the resulting leaf
 */
void merkle_leaf_hash(const uint8_t* data, size_t len,
                      merkle_proof_node_t* out);

/**
 * @brief Combines two nodes into their parent: H(0x01 || min(a,b) || max(a,b)).
 *        The pair is sorted, so a co-path carries no left/right position.
 *        In-place safe (out == a or out == b).
 *
 * @param a    one child
 * @param b    the other child
 * @param out  [out] the parent node
 */
void merkle_node_hash(const merkle_proof_node_t* a,
                      const merkle_proof_node_t* b, merkle_proof_node_t* out);
