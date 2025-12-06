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
#include "../secret_keys_common.h"

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

secbool secret_key_delegated_identity(uint16_t rotation_index,
                                      uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
#ifdef SECRET_UNPRIVILEGED_MASTER_KEY_SLOT
  static uint8_t key_slot = SECRET_UNPRIVILEGED_MASTER_KEY_SLOT;
#else
  static uint8_t key_slot = UNUSED_KEY_SLOT;
#endif
  return secret_key_derive_nist256p1(key_slot, KEY_INDEX_DELEGATED_IDENTITY,
                                     rotation_index, dest);
}

secbool secret_key_master_key_get(secret_key_master_key_t* master_key) {
  memset(master_key->bytes, 0, SECRET_KEY_MASTER_KEY_SIZE);
  master_key->size = SECRET_KEY_MASTER_KEY_SIZE;
  return sectrue;
}

#endif  // SECURE_MODE
