/**
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

#ifndef __OPTIONS_H__
#define __OPTIONS_H__

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

// support for printing bignum256 structures via printf
#ifndef USE_BN_PRINT
#define USE_BN_PRINT 0
#endif

// use deterministic signatures
#ifndef USE_RFC6979
#define USE_RFC6979 1
#endif

// check public key for validity
#ifndef USE_PUBKEY_VALIDATE
#define USE_PUBKEY_VALIDATE 1
#endif

#endif
