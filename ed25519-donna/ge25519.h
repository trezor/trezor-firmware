//
// Created by Dusan Klinec on 29/04/2018.
//

#ifndef GE25519_H
#define GE25519_H

#include <stdint.h>
#include "ed25519-donna.h"

/* uint32_t to Zmod(2^255-19) */
void curve25519_set(bignum25519 r, uint32_t x);

/* set d */
void curve25519_set_d(bignum25519 r);

/* set 2d */
void curve25519_set_2d(bignum25519 r);

/* set sqrt(-1) */
void curve25519_set_sqrtneg1(bignum25519 r);

/* constant time Zmod(2^255-19) negative test */
int curve25519_isnegative(const bignum25519 f);

/* constant time Zmod(2^255-19) non-zero test */
int curve25519_isnonzero(const bignum25519 f);

/* reduce Zmod(2^255-19) */
void curve25519_reduce(bignum25519 r, const bignum25519 in);

/* Zmod(2^255-19) from byte array to bignum25519 expansion with modular reduction */
void curve25519_expand_reduce(bignum25519 out, const unsigned char in[32]);

/* check if r is on curve */
int ge25519_check(const ge25519 *r);

/* a == b */
int ge25519_eq(const ge25519 *a, const ge25519 *b);

/* copies one point to another */
void ge25519_copy(ge25519 *dst, const ge25519 *src);

/* sets B point to r */
void ge25519_set_base(ge25519 *r);

/* 8*P */
void ge25519_mul8(ge25519 *r, const ge25519 *t);

/* -P */
void ge25519_neg_partial(ge25519 *r);

/* -P */
void ge25519_neg_full(ge25519 *r);

/* reduce all coords */
void ge25519_reduce(ge25519 *r, const ge25519 *t);

/* normalizes coords. (x, y, 1, x*y) */
void ge25519_norm(ge25519 *r, const ge25519 * t);

/* Simple addition */
void ge25519_add(ge25519 *r, const ge25519 *a, const ge25519 *b, unsigned char signbit);

/* point from bytes, used in H_p() */
void ge25519_fromfe_frombytes_vartime(ge25519 *r, const unsigned char *s);

/* point from bytes */
int ge25519_unpack_vartime(ge25519 *r, const unsigned char *s);

/* aG, wrapper for niels base mult. */
void ge25519_scalarmult_base_wrapper(ge25519 *r, const bignum256modm s);

/* aP, wrapper. General purpose, normalizes after multiplication */
void ge25519_scalarmult_wrapper(ge25519 *r, const ge25519 *P, const bignum256modm a);

#endif
