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

#ifdef USE_TROPIC

static uint8_t SECRET_TROPIC_PAIRING_BYTES[] = {
    0xf0, 0xc4, 0xaa, 0x04, 0x8f, 0x00, 0x13, 0xa0, 0x96, 0x84, 0xdf,
    0x05, 0xe8, 0xa2, 0x2e, 0xf7, 0x21, 0x38, 0x98, 0x28, 0x2b, 0xa9,
    0x43, 0x12, 0xf3, 0x13, 0xdf, 0x2d, 0xce, 0x8d, 0x41, 0x64};

static uint8_t SECRET_TROPIC_PUBKEY_BYTES[] = {
    0x31, 0xE9, 0x0A, 0xF1, 0x50, 0x45, 0x10, 0xEE, 0x4E, 0xFD, 0x79,
    0x13, 0x33, 0x41, 0x48, 0x15, 0x89, 0xA2, 0x89, 0x5C, 0xC5, 0xFB,
    0xB1, 0x3E, 0xD5, 0x71, 0x1C, 0x1E, 0x9B, 0x81, 0x98, 0x72};

_Static_assert(sizeof(SECRET_TROPIC_PAIRING_BYTES) == sizeof(curve25519_key),
               "Invalid size of Tropic pairing key");

_Static_assert(sizeof(SECRET_TROPIC_PUBKEY_BYTES) == sizeof(curve25519_key),
               "Invalid size of Tropic public key");

secbool secret_key_mcu_device_auth(uint8_t dest[MLDSA_SEEDBYTES]) {
  _Static_assert(MLDSA_SEEDBYTES == SHA256_DIGEST_LENGTH);
  memset(dest, 3, SHA256_DIGEST_LENGTH);
  return sectrue;
}

secbool secret_key_tropic_public(curve25519_key dest) {
  memcpy(dest, SECRET_TROPIC_PUBKEY_BYTES, sizeof(curve25519_key));
  return sectrue;
}

secbool secret_key_tropic_pairing_unprivileged(curve25519_key dest) {
  memset(dest, 2, sizeof(curve25519_key));
  return sectrue;
}

secbool secret_key_tropic_pairing_privileged(curve25519_key dest) {
  memcpy(dest, SECRET_TROPIC_PAIRING_BYTES, sizeof(curve25519_key));
  return sectrue;
}

secbool secret_key_tropic_masking(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  memset(dest, 1, ECDSA_PRIVATE_KEY_SIZE);
  return sectrue;
}

#endif  // USE_TROPIC

#ifdef USE_OPTIGA
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
