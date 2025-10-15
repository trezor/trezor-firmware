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

/**
 * Maximum size of generated salt (minimum is 32 bytes).
 * Newer devices derive salt from the master key - 32 bytes.
 * Older devices derive salt from CPUID and OTP - 32 + 12 bytes.
 */
#define STORAGE_SALT_MAX_SIZE (32 + 12)

typedef struct {
  /** Number of valid bytes in the bytes array */
  size_t size;
  /** Generated salt bytes */
  uint8_t bytes[STORAGE_SALT_MAX_SIZE];
} storage_salt_t;

/**
 * Retrieves the generated buffer with storage salt.
 *
 * If storage salt has not yet been generated for the device, it is
 * generated now.
 *
 * @param salt structure filled with the generated data.
 */
void storage_salt_get(storage_salt_t* salt);
