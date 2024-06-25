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

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "optiga_common.h"
#include "secbool.h"

#define OPTIGA_DEVICE_CERT_INDEX 1
#define OPTIGA_DEVICE_ECC_KEY_INDEX 0
#define OPTIGA_COMMAND_ERROR_OFFSET 0x100

// Error code 0x07: Access conditions not satisfied
#define OPTIGA_ERR_ACCESS_COND_NOT_SAT (OPTIGA_COMMAND_ERROR_OFFSET + 0x07)

// Error code 0x0E: Counter threshold limit exceeded
#define OPTIGA_ERR_COUNTER_EXCEEDED (OPTIGA_COMMAND_ERROR_OFFSET + 0x0E)

// Error code 0x2F: Authorization failure
#define OPTIGA_ERR_AUTH_FAIL (OPTIGA_COMMAND_ERROR_OFFSET + 0x2F)

// Size of secrets used in PIN processing, e.g. salted PIN, master secret etc.
#define OPTIGA_PIN_SECRET_SIZE 32

// The number of milliseconds it takes to execute optiga_pin_set().
#define OPTIGA_PIN_SET_MS 1300

// The number of milliseconds it takes to execute optiga_pin_verify().
#define OPTIGA_PIN_VERIFY_MS 900

typedef secbool (*OPTIGA_UI_PROGRESS)(uint32_t elapsed_ms);

int __wur optiga_sign(uint8_t index, const uint8_t *digest, size_t digest_size,
                      uint8_t *signature, size_t max_sig_size,
                      size_t *sig_size);

bool __wur optiga_cert_size(uint8_t index, size_t *cert_size);

bool __wur optiga_read_cert(uint8_t index, uint8_t *cert, size_t max_cert_size,
                            size_t *cert_size);

bool __wur optiga_read_sec(uint8_t *sec);

bool __wur optiga_random_buffer(uint8_t *dest, size_t size);

int __wur optiga_pin_set(OPTIGA_UI_PROGRESS ui_progress,
                         uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]);

int __wur optiga_pin_verify(OPTIGA_UI_PROGRESS ui_progress,
                            uint8_t stretched_pin[OPTIGA_PIN_SECRET_SIZE]);

int __wur optiga_pin_verify_v4(OPTIGA_UI_PROGRESS ui_progress,
                               const uint8_t pin_secret[OPTIGA_PIN_SECRET_SIZE],
                               uint8_t out_secret[OPTIGA_PIN_SECRET_SIZE]);

int __wur optiga_pin_get_fails_v4(uint32_t *ctr);

int __wur optiga_pin_get_fails(uint32_t *ctr);

int __wur optiga_pin_fails_increase_v4(uint32_t count);

int __wur optiga_pin_fails_increase(uint32_t count);

#endif
