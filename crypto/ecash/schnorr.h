/**
 * Copyright (c) 2021 The Bitcoin ABC developers
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

#ifndef TREZOR_CRYPTO_ECASH_SCHNORR_H
#define TREZOR_CRYPTO_ECASH_SCHNORR_H

#if !USE_ECASH
#error "Compile with -DUSE_ECASH=1"
#endif

#include "ecdsa.h"

/* A Schnorr signature is always 64 bytes */
#define SCHNORR_SIG_LENGTH 64

// sign/verify returns 0 if operation succeeded
int schnorr_sign_digest(const ecdsa_curve *curve, const uint8_t *priv_key,
                        const uint8_t *digest, uint8_t *result);
int schnorr_verify_digest(const ecdsa_curve *curve, const uint8_t *pub_key,
                          const uint8_t *msg_hash, const uint8_t *sign);
#endif
