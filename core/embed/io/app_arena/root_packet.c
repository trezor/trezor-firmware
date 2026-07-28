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

#ifdef KERNEL_MODE

#include <trezor_rtl.h>

#include <io/app_root.h>

#include <sha2.h>

#include "root_packet.h"

static const mldsa44_public_key_t * const ROOT_PACKET_KEYS[] = {
#if defined(BOOTLOADER_DEVEL) || defined(TREZOR_EMULATOR)
    (const mldsa44_public_key_t*) "\xec\x01\xe6\x02\x63\x02\x4f\x7e\x71\x72\x80\x13\xb7\x31\xf7\xba\x12\x99\xf5\x18\xc2\x7b\xa3\xed\x8f\x4a\x21\x99\x74\x12\x7c\x62",
    (const mldsa44_public_key_t*) "\x8a\xf8\x87\x80\x85\x94\x6e\xd8\xb1\x16\xbd\x24\xc0\xf2\xaa\xc4\x8b\x7e\x8f\x11\xbf\x06\x87\x25\xcc\xfb\xb1\x52\xab\xf7\xa4\xcd",
#else
    MODEL_ROOT_PACKET_KEYS
#endif
};

ts_t root_packet_verify(const void* data, size_t size,
                        root_packet_auth_t** out) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(data != NULL);
  TSH_CHECK_ARG(out != NULL);

  *out = NULL;

  TSH_CHECK(size >= sizeof(root_packet_auth_t), TS_EBADMSG);

  root_packet_auth_t* auth = (root_packet_auth_t*)data;

  TSH_CHECK(auth->magic == ROOT_PACKET_MAGIC, TS_EBADMSG);
  TSH_CHECK(auth->version == ROOT_PACKET_VERSION, TS_EBADMSG);
  TSH_CHECK(auth->ring_mask != 0, TS_EBADMSG);
  TSH_CHECK(auth->ring_mask <= (1 << APP_RING_COUNT) - 1, TS_EBADMSG);
  TSH_CHECK(auth->timestamp != 0, TS_EBADMSG);

  // Calculate the expected size of the authenticated part of the root packet
  size_t auth_part_size =
      sizeof(root_packet_auth_t) +
      sizeof(sha256_digest_t) * __builtin_popcount(auth->ring_mask);

  TSH_CHECK(size == auth_part_size + sizeof(root_packet_unauth_t), TS_EBADMSG);

  // Calculate hash of authenticated part of the root packet
  sha256_digest_t auth_hash;
  SHA256_CTX ctx;
  sha256_Init(&ctx);
  sha256_Update(&ctx, (const uint8_t*)auth, auth_part_size);
  sha256_Final(&ctx, auth_hash.bytes);

  // Verify signatures
  root_packet_unauth_t* unauth =
      (root_packet_unauth_t*)((uint8_t*)auth + auth_part_size);

  uint8_t sigmask = auth->sigmask;
  uint8_t sigmask_inv = 0;  // FIH

  TSH_CHECK(__builtin_popcount(sigmask) == ARRAY_LENGTH(unauth->signature),
            TS_EBADMSG);

  for (int sig_idx = 0; sig_idx < ARRAY_LENGTH(unauth->signature); sig_idx++) {
    // Get the index of the public key in the signature mask
    int key_idx = __builtin_ctz(sigmask);
    TSH_CHECK(key_idx < ARRAY_LENGTH(ROOT_PACKET_KEYS), TS_EBADMSG);

    secbool valid = secfalse;
    status =
        mldsa44_verify(&unauth->signature[sig_idx], &auth_hash,
                       sizeof(auth_hash), ROOT_PACKET_KEYS[key_idx], &valid);
    TSH_CHECK_OK(status);
    TSH_CHECK(valid == sectrue, TS_EBADMSG);

    // Mark the key as used
    sigmask &= ~(1 << key_idx);
    sigmask_inv |= (1 << key_idx);
  }

  // Check that all signatures were verified
  TSH_CHECK(sigmask == 0, TS_EBADMSG);
  TSH_CHECK(sigmask_inv == auth->sigmask, TS_EBADMSG);  // FIH

  *out = auth;

cleanup:
  TSH_RETURN;
}

#endif  // KERNEL_MODE
