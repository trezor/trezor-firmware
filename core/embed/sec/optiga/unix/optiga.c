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

#include <trezor_rtl.h>

#include <sec/optiga.h>
#include <sec/optiga_common.h>
#include "ecdsa.h"
#include "nist256p1.h"
#include "rand.h"
#include "storage.h"

#if defined(TREZOR_MODEL_T2B1)
#include "certs/T2B1.h"
#define DEVICE_CERT_CHAIN T2B1_der
#elif defined(TREZOR_MODEL_T3T1)
#include "certs/T3T1.h"
#define DEVICE_CERT_CHAIN T3T1_der
#elif defined(TREZOR_MODEL_T3B1)
#include "certs/T3B1.h"
#define DEVICE_CERT_CHAIN T3B1_der
#elif defined(TREZOR_MODEL_T3W1)
#include "certs/T3W1.h"
#define DEVICE_CERT_CHAIN T3W1_der
#else
#error "Cert chain for specified model is not available."
#endif

optiga_sign_result optiga_sign(uint8_t index, const uint8_t *digest,
                               size_t digest_size, uint8_t *signature,
                               size_t max_sig_size, size_t *sig_size) {
  const uint8_t DEVICE_PRIV_KEY[32] = {1};

  if (index != OPTIGA_DEVICE_ECC_KEY_INDEX) {
    return OPTIGA_SIGN_ERROR;
  }

  if (max_sig_size < 72) {
    return OPTIGA_SIGN_ERROR;
  }

  uint8_t raw_signature[64] = {0};
  int ret = ecdsa_sign_digest(&nist256p1, DEVICE_PRIV_KEY, digest,
                              raw_signature, NULL, NULL);
  if (ret != 0) {
    return OPTIGA_SIGN_ERROR;
  }

  *sig_size = ecdsa_sig_to_der(raw_signature, signature);
  return OPTIGA_SIGN_SUCCESS;
}

bool optiga_cert_size(uint8_t index, size_t *cert_size) {
  if (index != OPTIGA_DEVICE_CERT_INDEX) {
    return false;
  }

  *cert_size = sizeof(DEVICE_CERT_CHAIN);
  return true;
}

bool optiga_read_cert(uint8_t index, uint8_t *cert, size_t max_cert_size,
                      size_t *cert_size) {
  if (index != OPTIGA_DEVICE_CERT_INDEX) {
    return false;
  }

  if (max_cert_size < sizeof(DEVICE_CERT_CHAIN)) {
    return false;
  }

  memcpy(cert, DEVICE_CERT_CHAIN, sizeof(DEVICE_CERT_CHAIN));
  *cert_size = sizeof(DEVICE_CERT_CHAIN);
  return true;
}

bool optiga_read_sec(uint8_t *sec) {
  *sec = 0;
  return true;
}

void optiga_set_sec_max(void) {}

uint32_t optiga_estimate_time_ms(storage_pin_op_t op) { return 0; }

bool optiga_random_buffer(uint8_t *dest, size_t size) {
  random_buffer(dest, size);
  return true;
}

bool optiga_pin_set(optiga_ui_progress_t ui_progress,
                    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  return true;
}

optiga_pin_result optiga_pin_verify_v4(
    optiga_ui_progress_t ui_progress,
    const uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE],
    uint8_t out_secret[OPTIGA_PIN_SECRET_SIZE]) {
  memcpy(out_secret, pin_secret, OPTIGA_PIN_SECRET_SIZE);
  return OPTIGA_PIN_SUCCESS;
}

optiga_pin_result optiga_pin_verify(
    optiga_ui_progress_t ui_progress,
    uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  return OPTIGA_PIN_SUCCESS;
}

bool optiga_pin_get_rem_v4(uint32_t *ctr) {
  *ctr = PIN_MAX_TRIES;
  return true;
}

bool optiga_pin_get_rem(uint32_t *ctr) {
  *ctr = PIN_MAX_TRIES;
  return true;
}

bool optiga_pin_decrease_rem_v4(uint32_t count) { return true; }

bool optiga_pin_decrease_rem(uint32_t count) { return true; }
