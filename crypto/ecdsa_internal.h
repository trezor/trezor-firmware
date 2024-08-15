/**
 * Copyright (c) 2022 SatoshiLabs
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

#ifndef __ECDSA_INTERNAL_H__
#define __ECDSA_INTERNAL_H__

#include <stdint.h>
#include "ecdsa.h"

// trezor-crypto native implementations
int tc_ecdsa_get_public_key33(const ecdsa_curve *curve, const uint8_t *priv_key,
                              uint8_t *pub_key);
int tc_ecdsa_get_public_key65(const ecdsa_curve *curve, const uint8_t *priv_key,
                              uint8_t *pub_key);
int tc_ecdsa_sign_digest(const ecdsa_curve *curve, const uint8_t *priv_key,
                         const uint8_t *digest, uint8_t *sig, uint8_t *pby,
                         int (*is_canonical)(uint8_t by, uint8_t sig[64]));
int tc_ecdsa_verify_digest(const ecdsa_curve *curve, const uint8_t *pub_key,
                           const uint8_t *sig, const uint8_t *digest);
int tc_ecdsa_recover_pub_from_sig(const ecdsa_curve *curve, uint8_t *pub_key,
                                  const uint8_t *sig, const uint8_t *digest,
                                  int recid);
int tc_ecdh_multiply(const ecdsa_curve *curve, const uint8_t *priv_key,
                     const uint8_t *pub_key, uint8_t *session_key);
ecdsa_tweak_pubkey_result tc_ecdsa_tweak_pubkey(
    const ecdsa_curve *curve, const uint8_t *public_key_bytes,
    const uint8_t *tweak_bytes, uint8_t *tweaked_public_key_bytes);
#endif
