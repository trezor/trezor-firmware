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

#pragma once

#include <stdbool.h>
#include <stdint.h>

// ML-KEM-768 (FIPS 203), implemented by the vendored mlkem-native library.

#define MLKEM768_PUBLIC_KEY_SIZE 1184
#define MLKEM768_PRIVATE_KEY_SIZE 2400
#define MLKEM768_KEY_PAIR_SEED_SIZE 64  // d (32 bytes) || z (32 bytes)
#define MLKEM768_CIPHERTEXT_SIZE 1088
#define MLKEM768_ENCAPSULATION_SEED_SIZE 32  // m
#define MLKEM768_SHARED_SECRET_SIZE 32

/**
 * @brief Generates an ML-KEM-768 key pair.
 *
 * Implements ML-KEM.KeyGen from FIPS 203, Algorithm 19.
 *
 * @param[out] private_key Generated private (decapsulation) key.
 * @param[out] public_key  Generated public (encapsulation) key.
 * @return true on success.
 */
bool mlkem768_generate_key_pair(
    uint8_t private_key[MLKEM768_PRIVATE_KEY_SIZE],
    uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE]);

/**
 * @brief Derives an ML-KEM-768 key pair from the given seed.
 *
 * Implements ML-KEM.KeyGen_internal from FIPS 203, Algorithm 16.
 *
 * @param[in]  seed        Input randomness d || z.
 * @param[out] private_key Derived private (decapsulation) key.
 * @param[out] public_key  Derived public (encapsulation) key.
 * @return true on success.
 */
bool mlkem768_generate_key_pair_from_seed(
    const uint8_t seed[MLKEM768_KEY_PAIR_SEED_SIZE],
    uint8_t private_key[MLKEM768_PRIVATE_KEY_SIZE],
    uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE]);

/**
 * @brief Generates a shared secret and a ciphertext for the given public key.
 *
 * Implements ML-KEM.Encaps from FIPS 203, Algorithm 20, including the
 * encapsulation key check from FIPS 203, Section 7.2.
 *
 * @param[in]  public_key    Recipient's public (encapsulation) key.
 * @param[out] ciphertext    Generated ciphertext.
 * @param[out] shared_secret Generated shared secret.
 * @return true on success, false if the public key is invalid.
 */
bool mlkem768_encapsulate(
    const uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE],
    uint8_t ciphertext[MLKEM768_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM768_SHARED_SECRET_SIZE]);

/**
 * @brief Derives a shared secret and a ciphertext from the given seed for the
 * given public key.
 *
 * Implements ML-KEM.Encaps_internal from FIPS 203, Algorithm 17, including
 * the encapsulation key check from FIPS 203, Section 7.2.
 *
 * @param[in]  seed          Input randomness m.
 * @param[in]  public_key    Recipient's public (encapsulation) key.
 * @param[out] ciphertext    Derived ciphertext.
 * @param[out] shared_secret Derived shared secret.
 * @return true on success, false if the public key is invalid.
 */
bool mlkem768_encapsulate_from_seed(
    const uint8_t seed[MLKEM768_ENCAPSULATION_SEED_SIZE],
    const uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE],
    uint8_t ciphertext[MLKEM768_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM768_SHARED_SECRET_SIZE]);

/**
 * @brief Computes the shared secret for the given ciphertext and private key.
 *
 * Implements ML-KEM.Decaps from FIPS 203, Algorithm 21, including the
 * decapsulation key hash check from FIPS 203, Section 7.3. If the ciphertext
 * is not the encapsulation of the returned shared secret, a pseudorandom
 * shared secret is returned (implicit rejection).
 *
 * @param[in]  private_key   Recipient's private (decapsulation) key.
 * @param[in]  ciphertext    Input ciphertext.
 * @param[out] shared_secret Computed shared secret.
 * @return true on success, false if the private key is invalid.
 */
bool mlkem768_decapsulate(
    const uint8_t private_key[MLKEM768_PRIVATE_KEY_SIZE],
    const uint8_t ciphertext[MLKEM768_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM768_SHARED_SECRET_SIZE]);
