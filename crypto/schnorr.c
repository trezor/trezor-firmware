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

#include "schnorr.h"
#include "hmac_drbg.h"
#include "memzero.h"
#include "rfc6979.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static int jacobi(const bignum256 *_n, const bignum256 *_k) {
  assert(!bn_is_zero(_k) && bn_is_odd(_k));

  bignum256 n_copy = {0};
  bignum256 *n = &n_copy;
  bn_copy(_n, n);

  bignum256 k_copy = {0};
  bignum256 *k = &k_copy;
  bn_copy(_k, k);

  int t = 0;
  while (!bn_is_zero(n)) {
    while (bn_is_even(n)) {
      // jacobi(2 * n, k) = jacobi(n, k) if k = 1 (mod 8) or k = 7 (mod 8)
      // jacobi(2 * n, k) = -jacobi(n, k) if k = 3 (mod 8) or k = 5 (mod 8)
      uint32_t r = k->val[0] & 0x07;
      t ^= (r == 3 || r == 5);
      bn_rshift(n);
    }

    if (bn_is_less(n, k)) {
      // jacobi(n, k) = jacobi(k, n) if k = n = 1 (mod 4)
      // jacobi(n, k) = -jacobi(k, n) if k = n = 3 (mod 4)
      t ^= ((n->val[0] & k->val[0] & 3) == 3);
      bignum256 *temp = n;
      n = k;
      k = temp;
    }

    // jacobi(n, k) = jacobi(n - k, k)
    bn_subtract(n, k, n);
  }

  int k_is_one = bn_is_one(k);

  // Cleanup
  memzero(&n_copy, sizeof(n_copy));
  memzero(&k_copy, sizeof(k_copy));

  // Map t: [0] => 1, [1] => -1
  t = -2 * t + 1;

  return k_is_one * t;
}

static int is_non_quad_residue(const bignum256 *n, const bignum256 *prime) {
  return jacobi(n, prime) == -1;
}

static int generate_k_schnorr(const ecdsa_curve *curve, const uint8_t *priv_key,
                              const uint8_t *hash, bignum256 *k) {
  rfc6979_state rng = {0};
  uint8_t hmac_data[SHA256_DIGEST_LENGTH + 16] = {0};

  /*
   * Init the HMAC with additional data specific to Schnorr. This prevents from
   * leaking the private key in the case the same message is signed with both
   * Schnorr and ECDSA.
   */
  memcpy(hmac_data, hash, SHA256_DIGEST_LENGTH);
  memcpy(hmac_data + SHA256_DIGEST_LENGTH, "Schnorr+SHA256  ", 16);
  hmac_drbg_init(&rng, priv_key, 32, hmac_data, SHA256_DIGEST_LENGTH + 16);

  for (int i = 0; i < 10000; i++) {
    generate_k_rfc6979(k, &rng);
    // If k is too big or too small, we don't like it
    if (bn_is_zero(k) || !bn_is_less(k, &curve->order)) {
      continue;
    }

    memzero(&rng, sizeof(rng));
    return 0;
  }

  memzero(&rng, sizeof(rng));
  return 1;
}

// e = H(Rx, pub_key, msg_hash)
static void calc_e(const ecdsa_curve *curve, const bignum256 *Rx,
                   const uint8_t pub_key[33], const uint8_t *msg_hash,
                   bignum256 *e) {
  uint8_t Rxbuf[32] = {0};
  SHA256_CTX ctx = {0};
  uint8_t digest[SHA256_DIGEST_LENGTH] = {0};

  bn_write_be(Rx, Rxbuf);

  sha256_Init(&ctx);
  sha256_Update(&ctx, Rxbuf, sizeof(Rxbuf));
  sha256_Update(&ctx, pub_key, 33);
  sha256_Update(&ctx, msg_hash, SHA256_DIGEST_LENGTH);
  sha256_Final(&ctx, digest);

  bn_read_be(digest, e);
  bn_fast_mod(e, &curve->order);
  bn_mod(e, &curve->order);
}

int schnorr_sign_digest(const ecdsa_curve *curve, const uint8_t *priv_key,
                        const uint8_t *digest, uint8_t *sign) {
  uint8_t pub_key[33] = {0};
  curve_point R = {0};
  bignum256 e = {0}, s = {0}, k = {0};

  if (ecdsa_get_public_key33(curve, priv_key, pub_key) != 0) {
    return 1;
  }

  // Compute k
  if (generate_k_schnorr(curve, priv_key, digest, &k) != 0) {
    memzero(&k, sizeof(k));
    return 1;
  }

  // Compute R = k * G
  scalar_multiply(curve, &k, &R);

  // If R.y is not a quadratic residue, negate the nonce
  bn_cnegate(is_non_quad_residue(&R.y, &curve->prime), &k, &curve->order);

  bn_write_be(&R.x, sign);

  // Compute e = H(Rx, pub_key, msg_hash)
  calc_e(curve, &R.x, pub_key, digest, &e);

  // Compute s = k + e * priv_key
  bn_read_be(priv_key, &s);
  bn_multiply(&e, &s, &curve->order);
  bn_addmod(&s, &k, &curve->order);
  memzero(&k, sizeof(k));
  bn_mod(&s, &curve->order);
  bn_write_be(&s, sign + 32);

  return 0;
}

int schnorr_verify_digest(const ecdsa_curve *curve, const uint8_t *pub_key,
                          const uint8_t *digest, const uint8_t *sign) {
  curve_point P = {0}, sG = {0}, R = {0};
  bignum256 r = {0}, s = {0}, e = {0};

  bn_read_be(sign, &r);
  bn_read_be(sign + 32, &s);

  // Signature is invalid if s >= n or r >= p.
  if (!bn_is_less(&r, &curve->prime) || !bn_is_less(&s, &curve->order)) {
    return 1;
  }

  if (!ecdsa_read_pubkey(curve, pub_key, &P)) {
    return 2;
  }

  // Compute e
  calc_e(curve, &r, pub_key, digest, &e);

  if (bn_is_zero(&e)) {
    return 3;
  }

  // Compute R = sG - eP
  bn_subtract(&curve->order, &e, &e);
  scalar_multiply(curve, &s, &sG);
  point_multiply(curve, &e, &P, &R);
  point_add(curve, &sG, &R);

  if (point_is_infinity(&R)) {
    return 4;
  }

  // Check r == Rx
  if (!bn_is_equal(&r, &R.x)) {
    return 5;
  }

  // Check Ry is a quadratic residue
  if (is_non_quad_residue(&R.y, &curve->prime)) {
    return 6;
  }

  return 0;
}
