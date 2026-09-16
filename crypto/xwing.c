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

#include "xwing.h"

#include <string.h>

#include "ed25519-donna/ed25519.h"
#include "memzero.h"
#include "mlkem.h"
#include "rand.h"
#include "sha3.h"

#define XWING_X25519_KEY_SIZE 32

_Static_assert(XWING_PUBLIC_KEY_SIZE ==
                   MLKEM768_PUBLIC_KEY_SIZE + XWING_X25519_KEY_SIZE,
               "XWING_PUBLIC_KEY_SIZE mismatch");
_Static_assert(XWING_CIPHERTEXT_SIZE ==
                   MLKEM768_CIPHERTEXT_SIZE + XWING_X25519_KEY_SIZE,
               "XWING_CIPHERTEXT_SIZE mismatch");
_Static_assert(XWING_ENCAPSULATION_SEED_SIZE ==
                   MLKEM768_ENCAPSULATION_SEED_SIZE + XWING_X25519_KEY_SIZE,
               "XWING_ENCAPSULATION_SEED_SIZE mismatch");
_Static_assert(XWING_SHARED_SECRET_SIZE == SHA3_256_DIGEST_LENGTH,
               "XWING_SHARED_SECRET_SIZE mismatch");

/**
 * @brief Computes the X-Wing shared secret.
 *
 * Implements Combiner from draft-connolly-cfrg-xwing-kem-10, Section 5.2.
 */
static void xwing_combiner(
    const uint8_t mlkem_shared_secret[MLKEM768_SHARED_SECRET_SIZE],
    const uint8_t x25519_shared_secret[XWING_X25519_KEY_SIZE],
    const uint8_t x25519_ciphertext[XWING_X25519_KEY_SIZE],
    const uint8_t x25519_public_key[XWING_X25519_KEY_SIZE],
    uint8_t shared_secret[XWING_SHARED_SECRET_SIZE]) {
  // XWingLabel from draft-connolly-cfrg-xwing-kem-10, Section 5.2
  static const uint8_t xwing_label[6] = {'\\', '.', '/', '/', '^', '\\'};

  SHA3_CTX ctx = {0};
  sha3_256_Init(&ctx);
  sha3_Update(&ctx, mlkem_shared_secret, MLKEM768_SHARED_SECRET_SIZE);
  sha3_Update(&ctx, x25519_shared_secret, XWING_X25519_KEY_SIZE);
  sha3_Update(&ctx, x25519_ciphertext, XWING_X25519_KEY_SIZE);
  sha3_Update(&ctx, x25519_public_key, XWING_X25519_KEY_SIZE);
  sha3_Update(&ctx, xwing_label, sizeof(xwing_label));
  // sha3_Final() clears the context
  sha3_Final(&ctx, shared_secret);
}

/**
 * @brief Derives the ML-KEM-768 key pair and the X25519 private key from the
 * X-Wing private key.
 *
 * Implements expandDecapsulationKey from draft-connolly-cfrg-xwing-kem-10,
 * Section 5.3.
 */
static bool xwing_expand_private_key(
    const uint8_t private_key[XWING_PRIVATE_KEY_SIZE],
    uint8_t mlkem_private_key[MLKEM768_PRIVATE_KEY_SIZE],
    uint8_t mlkem_public_key[MLKEM768_PUBLIC_KEY_SIZE],
    uint8_t x25519_private_key[XWING_X25519_KEY_SIZE]) {
  uint8_t expanded[MLKEM768_KEY_PAIR_SEED_SIZE + XWING_X25519_KEY_SIZE] = {0};
  shake256(private_key, XWING_PRIVATE_KEY_SIZE, expanded, sizeof(expanded));

  bool ret = mlkem768_generate_key_pair_from_seed(expanded, mlkem_private_key,
                                                  mlkem_public_key);
  memcpy(x25519_private_key, expanded + MLKEM768_KEY_PAIR_SEED_SIZE,
         XWING_X25519_KEY_SIZE);

  // Clear buffers from stack
  memzero(expanded, sizeof(expanded));
  return ret;
}

bool xwing_generate_key_pair(uint8_t private_key[XWING_PRIVATE_KEY_SIZE],
                             uint8_t public_key[XWING_PUBLIC_KEY_SIZE]) {
  random_buffer(private_key, XWING_PRIVATE_KEY_SIZE);
  return xwing_derive_public_key(private_key, public_key);
}

bool xwing_derive_public_key(const uint8_t private_key[XWING_PRIVATE_KEY_SIZE],
                             uint8_t public_key[XWING_PUBLIC_KEY_SIZE]) {
  uint8_t mlkem_private_key[MLKEM768_PRIVATE_KEY_SIZE] = {0};
  uint8_t x25519_private_key[XWING_X25519_KEY_SIZE] = {0};

  bool ret = xwing_expand_private_key(private_key, mlkem_private_key,
                                      public_key, x25519_private_key);
  if (ret) {
    curve25519_scalarmult_basepoint(public_key + MLKEM768_PUBLIC_KEY_SIZE,
                                    x25519_private_key);
  }

  // Clear buffers from stack
  memzero(mlkem_private_key, sizeof(mlkem_private_key));
  memzero(x25519_private_key, sizeof(x25519_private_key));
  return ret;
}

