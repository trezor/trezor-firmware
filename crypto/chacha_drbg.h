/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#ifndef __CHACHA_DRBG__
#define __CHACHA_DRBG__

#include "chacha20poly1305/chacha20poly1305.h"
#include "sha2.h"

// A very fast deterministic random bit generator based on CTR_DRBG in NIST SP
// 800-90A. Chacha is used instead of a block cipher in the counter mode, SHA256
// is used as a derivation function. The highest supported security strength is
// at least 256 bits. Reseeding is left up to caller.

// Length of inputs of chacha_drbg_init (entropy and nonce) or
// chacha_drbg_reseed (entropy and additional_input) that fill exactly
// block_count blocks of hash function in derivation_function. There is no need
// the input to have this length, it's just an optimalization.
#define CHACHA_DRBG_OPTIMAL_RESEED_LENGTH(block_count) \
  ((block_count) * SHA256_BLOCK_LENGTH - 1 - 4 - 9)
// 1 = sizeof(counter), 4 = sizeof(output_length) in
// derivation_function, 9 is length of SHA256 padding of message
// aligned to bytes

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
