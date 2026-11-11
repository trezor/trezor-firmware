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
#include <rtl/sizedefs.h>

#include <sha2.h>

#include "root_packet.h"
#include "root_packet_keys.h"

// Maximum allowed time difference between the root packet and its
// higher-level root packet.
#define ROOT_PACKET_MAX_DRIFT (90 * 86400)  // 90 days

static const mldsa44_public_key_t * const ROOT_PACKET_KEYS[] = {
#if defined(BOOTLOADER_DEVEL) || defined(TREZOR_EMULATOR)
  ROOT_PACKET_MLDSA44_KEYS_DEV
#else
  ROOT_PACKET_MLDSA44_KEYS
#endif
};

// Returns the number of set bits in the given value.
static int popcount(uint8_t value) {
  int count = 0;
  while (value != 0) {
    if ((value & 1) != 0) {
      count++;
    }
    value >>= 1;
  }
  return count;
}

// Returns true if the set bits in mask form a single contiguous run.
// Assumes mask != 0
static bool is_contiguous_mask(uint8_t mask) {
  // mask | (mask - 1) sets all bits below the lowest set bit.
  // For a contiguous run the result is 2^n - 1, so adding one yields
  // a single power of two, i.e. x & (x - 1) == 0.
  uint32_t x = (uint32_t)(mask | (mask - 1)) + 1;
  return (x & (x - 1)) == 0;
}

ts_t root_packet_verify(const void* data, size_t size,
                        root_packet_auth_t** out) {
  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(data != NULL);
  TSH_CHECK_ARG(out != NULL);

  *out = NULL;

  TSH_CHECK(size >= sizeof(root_packet_auth_t), TS_EBADMSG);
  TSH_CHECK(IS_ALIGNED((uintptr_t)data, _Alignof(root_packet_auth_t)),
            TS_EBADMSG);

  root_packet_auth_t* auth = (root_packet_auth_t*)data;

  TSH_CHECK(auth->magic == ROOT_PACKET_MAGIC, TS_EBADMSG);
  TSH_CHECK(auth->version == ROOT_PACKET_VERSION, TS_EBADMSG);
  TSH_CHECK(auth->ring_mask != 0, TS_EBADMSG);
  TSH_CHECK(auth->ring_mask <= (1 << APP_RING_COUNT) - 1, TS_EBADMSG);
  TSH_CHECK(is_contiguous_mask(auth->ring_mask), TS_EBADMSG);
  TSH_CHECK(auth->timestamp > 0, TS_EBADMSG);
  TSH_CHECK(auth->chain_timestamp >= 0, TS_EBADMSG);

  if (auth->ring_mask & (1 << APP_RING_0)) {
    // Ring #0 - no chain timestamp
    TSH_CHECK(auth->chain_timestamp == 0, TS_EBADMSG);
  } else {
    // Ring #1 and/or #2
    // Both operands are non-negative, so the subtraction cannot overflow
    int64_t diff = auth->timestamp - auth->chain_timestamp;
    TSH_CHECK(diff >= -ROOT_PACKET_MAX_DRIFT && diff <= ROOT_PACKET_MAX_DRIFT,
              TS_EBADMSG);
  }

  // Calculate the expected size of the authenticated part of the root packet
  size_t auth_part_size = sizeof(root_packet_auth_t) +
                          sizeof(sha256_digest_t) * popcount(auth->ring_mask);

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
  TSH_CHECK(IS_ALIGNED((uintptr_t)unauth, _Alignof(root_packet_unauth_t)),
            TS_EBADMSG);

  uint8_t sigmask = unauth->sigmask;
  uint8_t sigmask_inv = 0;  // FIH

  TSH_CHECK(popcount(sigmask) == ARRAY_LENGTH(unauth->signature), TS_EBADMSG);

  for (size_t sig_idx = 0; sig_idx < ARRAY_LENGTH(unauth->signature);
       sig_idx++) {
    // Get the index of the public key in the signature mask
    size_t key_idx = __builtin_ctz(sigmask);
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
  TSH_CHECK(sigmask_inv == unauth->sigmask, TS_EBADMSG);  // FIH

  *out = auth;

cleanup:
  TSH_RETURN;
}

#endif  // KERNEL_MODE
