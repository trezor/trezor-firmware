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

#ifndef __UNIX_DRBG_H__
#define __UNIX_DRBG_H__

#include <stddef.h>
#include <stdint.h>

#include "assert.h"
#include "chacha_drbg.h"

#define DRBG_INIT_ENTROPY_LENGTH 50
_Static_assert(CHACHA_DRBG_DERIVATION_FUNCTION_BLOCK_LENGTH -
                       CHACHA_DRBG_DERIVATION_FUNCTION_PREFIX_LENGTH -
                       CHACHA_DRBG_DERIVATION_FUNCTION_PADDING ==
                   DRBG_INIT_ENTROPY_LENGTH,
               "");
// Make sure entropy in chacha_drbg derivation function fills exactly one block
// of hashing function. This is not needed it's just an optimalization.

#define DRBG_RESEED_ENTROPY_LENGTH 50
_Static_assert(CHACHA_DRBG_DERIVATION_FUNCTION_BLOCK_LENGTH -
                       CHACHA_DRBG_DERIVATION_FUNCTION_PREFIX_LENGTH -
                       CHACHA_DRBG_DERIVATION_FUNCTION_PADDING ==
                   DRBG_RESEED_ENTROPY_LENGTH,
               "");

#define DRBG_RESEED_INTERVAL_CALLS 1024

void drbg_init();
void drbg_set_seed(uint32_t seed);
void drbg_reseed();
void drbg_generate(uint8_t *buffer, size_t length);
uint32_t drbg_random32(void);
#endif
