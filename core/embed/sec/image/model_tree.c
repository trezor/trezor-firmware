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
 * Model-tree slot verification. Pure hash math over caller-supplied buffers,
 * so not secure-mode gated, and built verbatim by the host tests.
 */

// In a host test build these come from its shim header.
#ifndef SEC_IMAGE_SHIMMED
#include <string.h>

#include <sec/model_tree.h>
#endif

// Fold a model-tree slot value up to modelRoot. Proves founder commitment
// only; identity (model, kind, index) must be inside the value itself.
secbool model_tree_verify_slot(const uint8_t* slot_value, size_t slot_len,
                               const merkle_proof_node_t* proof,
                               size_t proof_count,
                               const merkle_proof_node_t* trusted_model_root) {
  if (slot_value == NULL || slot_len == 0 || trusted_model_root == NULL) {
    return secfalse;
  }
  merkle_proof_node_t node;
  merkle_leaf_hash(slot_value, slot_len, &node);
  for (size_t i = 0; i < proof_count; i++) {
    merkle_node_hash(&node, &proof[i], &node);
  }
  // FIH: a single, unhardened memcmp -- on T3W1 the only founder check the
  // nRF image gets.
  return (memcmp(node.bytes, trusted_model_root->bytes, sizeof(node.bytes)) ==
          0)
             ? sectrue
             : secfalse;
}
