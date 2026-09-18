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
#include <stddef.h>
#include <stdint.h>

// Hybrid signature scheme combining SPHINCS+ sha2-128s and Ed25519. The
// Ed25519 part signs SHA-256 of the message and the SPHINCS+ signature, so
// the SPHINCS+ signature is verified only after it has been authenticated by
// Ed25519. This is a simplified version of the boot header signature scheme
// intended for testing purposes only.

#define SLH_ED25519_PRIVATE_KEY_SIZE 32  // the private key is a seed
#define SLH_ED25519_PUBLIC_KEY_SIZE 64   // SPHINCS+ (32) || Ed25519 (32)
#define SLH_ED25519_SIGNATURE_SIZE 7920  // SPHINCS+ (7856) || Ed25519 (64)

/**
 * @brief Generates a hybrid key pair.
 *
 * @param[out] private_key Generated private (signing) key.
 * @param[out] public_key  Generated public (verifying) key.
 * @return true on success.
 */
bool slh_ed25519_generate_key_pair(
    uint8_t private_key[SLH_ED25519_PRIVATE_KEY_SIZE],
    uint8_t public_key[SLH_ED25519_PUBLIC_KEY_SIZE]);

/**
 * @brief Derives the public key from the given private key.
 *
 * @param[in]  private_key Input private (signing) key.
 * @param[out] public_key  Derived public (verifying) key.
 * @return true on success.
 */
bool slh_ed25519_derive_public_key(
    const uint8_t private_key[SLH_ED25519_PRIVATE_KEY_SIZE],
    uint8_t public_key[SLH_ED25519_PUBLIC_KEY_SIZE]);

/**
 * @brief Signs the given message with the given private key.
 *
 * The signature is randomized, signing the same message twice produces
 * different signatures.
 *
 * @param[in]  private_key Signer's private (signing) key.
 * @param[in]  message     Message to sign.
 * @param[in]  message_size Size of the message in bytes.
 * @param[out] signature   Generated signature.
 * @return true on success.
 */
bool slh_ed25519_sign(const uint8_t private_key[SLH_ED25519_PRIVATE_KEY_SIZE],
                      const uint8_t *message, size_t message_size,
                      uint8_t signature[SLH_ED25519_SIGNATURE_SIZE]);

/**
 * @brief Verifies the given signature of the given message.
 *
 * Both the SPHINCS+ and the Ed25519 part of the signature must be valid.
 *
 * @param[in] public_key  Signer's public (verifying) key.
 * @param[in] message     Signed message.
 * @param[in] message_size Size of the message in bytes.
 * @param[in] signature   Input signature.
 * @return true if the signature is valid.
 */
bool slh_ed25519_verify(const uint8_t public_key[SLH_ED25519_PUBLIC_KEY_SIZE],
                        const uint8_t *message, size_t message_size,
                        const uint8_t signature[SLH_ED25519_SIGNATURE_SIZE]);

/**
 * @brief Verifies the given 2-of-2 multisignature of the given message.
 *
 * The public keys must be distinct and each signature must be a valid
 * signature of the message by the public key with the same index.
 *
 * @param[in] public_key1 First signer's public (verifying) key.
 * @param[in] public_key2 Second signer's public (verifying) key.
 * @param[in] message     Signed message.
 * @param[in] message_size Size of the message in bytes.
 * @param[in] signature1  First signer's signature.
 * @param[in] signature2  Second signer's signature.
 * @return true if both signatures are valid.
 */
bool slh_ed25519_verify_2of2(
    const uint8_t public_key1[SLH_ED25519_PUBLIC_KEY_SIZE],
    const uint8_t public_key2[SLH_ED25519_PUBLIC_KEY_SIZE],
    const uint8_t *message, size_t message_size,
    const uint8_t signature1[SLH_ED25519_SIGNATURE_SIZE],
    const uint8_t signature2[SLH_ED25519_SIGNATURE_SIZE]);
