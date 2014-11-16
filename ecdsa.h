/**
 * Copyright (c) 2013-2014 Tomas Dzetkulic
 * Copyright (c) 2013-2014 Pavol Rusnak
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

#ifndef __ECDSA_H__
#define __ECDSA_H__

#include <stdint.h>
#include "options.h"
#include "secp256k1.h"

void point_copy(const curve_point *cp1, curve_point *cp2);
void point_add(const curve_point *cp1, curve_point *cp2);
void point_double(curve_point *cp);
void point_multiply(const bignum256 *k, const curve_point *p, curve_point *res);
void point_set_infinity(curve_point *p);
int point_is_infinity(const curve_point *p);
int point_is_equal(const curve_point *p, const curve_point *q);
int point_is_negative_of(const curve_point *p, const curve_point *q);
void scalar_multiply(const bignum256 *k, curve_point *res);
void uncompress_coords(uint8_t odd, const bignum256 *x, bignum256 *y);

int ecdsa_sign(const uint8_t *priv_key, const uint8_t *msg, uint32_t msg_len, uint8_t *sig);
int ecdsa_sign_double(const uint8_t *priv_key, const uint8_t *msg, uint32_t msg_len, uint8_t *sig);
int ecdsa_sign_digest(const uint8_t *priv_key, const uint8_t *digest, uint8_t *sig);
void ecdsa_get_public_key33(const uint8_t *priv_key, uint8_t *pub_key);
void ecdsa_get_public_key65(const uint8_t *priv_key, uint8_t *pub_key);
void ecdsa_get_pubkeyhash(const uint8_t *pub_key, uint8_t *pubkeyhash);
void ecdsa_get_address_raw(const uint8_t *pub_key, uint8_t version, uint8_t *addr_raw);
void ecdsa_get_address(const uint8_t *pub_key, uint8_t version, char *addr);
void ecdsa_get_wif(const uint8_t *priv_key, uint8_t version, char *wif);
int ecdsa_address_decode(const char *addr, uint8_t *out);
int ecdsa_read_pubkey(const uint8_t *pub_key, curve_point *pub);
int ecdsa_validate_pubkey(const curve_point *pub);
int ecdsa_verify(const uint8_t *pub_key, const uint8_t *sig, const uint8_t *msg, uint32_t msg_len);
int ecdsa_verify_double(const uint8_t *pub_key, const uint8_t *sig, const uint8_t *msg, uint32_t msg_len);
int ecdsa_verify_digest(const uint8_t *pub_key, const uint8_t *sig, const uint8_t *digest);
int ecdsa_sig_to_der(const uint8_t *sig, uint8_t *der);

#endif