bool xwing_encapsulate(const uint8_t public_key[XWING_PUBLIC_KEY_SIZE],
                       uint8_t ciphertext[XWING_CIPHERTEXT_SIZE],
                       uint8_t shared_secret[XWING_SHARED_SECRET_SIZE]) {
  uint8_t seed[XWING_ENCAPSULATION_SEED_SIZE] = {0};
  random_buffer(seed, sizeof(seed));

  bool ret =
      xwing_encapsulate_from_seed(seed, public_key, ciphertext, shared_secret);

  // Clear buffers from stack
  memzero(seed, sizeof(seed));
  return ret;
}

bool xwing_encapsulate_from_seed(
    const uint8_t seed[XWING_ENCAPSULATION_SEED_SIZE],
    const uint8_t public_key[XWING_PUBLIC_KEY_SIZE],
    uint8_t ciphertext[XWING_CIPHERTEXT_SIZE],
    uint8_t shared_secret[XWING_SHARED_SECRET_SIZE]) {
  const uint8_t *mlkem_seed = seed;
  const uint8_t *x25519_private_key = seed + MLKEM768_ENCAPSULATION_SEED_SIZE;
  const uint8_t *mlkem_public_key = public_key;
  const uint8_t *x25519_public_key = public_key + MLKEM768_PUBLIC_KEY_SIZE;
  uint8_t *mlkem_ciphertext = ciphertext;
  uint8_t *x25519_ciphertext = ciphertext + MLKEM768_CIPHERTEXT_SIZE;

  uint8_t mlkem_shared_secret[MLKEM768_SHARED_SECRET_SIZE] = {0};
  uint8_t x25519_shared_secret[XWING_X25519_KEY_SIZE] = {0};

  // includes the encapsulation key check from FIPS 203, Section 7.2
  bool ret = mlkem768_encapsulate_from_seed(
      mlkem_seed, mlkem_public_key, mlkem_ciphertext, mlkem_shared_secret);
  if (ret) {
    curve25519_scalarmult_basepoint(x25519_ciphertext, x25519_private_key);
    curve25519_scalarmult(x25519_shared_secret, x25519_private_key,
                          x25519_public_key);
    xwing_combiner(mlkem_shared_secret, x25519_shared_secret, x25519_ciphertext,
                   x25519_public_key, shared_secret);
  } else {
    memzero(ciphertext, XWING_CIPHERTEXT_SIZE);
    memzero(shared_secret, XWING_SHARED_SECRET_SIZE);
  }

  // Clear buffers from stack
  memzero(mlkem_shared_secret, sizeof(mlkem_shared_secret));
  memzero(x25519_shared_secret, sizeof(x25519_shared_secret));
  return ret;
}

bool xwing_decapsulate(const uint8_t private_key[XWING_PRIVATE_KEY_SIZE],
                       const uint8_t ciphertext[XWING_CIPHERTEXT_SIZE],
                       uint8_t shared_secret[XWING_SHARED_SECRET_SIZE]) {
  const uint8_t *mlkem_ciphertext = ciphertext;
  const uint8_t *x25519_ciphertext = ciphertext + MLKEM768_CIPHERTEXT_SIZE;

  uint8_t mlkem_private_key[MLKEM768_PRIVATE_KEY_SIZE] = {0};
  uint8_t mlkem_public_key[MLKEM768_PUBLIC_KEY_SIZE] = {0};
  uint8_t x25519_private_key[XWING_X25519_KEY_SIZE] = {0};
  uint8_t x25519_public_key[XWING_X25519_KEY_SIZE] = {0};
  uint8_t mlkem_shared_secret[MLKEM768_SHARED_SECRET_SIZE] = {0};
  uint8_t x25519_shared_secret[XWING_X25519_KEY_SIZE] = {0};

  bool ret = xwing_expand_private_key(private_key, mlkem_private_key,
                                      mlkem_public_key, x25519_private_key);
  if (ret) {
    ret = mlkem768_decapsulate(mlkem_private_key, mlkem_ciphertext,
                               mlkem_shared_secret);
  }
  if (ret) {
    curve25519_scalarmult(x25519_shared_secret, x25519_private_key,
                          x25519_ciphertext);
    curve25519_scalarmult_basepoint(x25519_public_key, x25519_private_key);
    xwing_combiner(mlkem_shared_secret, x25519_shared_secret, x25519_ciphertext,
                   x25519_public_key, shared_secret);
  } else {
    memzero(shared_secret, XWING_SHARED_SECRET_SIZE);
  }

  // Clear buffers from stack
  memzero(mlkem_private_key, sizeof(mlkem_private_key));
  memzero(mlkem_public_key, sizeof(mlkem_public_key));
  memzero(x25519_private_key, sizeof(x25519_private_key));
  memzero(x25519_public_key, sizeof(x25519_public_key));
  memzero(mlkem_shared_secret, sizeof(mlkem_shared_secret));
  memzero(x25519_shared_secret, sizeof(x25519_shared_secret));
  return ret;
}
