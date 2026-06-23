/**
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

#ifndef __NOISE_INTERNAL_H__
#define __NOISE_INTERNAL_H__

#include "noise_common.h"

#include "sha2.h"

// Internal building blocks used by all implemented noise patterns.

bool noise_internal_encrypt(const uint8_t key[NOISE_KEY_SIZE],
                            const uint8_t nonce[NOISE_NONCE_SIZE],
                            const uint8_t *associated_data,
                            size_t associated_data_length,
                            const uint8_t *plaintext, size_t plaintext_length,
                            uint8_t *ciphertext);

bool noise_internal_decrypt(const uint8_t key[NOISE_KEY_SIZE],
                            const uint8_t nonce[NOISE_NONCE_SIZE],
                            const uint8_t *associated_data,
                            size_t associated_data_length,
                            const uint8_t *ciphertext, size_t ciphertext_length,
                            uint8_t *plaintext);

void noise_internal_mix_hash(uint8_t hash[SHA256_DIGEST_LENGTH],
                             const uint8_t *data, size_t data_length);

void noise_internal_mix_key(uint8_t chaining_key[SHA256_DIGEST_LENGTH],
                            curve25519_key input_key,
                            uint8_t output_key[NOISE_KEY_SIZE]);

void noise_internal_split(uint8_t chaining_key[SHA256_DIGEST_LENGTH],
                          uint8_t output1[NOISE_KEY_SIZE],
                          uint8_t output2[NOISE_KEY_SIZE]);

#endif  // __NOISE_INTERNAL_H__
