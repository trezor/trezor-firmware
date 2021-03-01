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

#ifndef __CHACHA_DRBG__
#define __CHACHA_DRBG__

#include "chacha20poly1305/chacha20poly1305.h"
#include "sha2.h"

// A very fast deterministic random bit generator based on CTR_DRBG in NIST SP
// 800-90A. Chacha is used instead of a block cipher in the counter mode, SHA256
// is used as a derivation function. The highest supported security strength is
// at least 256 bits. Reseeding is left up to caller.

#define CHACHA_DRBG_DERIVATION_FUNCTION_PREFIX_LENGTH (1 + 4)
// 1 = sizeof(counter), 4 = sizeof(output_length) in derivation_function
#define CHACHA_DRBG_DERIVATION_FUNCTION_PADDING 9
// padding in SHA256
#define CHACHA_DRBG_DERIVATION_FUNCTION_BLOCK_LENGTH SHA256_BLOCK_LENGTH

typedef struct _CHACHA_DRBG_CTX {
  ECRYPT_ctx chacha_ctx;
  uint32_t reseed_counter;
} CHACHA_DRBG_CTX;

void chacha_drbg_init(CHACHA_DRBG_CTX *ctx, const uint8_t *entropy,
                      size_t entropy_length, const uint8_t *nonce,
                      size_t nonce_length);
void chacha_drbg_generate(CHACHA_DRBG_CTX *ctx, uint8_t *output,
                          size_t output_length);
void chacha_drbg_reseed(CHACHA_DRBG_CTX *ctx, const uint8_t *entropy,
                        size_t entropy_length, const uint8_t *additional_input,
                        size_t additional_input_length);
#endif  // __CHACHA_DRBG__
