/**
 * Copyright (c) 2016 Jochen Hoenicke
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

#include "curves.h"

const char SECP256K1_NAME[] = "secp256k1";
const char SECP256K1_DECRED_NAME[] = "secp256k1-decred";
const char SECP256K1_GROESTL_NAME[] = "secp256k1-groestl";
const char SECP256K1_SMART_NAME[] = "secp256k1-smart";
const char NIST256P1_NAME[] = "nist256p1";
const char ED25519_NAME[] = "ed25519";
const char ED25519_SEED_NAME[] = "ed25519 seed";
#if USE_CARDANO
const char ED25519_CARDANO_NAME[] = "ed25519 cardano seed";
#endif
const char ED25519_SHA3_NAME[] = "ed25519-sha3";
#if USE_KECCAK
const char ED25519_KECCAK_NAME[] = "ed25519-keccak";
#endif
const char CURVE25519_NAME[] = "curve25519";
