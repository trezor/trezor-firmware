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

#pragma once

#include <trezor_types.h>

#ifdef SECURE_MODE

#include <trezor_model.h>
#include <trezor_rtl.h>

#ifndef SECRET_PRIVILEGED_MASTER_KEY_SLOT

#define KEY_INDEX_DELEGATED_IDENTITY 1

#endif  // SECRET_PRIVILEGED_MASTER_KEY_SLOT

secbool secret_key_derive_sym(uint8_t slot, uint16_t index, uint16_t subindex,
                              uint8_t dest[SHA256_DIGEST_LENGTH]);

secbool secret_key_derive_nist256p1(uint8_t slot, uint16_t index,
                                    uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]);

#define MASTER_KEY_MAX_SIZE 32

typedef struct {
  size_t size;
  uint8_t bytes[MASTER_KEY_MAX_SIZE];
} master_key_t;

/**
 * Retrieves the generated buffer with the master key.
 *
 * If master key has not yet been generated for the device,
 * it is generated now.
 *
 * This key is used to derive additional credential keys (e.g. Evolu).
 *
 * @param master_key structure filled with the generated data.
 */
secbool master_key_get(master_key_t* master_key);

#endif  // SECURE_MODE
