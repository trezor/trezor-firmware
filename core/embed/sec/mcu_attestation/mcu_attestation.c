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
#ifdef USE_MCU_ATTESTATION

#include <trezor_rtl.h>
#include <trezor_types.h>

#include <sec/mcu_attestation.h>
#include <sec/secret_keys.h>
#include <sys/rng.h>
#include <sys/startup_args.h>

#include <mldsa_native.h>

#include "memzero.h"

#ifndef SECRET_PRIVILEGED_MASTER_KEY_SLOT
#error "USE_MCU_ATTESTATION requires SECRET_PRIVILEGED_MASTER_KEY_SLOT."
#endif

secbool mcu_attestation_cert_size(size_t *cert_size) {
  if (ts_ok(startup_args_get(STARTUP_ARGS_TYPE_MCU_DEVICE_CERT, NULL,
                             cert_size))) {
    return sectrue;
  }
  return secfalse;
}

secbool mcu_attestation_cert_read(uint8_t *cert, size_t max_cert_size,
                                  size_t *cert_size) {
  const void *value = NULL;
  size_t size = 0;
  if (ts_error(
          startup_args_get(STARTUP_ARGS_TYPE_MCU_DEVICE_CERT, &value, &size))) {
    return secfalse;
  }
  if (size > max_cert_size) {
    return secfalse;
  }
  memcpy(cert, value, size);
  *cert_size = size;
  return sectrue;
}

secbool mcu_attestation_sign(const uint8_t *challenge, size_t challenge_size,
                             uint8_t signature[MCU_ATTESTATION_SIG_SIZE]) {
  secbool ret = secfalse;

  uint8_t seed[MLDSA_SEEDBYTES] = {0};
  if (secret_key_mcu_device_auth(seed) != sectrue) {
    goto cleanup;
  }

  uint8_t mcu_public[MCU_ATTESTATION_PUBKEY_SIZE] = {0};
  uint8_t mcu_private[MCU_ATTESTATION_PRIVKEY_SIZE] = {0};
  if (mldsa_keypair_internal(mcu_public, mcu_private, seed) != 0) {
    goto cleanup;
  }

  uint8_t rnd[MLDSA_RNDBYTES] = {0};
  rng_fill_buffer(rnd, sizeof(rnd));

  const uint8_t ENCODED_EMPTY_CONTEXT_STRING[] = {0, 0};
  size_t siglen = 0;
  if (mldsa_signature_internal(signature, &siglen, challenge, challenge_size,
                               ENCODED_EMPTY_CONTEXT_STRING,
                               sizeof(ENCODED_EMPTY_CONTEXT_STRING), rnd,
                               mcu_private, 0) != 0) {
    goto cleanup;
  }

  ret = sectrue;

cleanup:
  memzero(seed, sizeof(seed));
  memzero(mcu_private, sizeof(mcu_private));
  memzero(rnd, sizeof(rnd));
  return ret;
}

#endif  // USE_MCU_ATTESTATION
#endif  // SECURE_MODE
