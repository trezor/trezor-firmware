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

#include "optiga.h"
#include <string.h>
#include "ecdsa.h"
#include "nist256p1.h"
#include "optiga_common.h"
#include "rand.h"

#if defined(TREZOR_MODEL_R)
#include "certs/T2B1.h"
#define DEVICE_CERT_CHAIN T2B1_der
#elif defined(TREZOR_MODEL_T3T1)
#include "certs/T3T1.h"
#define DEVICE_CERT_CHAIN T3T1_der
#else
#error "Cert chain for specified model is not available."
#endif

int optiga_sign(uint8_t index, const uint8_t *digest, size_t digest_size,
                uint8_t *signature, size_t max_sig_size, size_t *sig_size) {
  const uint8_t DEVICE_PRIV_KEY[32] = {1};

  if (index != OPTIGA_DEVICE_ECC_KEY_INDEX) {
    return false;
  }

  if (max_sig_size < 72) {
    return OPTIGA_ERR_SIZE;
  }

  uint8_t raw_signature[64] = {0};
  int ret = ecdsa_sign_digest(&nist256p1, DEVICE_PRIV_KEY, digest,
                              raw_signature, NULL, NULL);
  if (ret != 0) {
    return OPTIGA_ERR_CMD;
  }

  *sig_size = ecdsa_sig_to_der(raw_signature, signature);
  return OPTIGA_SUCCESS;
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

bool optiga_random_buffer(uint8_t *dest, size_t size) {
  random_buffer(dest, size);
  return true;
}

int optiga_pin_set(OPTIGA_UI_PROGRESS ui_progress,
                   uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  ui_progress(OPTIGA_PIN_SET_MS);
  return OPTIGA_SUCCESS;
}

int optiga_pin_verify_v4(OPTIGA_UI_PROGRESS ui_progress,
                         const uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE],
                         uint8_t out_secret[OPTIGA_PIN_SECRET_SIZE]) {
  memcpy(out_secret, pin_secret, OPTIGA_PIN_SECRET_SIZE);
  ui_progress(OPTIGA_PIN_VERIFY_MS);
  return OPTIGA_SUCCESS;
}

int optiga_pin_verify(OPTIGA_UI_PROGRESS ui_progress,
                      uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]) {
  ui_progress(OPTIGA_PIN_VERIFY_MS);
  return OPTIGA_SUCCESS;
}

int optiga_pin_get_fails_v4(uint32_t *ctr) {
  *ctr = 0;
  return OPTIGA_SUCCESS;
}

int optiga_pin_get_fails(uint32_t *ctr) {
  *ctr = 0;
  return OPTIGA_SUCCESS;
}

int optiga_pin_fails_increase_v4(uint32_t count) { return OPTIGA_SUCCESS; }

int optiga_pin_fails_increase(uint32_t count) { return OPTIGA_SUCCESS; }
