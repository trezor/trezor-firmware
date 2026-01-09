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
#include "hmac.h"
#include "memzero.h"

#ifdef SECRET_PRIVILEGED_MASTER_KEY_SLOT

secbool secret_key_mcu_device_auth(uint8_t dest[MLDSA_SEEDBYTES]) {
  _Static_assert(MLDSA_SEEDBYTES == SHA256_DIGEST_LENGTH);
  return secret_key_derive_sym(SECRET_PRIVILEGED_MASTER_KEY_SLOT,
                               KEY_INDEX_MCU_DEVICE_AUTH, 0, dest);
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

secbool secret_key_delegated_identity(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  return secret_key_derive_nist256p1(SECRET_UNPRIVILEGED_MASTER_KEY_SLOT,
                                     KEY_INDEX_DELEGATED_IDENTITY, dest);
}

#ifdef USE_TROPIC
static secbool secret_key_derive_curve25519(uint8_t slot, uint16_t index,
                                            curve25519_key dest) {
  _Static_assert(sizeof(curve25519_key) == SHA256_DIGEST_LENGTH);

  secbool ret = secret_key_derive_sym(slot, index, 0, dest);
  dest[0] &= 248;
  dest[31] &= 127;
  dest[31] |= 64;
  return ret;
}

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

#ifdef USE_NRF_AUTH

static secbool secequal(const void* ptr1, const void* ptr2, size_t n) {
  const uint8_t* p1 = ptr1;
  const uint8_t* p2 = ptr2;
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

  if (secfalse != secret_is_locked()) {
    return secfalse;
  }

  return secret_key_derive_sym(SECRET_UNPRIVILEGED_MASTER_KEY_SLOT,
                               KEY_INDEX_NRF_PAIRING, 0, dest);
}

secbool secret_validate_nrf_pairing(const uint8_t* message, size_t msg_len,
                                    const uint8_t* mac, size_t mac_len) {
  secbool result = secfalse;

  uint8_t key[NRF_PAIRING_SECRET_SIZE] = {0};

  if (sectrue != secret_key_derive_sym(SECRET_UNPRIVILEGED_MASTER_KEY_SLOT,
                                       KEY_INDEX_NRF_PAIRING, 0, key)) {
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

#endif  // USE_NRF_AUTH

secbool secret_key_storage_salt(uint16_t fw_type,
                                uint8_t dest[SECRET_KEY_STORAGE_SALT_SIZE]) {
  _Static_assert(SECRET_KEY_STORAGE_SALT_SIZE == SHA256_DIGEST_LENGTH);
  return secret_key_derive_sym(SECRET_UNPRIVILEGED_MASTER_KEY_SLOT,
                               KEY_INDEX_STORAGE_SALT, fw_type, dest);
}

#else  // SECRET_PRIVILEGED_MASTER_KEY_SLOT
#include <sec/rng_strong.h>
#include <sys/flash_otp.h>
#include <sys/mpu.h>

#ifdef USE_OPTIGA
secbool secret_key_optiga_pairing(uint8_t dest[OPTIGA_PAIRING_SECRET_SIZE]) {
  return secret_key_get(SECRET_OPTIGA_SLOT, dest, OPTIGA_PAIRING_SECRET_SIZE);
}
#endif  // USE_OPTIGA

secbool secret_key_master_key_get(secret_key_master_key_t* master_key) {
  if (secfalse == flash_otp_is_locked(FLASH_OTP_BLOCK_MASTER_KEY)) {
    uint8_t rnd_bytes[SECRET_KEY_MASTER_KEY_SIZE];
    if (!rng_fill_buffer_strong(rnd_bytes, SECRET_KEY_MASTER_KEY_SIZE)) {
      memzero(rnd_bytes, sizeof(rnd_bytes));
      return secfalse;
    }
    ensure(flash_otp_write(FLASH_OTP_BLOCK_MASTER_KEY, 0, rnd_bytes,
                           SECRET_KEY_MASTER_KEY_SIZE),
           NULL);
  }
  ensure(flash_otp_read(FLASH_OTP_BLOCK_MASTER_KEY, 0, &master_key->bytes[0],
                        SECRET_KEY_MASTER_KEY_SIZE),
         NULL);

  master_key->size = SECRET_KEY_MASTER_KEY_SIZE;
  return sectrue;
}

secbool secret_key_delegated_identity(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  return secret_key_derive_nist256p1(UNUSED_KEY_SLOT,
                                     KEY_INDEX_DELEGATED_IDENTITY, dest);
}

#endif  // SECRET_PRIVILEGED_MASTER_KEY_SLOT

#endif  // SECURE_MODE
