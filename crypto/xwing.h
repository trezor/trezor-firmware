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

// X-Wing hybrid KEM combining ML-KEM-768 and X25519, as specified by
// draft-connolly-cfrg-xwing-kem-10.

#define XWING_PRIVATE_KEY_SIZE 32         // the private key is a seed
#define XWING_PUBLIC_KEY_SIZE 1216        // ML-KEM-768 (1184) || X25519 (32)
#define XWING_CIPHERTEXT_SIZE 1120        // ML-KEM-768 (1088) || X25519 (32)
#define XWING_ENCAPSULATION_SEED_SIZE 64  // ML-KEM m (32) || X25519 (32)
#define XWING_SHARED_SECRET_SIZE 32

/**
 * @brief Generates an X-Wing key pair.
 *
 * @param[out] private_key Generated private (decapsulation) key.
 * @param[out] public_key  Generated public (encapsulation) key.
 * @return true on success.
 */
bool xwing_generate_key_pair(uint8_t private_key[XWING_PRIVATE_KEY_SIZE],
                             uint8_t public_key[XWING_PUBLIC_KEY_SIZE]);

/**
 * @brief Derives the public key from the given private key.
 *
 * @param[in]  private_key Input private (decapsulation) key.
 * @param[out] public_key  Derived public (encapsulation) key.
 * @return true on success.
 */
bool xwing_derive_public_key(const uint8_t private_key[XWING_PRIVATE_KEY_SIZE],
                             uint8_t public_key[XWING_PUBLIC_KEY_SIZE]);

/**
 * @brief Generates a shared secret and a ciphertext for the given public key.
 *
 * @param[in]  public_key    Recipient's public (encapsulation) key.
 * @param[out] ciphertext    Generated ciphertext.
 * @param[out] shared_secret Generated shared secret.
 * @return true on success, false if the public key is invalid.
 */
bool xwing_encapsulate(const uint8_t public_key[XWING_PUBLIC_KEY_SIZE],
                       uint8_t ciphertext[XWING_CIPHERTEXT_SIZE],
                       uint8_t shared_secret[XWING_SHARED_SECRET_SIZE]);

/**
 * @brief Derives a shared secret and a ciphertext from the given seed for the
 * given public key.
 *
 * @param[in]  seed          Input randomness.
 * @param[in]  public_key    Recipient's public (encapsulation) key.
 * @param[out] ciphertext    Derived ciphertext.
 * @param[out] shared_secret Derived shared secret.
 * @return true on success, false if the public key is invalid.
 */
bool xwing_encapsulate_from_seed(
    const uint8_t seed[XWING_ENCAPSULATION_SEED_SIZE],
    const uint8_t public_key[XWING_PUBLIC_KEY_SIZE],
    uint8_t ciphertext[XWING_CIPHERTEXT_SIZE],
    uint8_t shared_secret[XWING_SHARED_SECRET_SIZE]);

/**
 * @brief Computes the shared secret for the given ciphertext and private key.
 *
 * If the ciphertext is not the encapsulation of the returned shared secret, a
 * pseudorandom shared secret is returned (implicit rejection by the ML-KEM
 * part).
 *
 * @param[in]  private_key   Recipient's private (decapsulation) key.
 * @param[in]  ciphertext    Input ciphertext.
 * @param[out] shared_secret Computed shared secret.
 * @return true on success.
 */
bool xwing_decapsulate(const uint8_t private_key[XWING_PRIVATE_KEY_SIZE],
                       const uint8_t ciphertext[XWING_CIPHERTEXT_SIZE],
                       uint8_t shared_secret[XWING_SHARED_SECRET_SIZE]);
