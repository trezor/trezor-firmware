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

/**
 * Initializes the entropy module.
 * If entropy has not yet been generated for the device, it is generated now.
 */
void entropy_init(void);

#endif  // SECURE_MODE

/**
 * Maximum size of generated entropy (minimum is 32 bytes).
 * Newer devices derive entropy from the master key - 32 bytes.
 * Older devices derive entropy from CPUID and OTP - 32 + 12 bytes.
 */
#define ENTROPY_MAX_SIZE (32 + 12)

typedef struct {
  /** Number of valid bytes in the bytes array */
  size_t size;
  /** Generated entropy bytes */
  uint8_t bytes[ENTROPY_MAX_SIZE];
} entropy_data_t;

/**
 * Retrieves the generated entropy buffer.
 * @param entropy structure filled with the generated data.
 */
void entropy_get(entropy_data_t* entropy);
