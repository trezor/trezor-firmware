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

#ifdef SECURE_MODE

#include <sec/secret.h>
#include <sec/secret_keys.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include "../storage/storage_salt.h"
#include "hmac.h"
#include "memzero.h"
#include "nist256p1.h"
#include "secret_keys_common.h"

static void diversify_and_derive(uint16_t index, uint16_t subindex,
                                 uint16_t rotation_index,
                                 const uint8_t master_key[SHA256_DIGEST_LENGTH],
                                 uint8_t master_key_length,
                                 uint8_t dest[SHA256_DIGEST_LENGTH]) {
  // The diversifier consists of:
  // - the key derivation index (2 bytes big-endian), which identifies the
  //   purpose of the key,
  // - the subindex (2 bytes big-endian), which is incremented until the derived
  //   key meets required criteria, and
  // - the block index (1 byte), which can be used to produce outputs that are
  //   longer than 32 bytes.

  uint8_t diversifier[rotation_index == 0 ? 5 : 7];

  /* first bytes (index + subindex) are common */
  diversifier[0] = (index >> 8) & 0xFF;
  diversifier[1] = index & 0xFF;
  diversifier[2] = (subindex >> 8) & 0xFF;
  diversifier[3] = subindex & 0xFF;

  if (rotation_index == 0) {
    diversifier[4] = 0;
  } else {
    diversifier[4] = (rotation_index >> 8) & 0xFF;
    diversifier[5] = rotation_index & 0xFF;
    diversifier[6] = 0;
  }

  hmac_sha256(master_key, master_key_length, diversifier, sizeof(diversifier),
              dest);
}

secbool secret_key_derive_sym(uint8_t slot, uint16_t index, uint16_t subindex,
                              uint16_t rotation_index,
                              uint8_t dest[SHA256_DIGEST_LENGTH]) {
  secbool ret = sectrue;

  secret_key_master_key_t master_key = {.bytes = {0},
                                        .size = SECRET_KEY_MASTER_KEY_SIZE};

#ifdef SECRET_PRIVILEGED_MASTER_KEY_SLOT
  ret = secret_key_get(slot, master_key.bytes, master_key.size);
#else   // SECRET_PRIVILEGED_MASTER_KEY_SLOT
  if (slot != UNUSED_KEY_SLOT) {
    ret = secfalse;
    goto cleanup;
  }
  ret = secret_key_master_key_get(&master_key);
#endif  // SECRET_PRIVILEGED_MASTER_KEY_SLOT

  if (ret != sectrue) {
    goto cleanup;
  }

  diversify_and_derive(index, subindex, rotation_index, master_key.bytes,
                       master_key.size, dest);

cleanup:
  memzero(master_key.bytes, master_key.size);
  return ret;
}

secbool secret_key_derive_nist256p1(uint8_t slot, uint16_t index,
                                    uint16_t rotation_index,
                                    uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  // `slot` argument is not used unless SECRET_PRIVILEGED_MASTER_KEY_SLOT is
  // defined

  _Static_assert(ECDSA_PRIVATE_KEY_SIZE == SHA256_DIGEST_LENGTH);

  secbool ret = sectrue;
  bignum256 s = {0};
  for (uint16_t i = 0; i < 10000; i++) {
    ret = secret_key_derive_sym(slot, index, i, rotation_index, dest);
    if (ret != sectrue) {
      goto cleanup;
    }

    bn_read_be(dest, &s);
    if (!bn_is_zero(&s) && bn_is_less(&s, &nist256p1.order)) {
      // Valid private key, we are done.
      ret = sectrue;
      goto cleanup;
    }

    // Invalid private key, we generate the next key in line.
  }

  // Loop exhausted all attempts without producing a valid private key.
  ret = secfalse;

cleanup:
  memzero(&s, sizeof(s));
  if (ret != sectrue) {
    memzero(dest, ECDSA_PRIVATE_KEY_SIZE);
  }
  return ret;
}

#endif  // SECURE_MODE
