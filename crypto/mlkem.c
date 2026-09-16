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

#define MLK_CONFIG_PARAMETER_SET 768
#define MLK_CONFIG_NAMESPACE_PREFIX mlk
// The randomized API of mlkem-native is not used, because it requires an
// external randombytes() function. Randomized variants are implemented below
// on top of the derandomized API using random_buffer().
#define MLK_CONFIG_NO_RANDOMIZED_API

#include "mlkem.h"

#include "memzero.h"
#include "rand.h"

// The mlk_* API declarations and size constants of the vendored mlkem-native
// library. The size constants get undefined at the end of the single
// compilation unit below, so they can be checked for consistency only here.
#include "mlkem_native.h"

_Static_assert(MLKEM768_PUBLIC_KEY_SIZE == MLKEM768_PUBLICKEYBYTES,
               "MLKEM768_PUBLIC_KEY_SIZE mismatch");
_Static_assert(MLKEM768_PRIVATE_KEY_SIZE == MLKEM768_SECRETKEYBYTES,
               "MLKEM768_PRIVATE_KEY_SIZE mismatch");
_Static_assert(MLKEM768_KEY_PAIR_SEED_SIZE == 2 * MLKEM_SYMBYTES,
               "MLKEM768_KEY_PAIR_SEED_SIZE mismatch");
_Static_assert(MLKEM768_CIPHERTEXT_SIZE == MLKEM768_CIPHERTEXTBYTES,
               "MLKEM768_CIPHERTEXT_SIZE mismatch");
_Static_assert(MLKEM768_ENCAPSULATION_SEED_SIZE == MLKEM_SYMBYTES,
               "MLKEM768_ENCAPSULATION_SEED_SIZE mismatch");
_Static_assert(MLKEM768_SHARED_SECRET_SIZE == MLKEM768_BYTES,
               "MLKEM768_SHARED_SECRET_SIZE mismatch");

// Single compilation unit build of the vendored mlkem-native library. All
// its symbols are namespaced with the mlk_ prefix set by the configuration
// above. The library intentionally declares its API functions twice (in
// mlkem_native.h and in the internal kem.h), so -Wredundant-decls does not
// apply to it.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wredundant-decls"
#include "../vendor/mlkem-native/mlkem/mlkem_native.c"
#pragma GCC diagnostic pop

bool mlkem768_generate_key_pair(
    uint8_t private_key[MLKEM768_PRIVATE_KEY_SIZE],
    uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE]) {
  uint8_t seed[MLKEM768_KEY_PAIR_SEED_SIZE] = {0};
  random_buffer(seed, sizeof(seed));

  bool ret =
      mlkem768_generate_key_pair_from_seed(seed, private_key, public_key);

  // Clear buffers from stack
  memzero(seed, sizeof(seed));
  return ret;
}

bool mlkem768_generate_key_pair_from_seed(
    const uint8_t seed[MLKEM768_KEY_PAIR_SEED_SIZE],
    uint8_t private_key[MLKEM768_PRIVATE_KEY_SIZE],
    uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE]) {
  return mlk_keypair_derand(public_key, private_key, seed) == 0;
}

bool mlkem768_encapsulate(
    const uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE],
    uint8_t ciphertext[MLKEM768_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM768_SHARED_SECRET_SIZE]) {
  uint8_t seed[MLKEM768_ENCAPSULATION_SEED_SIZE] = {0};
  random_buffer(seed, sizeof(seed));

  bool ret = mlkem768_encapsulate_from_seed(seed, public_key, ciphertext,
                                            shared_secret);

  // Clear buffers from stack
  memzero(seed, sizeof(seed));
  return ret;
}

bool mlkem768_encapsulate_from_seed(
    const uint8_t seed[MLKEM768_ENCAPSULATION_SEED_SIZE],
    const uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE],
    uint8_t ciphertext[MLKEM768_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM768_SHARED_SECRET_SIZE]) {
  return mlk_enc_derand(ciphertext, shared_secret, public_key, seed) == 0;
}

bool mlkem768_decapsulate(
    const uint8_t private_key[MLKEM768_PRIVATE_KEY_SIZE],
    const uint8_t ciphertext[MLKEM768_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM768_SHARED_SECRET_SIZE]) {
  return mlk_dec(shared_secret, ciphertext, private_key) == 0;
}
