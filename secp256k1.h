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

#ifndef __SECP256K1_H__
#define __SECP256K1_H__

#include <stdint.h>

#include "bignum.h"

// curve point x and y
typedef struct {
	bignum256 x, y;
} curve_point;

// secp256k1 prime
extern const bignum256 prime256k1;

// secp256k1 initial curve point
extern const curve_point G256k1;

// secp256k1 order of G
extern const bignum256 order256k1;

// secp256k1 order of G / 2
extern const bignum256 order256k1_half;

// 3/2 in G_p
extern const bignum256 three_over_two256k1;

#if USE_PRECOMPUTED_IV
extern const bignum256 secp256k1_iv[256];
#endif

#if USE_PRECOMPUTED_CP
extern const curve_point secp256k1_cp[256];
extern const curve_point secp256k1_cp2[255];
#endif

#endif
