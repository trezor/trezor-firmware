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

#include <sec/secret_keys.h>
#include "../secret_keys_common.h"

#ifdef USE_SECRET
#include <sec/secret.h>
#endif

#ifdef USE_MCU_ATTESTATION
secbool secret_key_mcu_device_auth(uint8_t dest[MLDSA_SEEDBYTES]) {
#ifdef TREZOR_PRODTEST
  uint8_t key[SECRET_MASTER_KEY_SLOT_SIZE] = {0};
  if (secret_key_get(SECRET_PRIVILEGED_MASTER_KEY_SLOT, key, sizeof(key)) !=
      sectrue) {
    return secfalse;
  }
#endif

  _Static_assert(MLDSA_SEEDBYTES == SHA256_DIGEST_LENGTH, "");
  memset(dest, 3, SHA256_DIGEST_LENGTH);
  return sectrue;
}
#endif  // USE_MCU_ATTESTATION

#ifdef USE_TROPIC
secbool secret_key_tropic_public(curve25519_key dest) {
  return secret_key_get(SECRET_TROPIC_TROPIC_PUBKEY_SLOT, dest,
                        sizeof(curve25519_key));
}

secbool secret_key_tropic_pairing_unprivileged(curve25519_key dest) {
  return secret_key_derive_curve25519(SECRET_UNPRIVILEGED_MASTER_KEY_SLOT,
                                      KEY_INDEX_TROPIC_PAIRING_UNPRIVILEGED,
                                      dest);
}

secbool secret_key_tropic_pairing_privileged(curve25519_key dest) {
  return secret_key_derive_curve25519(SECRET_PRIVILEGED_MASTER_KEY_SLOT,
                                      KEY_INDEX_TROPIC_PAIRING_PRIVILEGED,
                                      dest);
}

secbool secret_key_tropic_masking(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  return secret_key_derive_nist256p1(SECRET_PRIVILEGED_MASTER_KEY_SLOT,
                                     KEY_INDEX_TROPIC_MASKING, 0, dest);
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
