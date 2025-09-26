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

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/secret.h>
#include <sec/secret_keys.h>

#ifdef USE_OPTIGA
secbool secret_key_optiga_pairing(uint8_t dest[OPTIGA_PAIRING_SECRET_SIZE]) {
  return secret_key_get(SECRET_OPTIGA_SLOT, dest, OPTIGA_PAIRING_SECRET_SIZE);
}

#include <sec/storage.h>
#include "../../storage/storage_salt.h"
#include "memzero.h"
#include "pbkdf2.h"
#define DELEGATED_IDENTITY_KEY_ITER_COUNT 20000
#define DELEGATED_IDENTITY_KEY_HEADER_LENGTH 21

secbool secret_key_delegated_identity(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  additional_salt_t salt = {0};
  additional_salt_get(&salt);

  const uint8_t header[DELEGATED_IDENTITY_KEY_HEADER_LENGTH] =
      "DelegatedIdentityKey";
  PBKDF2_HMAC_SHA256_CTX ctx = {0};
  pbkdf2_hmac_sha256_Init(&ctx, header, DELEGATED_IDENTITY_KEY_HEADER_LENGTH,
                          salt.bytes, STORAGE_SALT_SIZE, 1);

  for (int i = 1; i <= 10; i++) {
    pbkdf2_hmac_sha256_Update(&ctx, DELEGATED_IDENTITY_KEY_ITER_COUNT / 10);
  }
  pbkdf2_hmac_sha256_Final(&ctx, dest);
  memzero(&salt, sizeof(salt));
  memzero(&ctx, sizeof(ctx));
  return sectrue;
}
#endif  // USE_OPTIGA
#endif  // SECURE_MODE
