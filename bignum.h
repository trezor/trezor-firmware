/**
 * Copyright (c) 2013 Tomas Dzetkulic
 * Copyright (c) 2013 Pavol Rusnak
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

#ifndef __BIGNUM_H__
#define __BIGNUM_H__

#include <stdint.h>

// use precomputed Inverse Values of powers of two
#ifndef USE_PRECOMPUTED_IV
#define USE_PRECOMPUTED_IV 1
#endif

// use precomputed Curve Points (some scalar multiples of curve base point G)
#ifndef USE_PRECOMPUTED_CP
#define USE_PRECOMPUTED_CP 1
#endif

// use fast inverse method
#ifndef USE_INVERSE_FAST
#define USE_INVERSE_FAST 1
#endif

// bignum256 are 256 bits stored as 8*30 bit + 1*16 bit
// val[0] are lowest 30 bits, val[8] highest 16 bits
typedef struct {
	uint32_t val[9];
} bignum256;

// read 4 big endian bytes into uint32
uint32_t read_be(const uint8_t *data);

// write 4 big endian bytes
void write_be(uint8_t *data, uint32_t x);

void bn_read_be(const uint8_t *in_number, bignum256 *out_number);

void bn_write_be(const bignum256 *in_number, uint8_t *out_number);

void bn_zero(bignum256 *a);

int bn_is_zero(const bignum256 *a);

int bn_is_less(const bignum256 *a, const bignum256 *b);

int bn_is_equal(const bignum256 *a, const bignum256 *b);

int bn_bitlen(const bignum256 *a);

void bn_lshift(bignum256 *a);

void bn_rshift(bignum256 *a);

void bn_mod(bignum256 *x, const bignum256 *prime);

void bn_addi(bignum256 *a, uint32_t b);

void bn_muli(bignum256 *a, uint32_t b);

void bn_multiply(const bignum256 *k, bignum256 *x, const bignum256 *prime);

void bn_fast_mod(bignum256 *x, const bignum256 *prime);

void bn_sqrt(bignum256 *x, const bignum256 *prime);

void bn_inverse(bignum256 *x, const bignum256 *prime);

void bn_normalize(bignum256 *a);

void bn_addmod(bignum256 *a, const bignum256 *b, const bignum256 *prime);

void bn_addmodi(bignum256 *a, uint32_t b, const bignum256 *prime);

void bn_substract(const bignum256 *a, const bignum256 *b, bignum256 *res);

void bn_substract_noprime(const bignum256 *a, const bignum256 *b, bignum256 *res);

void bn_divmod58(bignum256 *a, uint32_t *r);

#ifndef BN_PRINT
#define BN_PRINT 0
#endif

#if BN_PRINT
void bn_print(const bignum256 *a);
void bn_print_raw(const bignum256 *a);
#endif

#endif
