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

#ifdef SECRET_PRIVILEGED_MASTER_KEY_SLOT

#include "hmac.h"
#include "memzero.h"
#include "nist256p1.h"

// Key derivation indices
#define KEY_INDEX_MCU_DEVICE_AUTH 0
#define KEY_INDEX_OPTIGA_PAIRING 1
#define KEY_INDEX_OPTIGA_MASKING 2
#define KEY_INDEX_TROPIC_PAIRING_UNPRIVILEGED 3
#define KEY_INDEX_TROPIC_PAIRING_PRIVILEGED 4
#define KEY_INDEX_TROPIC_MASKING 5
#define KEY_INDEX_NRF_PAIRING 6
#define KEY_INDEX_STORAGE_SALT 7

static secbool secret_key_derive_sym(uint8_t slot, uint16_t index,
                                     uint16_t subindex,
                                     uint8_t dest[SHA256_DIGEST_LENGTH]) {
  secbool ret = sectrue;

  // The diversifier consists of:
  // - the key derivation index (2 bytes big-endian), which identifies the
  //   purpose of the key,
  // - the subindex (2 bytes big-endian), which is incremented until the derived
  //   key meets required criteria, and
  // - the block index (1 byte), which can be used to produce outputs that are
  //   longer than 32 bytes.
  uint8_t diversifier[] = {index >> 8, index & 0xff, subindex >> 8,
                           subindex & 0xff, 0};

  uint8_t master_key[32] = {0};
  ret = secret_key_get(slot, master_key, sizeof(master_key));
  if (ret != sectrue) {
    goto cleanup;
  }

  hmac_sha256(master_key, sizeof(master_key), diversifier, sizeof(diversifier),
              dest);

cleanup:
  memzero(master_key, sizeof(master_key));
  return ret;
}

static secbool secret_key_derive_curve25519(uint8_t slot, uint16_t index,
                                            curve25519_key dest) {
  _Static_assert(sizeof(curve25519_key) == SHA256_DIGEST_LENGTH);

  secbool ret = secret_key_derive_sym(slot, index, 0, dest);
  dest[0] &= 248;
  dest[31] &= 127;
  dest[31] |= 64;
  return ret;
}

#if defined(USE_OPTIGA) || defined(USE_TROPIC)
static secbool secret_key_derive_nist256p1(
    uint8_t slot, uint16_t index, uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  _Static_assert(ECDSA_PRIVATE_KEY_SIZE == SHA256_DIGEST_LENGTH);

  secbool ret = sectrue;
  bignum256 s = {0};
  for (uint16_t i = 0; i < 10000; i++) {
    ret = secret_key_derive_sym(slot, index, i, dest);
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
  return ret;
}
#endif

secbool secret_key_mcu_device_auth(curve25519_key dest) {
  return secret_key_derive_curve25519(SECRET_PRIVILEGED_MASTER_KEY_SLOT,
                                      KEY_INDEX_MCU_DEVICE_AUTH, dest);
}

#ifdef USE_OPTIGA
secbool secret_key_optiga_pairing(uint8_t dest[OPTIGA_PAIRING_SECRET_SIZE]) {
  _Static_assert(OPTIGA_PAIRING_SECRET_SIZE == SHA256_DIGEST_LENGTH);
  return secret_key_derive_sym(SECRET_PRIVILEGED_MASTER_KEY_SLOT,
                               KEY_INDEX_OPTIGA_PAIRING, 0, dest);
}

secbool secret_key_optiga_masking(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  return secret_key_derive_nist256p1(SECRET_PRIVILEGED_MASTER_KEY_SLOT,
                                     KEY_INDEX_OPTIGA_MASKING, dest);
}
#endif  // USE_OPTIGA

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
                                     KEY_INDEX_TROPIC_MASKING, dest);
}

#endif  // USE_TROPIC

#ifdef USE_NRF

static secbool secequal(const void *ptr1, const void *ptr2, size_t n) {
  const uint8_t *p1 = ptr1;
  const uint8_t *p2 = ptr2;
  uint8_t diff = 0;
  size_t i = 0;
  for (i = 0; i < n; ++i) {
    diff |= *p1 ^ *p2;
    ++p1;
    ++p2;
  }
  return diff ? secfalse : sectrue;
}

secbool secret_key_nrf_pairing(uint8_t dest[NRF_PAIRING_SECRET_SIZE]) {
  _Static_assert(NRF_PAIRING_SECRET_SIZE == SHA256_DIGEST_LENGTH);
  return secret_key_derive_sym(SECRET_UNPRIVILEGED_MASTER_KEY_SLOT,
                               KEY_INDEX_NRF_PAIRING, 0, dest);
}

secbool secret_validate_nrf_pairing(const uint8_t *message, size_t msg_len,
                                    const uint8_t *mac, size_t mac_len) {
  secbool result = secfalse;

  uint8_t key[NRF_PAIRING_SECRET_SIZE] = {0};
  if (sectrue != secret_key_nrf_pairing(key)) {
    return secfalse;
  }

  if (mac_len != SHA256_DIGEST_LENGTH) {
    goto cleanup;
  }

  uint8_t dest[SHA256_DIGEST_LENGTH] = {0};

  hmac_sha256(key, sizeof(key), message, msg_len, dest);

  if (secequal(dest, mac, SHA256_DIGEST_LENGTH) == sectrue) {
    result = sectrue;
  }

cleanup:
  memzero(dest, sizeof(dest));
  memzero(key, sizeof(key));
  return result;
}

#endif

secbool secret_key_storage_salt(uint16_t fw_type,
                                uint8_t dest[SECRET_KEY_STORAGE_SALT_SIZE]) {
  _Static_assert(SECRET_KEY_STORAGE_SALT_SIZE == SHA256_DIGEST_LENGTH);
  return secret_key_derive_sym(SECRET_UNPRIVILEGED_MASTER_KEY_SLOT,
                               KEY_INDEX_STORAGE_SALT, fw_type, dest);
}

#else  // SECRET_PRIVILEGED_MASTER_KEY_SLOT

#ifdef USE_OPTIGA
secbool secret_key_optiga_pairing(uint8_t dest[OPTIGA_PAIRING_SECRET_SIZE]) {
  return secret_key_get(SECRET_OPTIGA_SLOT, dest, OPTIGA_PAIRING_SECRET_SIZE);
}
#endif  // USE_OPTIGA

#endif  // SECRET_PRIVILEGED_MASTER_KEY_SLOT

#endif  // SECURE_MODE
