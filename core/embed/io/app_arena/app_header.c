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

#include <io/app_header.h>
#include <io/app_root.h>

#include <sha2.h>

const app_header_t* app_header_verify(const void* header_ptr,
                                      size_t header_size) {
  TSH_DECLARE;
  const app_header_t* retval = NULL;

  TSH_CHECK(header_ptr != NULL, TS_EINVAL);
  TSH_CHECK(header_size >= sizeof(app_header_t), TS_EINVAL);

  const app_header_t* header = (const app_header_t*)header_ptr;

  TSH_CHECK(header->magic == APP_HEADER_MAGIC, TS_EBADMSG);
  TSH_CHECK(header->header_size == header_size, TS_EBADMSG);
  TSH_CHECK(header->abi_version == 1, TS_EBADMSG);
  TSH_CHECK(header->app_ring < APP_RING_COUNT, TS_EBADMSG);

  retval = header;

cleanup:
  return retval;
}

ts_t app_header_calc_merkle_root(const app_header_t* header,
                                 const sha256_digest_t* proof,
                                 size_t proof_size, sha256_digest_t* root) {
  TSH_DECLARE;

  TSH_CHECK(root != NULL, TS_EINVAL);
  memset(root, 0, sizeof(*root));

  TSH_CHECK(header != NULL, TS_EINVAL);
  TSH_CHECK(proof_size == 0 || proof != NULL, TS_EINVAL);
  TSH_CHECK(proof_size % sizeof(sha256_digest_t) == 0, TS_EINVAL);

  static const uint8_t prefix0[] = {0x00};
  static const uint8_t prefix1[] = {0x01};

  // Calculate header hash
  SHA256_CTX ctx;
  sha256_Init(&ctx);
  sha256_Update(&ctx, prefix0, sizeof(prefix0));
  sha256_Update(&ctx, (const uint8_t*)header, header->header_size);
  sha256_Final(&ctx, root->bytes);

  // Add the Merkle proof nodes to the hash
  for (size_t i = 0; i < proof_size / sizeof(sha256_digest_t); i++) {
    const sha256_digest_t* node = &proof[i];
    sha256_Init(&ctx);
    sha256_Update(&ctx, prefix1, sizeof(prefix1));
    if (memcmp(node, root->bytes, sizeof(root->bytes)) < 0) {
      sha256_Update(&ctx, node->bytes, sizeof(node->bytes));
      sha256_Update(&ctx, root->bytes, sizeof(root->bytes));
    } else {
      sha256_Update(&ctx, root->bytes, sizeof(root->bytes));
      sha256_Update(&ctx, node->bytes, sizeof(node->bytes));
    }
    sha256_Final(&ctx, root->bytes);
  }

cleanup:
  TSH_RETURN;
}

ts_t app_header_verify_signature(const app_header_t* header,
                                 const sha256_digest_t* proof,
                                 size_t proof_size, secbool* valid) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK(header != NULL, TS_EINVAL);
  TSH_CHECK(valid != NULL, TS_EINVAL);

  *valid = secfalse;

  sha256_digest_t calc_root = {.bytes = {0}};
  status = app_header_calc_merkle_root(header, proof, proof_size, &calc_root);
  TSH_CHECK_OK(status);

  sha256_digest_t exp_root = {.bytes = {0}};
  status = app_root_get_merkle_root(header->app_ring, &exp_root);
  TSH_CHECK_OK(status);

  volatile int cmp1 = memcmp(&calc_root, &exp_root, sizeof(calc_root));
  if (cmp1 == 0) {
    *valid = sectrue;
  }

  // FIH
  volatile int cmp2 = memcmp(&exp_root, &calc_root, sizeof(calc_root));
  if (cmp2 != 0) {
    *valid = secfalse;
  }

cleanup:
  TSH_RETURN;
}

ts_t app_header_get_app_ring(const void* header_ptr, size_t header_size,
                             uint8_t* app_ring) {
  TSH_DECLARE;

  TSH_CHECK_ARG(header_ptr != NULL);
  TSH_CHECK_ARG(app_ring != NULL);

  const app_header_t* header = app_header_verify(header_ptr, header_size);
  TSH_CHECK(header != NULL, TS_EBADMSG);

  *app_ring = header->app_ring;

cleanup:
  TSH_RETURN;
}
