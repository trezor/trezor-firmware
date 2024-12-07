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

#ifndef TREZORHAL_OPTIGA_H
#define TREZORHAL_OPTIGA_H

#include <trezor_types.h>

#include "optiga_common.h"
#include "storage.h"

#define OPTIGA_DEVICE_CERT_INDEX 1
#define OPTIGA_DEVICE_ECC_KEY_INDEX 0

typedef enum _optiga_pin_result {
  OPTIGA_PIN_SUCCESS = 0,       // The operation completed successfully.
  OPTIGA_PIN_INVALID,           // The PIN is invalid.
  OPTIGA_PIN_COUNTER_EXCEEDED,  // The PIN try counter limit was exceeded.
  OPTIGA_PIN_ERROR,             // Optiga processing or communication error.
} optiga_pin_result;

typedef enum _optiga_sign_result {
  OPTIGA_SIGN_SUCCESS = 0,   // The operation completed successfully.
  OPTIGA_SIGN_INACCESSIBLE,  // The signing key is inaccessible.
  OPTIGA_SIGN_ERROR,         // Invalid parameters or Optiga processing or
                             // communication error.
} optiga_sign_result;

// Size of secrets used in PIN processing, e.g. salted PIN, master secret etc.
#define OPTIGA_PIN_SECRET_SIZE 32

optiga_sign_result __wur optiga_sign(uint8_t index, const uint8_t *digest,
                                     size_t digest_size, uint8_t *signature,
                                     size_t max_sig_size, size_t *sig_size);

bool __wur optiga_cert_size(uint8_t index, size_t *cert_size);

bool __wur optiga_read_cert(uint8_t index, uint8_t *cert, size_t max_cert_size,
                            size_t *cert_size);

bool __wur optiga_read_sec(uint8_t *sec);

void optiga_set_sec_max(void);

bool __wur optiga_random_buffer(uint8_t *dest, size_t size);

bool __wur optiga_pin_set(optiga_ui_progress_t ui_progress,
                          uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]);

uint32_t optiga_estimate_time_ms(storage_pin_op_t op);

optiga_pin_result __wur
optiga_pin_verify(optiga_ui_progress_t ui_progress,
                  uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]);

optiga_pin_result __wur
optiga_pin_verify_v4(optiga_ui_progress_t ui_progress,
                     const uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE],
                     uint8_t out_secret[OPTIGA_PIN_SECRET_SIZE]);

bool __wur optiga_pin_get_rem_v4(uint32_t *ctr);

bool __wur optiga_pin_get_rem(uint32_t *ctr);

bool __wur optiga_pin_decrease_rem_v4(uint32_t count);

bool __wur optiga_pin_decrease_rem(uint32_t count);

#endif
