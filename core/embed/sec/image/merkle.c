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
 * Merkle leaf and node hashing shared by the firmware tree and the model tree.
 * Pure hash math over caller-supplied buffers, so not secure-mode gated, and
 * built verbatim by the host tests.
 */

// In a host test build these come from its shim header.
#ifndef SEC_IMAGE_SHIMMED
#include <string.h>

#include <sec/image_hash_conf.h>
#include <sec/merkle.h>
#endif

void merkle_leaf_hash(const uint8_t* data, size_t len,
                      merkle_proof_node_t* out) {
  static const uint8_t prefix0[] = {0x00};
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix0, sizeof(prefix0));
  IMAGE_HASH_UPDATE(&ctx, data, len);
  IMAGE_HASH_FINAL(&ctx, out->bytes);
}

void merkle_node_hash(const merkle_proof_node_t* a,
                      const merkle_proof_node_t* b, merkle_proof_node_t* out) {
  static const uint8_t prefix1[] = {0x01};
  IMAGE_HASH_CTX ctx;
  IMAGE_HASH_INIT(&ctx);
  IMAGE_HASH_UPDATE(&ctx, prefix1, sizeof(prefix1));
  if (memcmp(a->bytes, b->bytes, sizeof(a->bytes)) < 0) {
    IMAGE_HASH_UPDATE(&ctx, a->bytes, sizeof(a->bytes));
    IMAGE_HASH_UPDATE(&ctx, b->bytes, sizeof(b->bytes));
  } else {
    IMAGE_HASH_UPDATE(&ctx, b->bytes, sizeof(b->bytes));
    IMAGE_HASH_UPDATE(&ctx, a->bytes, sizeof(a->bytes));
  }
  IMAGE_HASH_FINAL(&ctx, out->bytes);
}
