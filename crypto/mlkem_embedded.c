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

#include "mlkem_embedded.h"

#include <string.h>

#include "memzero.h"
#include "rand.h"

#define MLKEM_K 3

// The vendored code exports the FIPS-202 primitives and randombytes() under
// generic names; prefix them to avoid collisions with sha3.c and other
// libraries. The ML-KEM functions themselves are already namespaced with the
// pqcrystals_mlkem768_ref_ prefix.
#define shake128_absorb mlke_shake128_absorb
#define shake128_squeezeblocks mlke_shake128_squeezeblocks
#define shake256_inc_init mlke_shake256_inc_init
#define shake256_inc_absorb mlke_shake256_inc_absorb
#define shake256_inc_finalize mlke_shake256_inc_finalize
#define shake256_inc_squeeze mlke_shake256_inc_squeeze
#define shake256 mlke_shake256
#define sha3_256 mlke_sha3_256
#define sha3_512 mlke_sha3_512
#define KeccakP1600_AddLanes mlke_KeccakP1600_AddLanes
#define KeccakF1600_StateExtractBytes mlke_KeccakF1600_StateExtractBytes
#define KeccakF1600_StateXORBytes mlke_KeccakF1600_StateXORBytes
#define KeccakF1600_StatePermute mlke_KeccakF1600_StatePermute
#define randombytes mlke_randombytes

// Single compilation unit build of the vendored low-memory ML-KEM
// implementation (see mlkem-embedded/README.md for provenance and local
// modifications).
#include "mlkem-embedded/fips202/keccakf1600.c"
#include "mlkem-embedded/fips202/fips202.c"
#include "mlkem-embedded/mlkem/cbd.c"
#include "mlkem-embedded/mlkem/indcpa.c"
#include "mlkem-embedded/mlkem/kem.c"
#include "mlkem-embedded/mlkem/matacc.c"
#include "mlkem-embedded/mlkem/ntt.c"
#include "mlkem-embedded/mlkem/poly.c"
#include "mlkem-embedded/mlkem/polyvec.c"
#include "mlkem-embedded/mlkem/reduce.c"
#include "mlkem-embedded/mlkem/symmetric-shake.c"
#include "mlkem-embedded/mlkem/verify.c"

_Static_assert(MLKEM768_PUBLIC_KEY_SIZE == MLKEM_PUBLICKEYBYTES,
               "MLKEM768_PUBLIC_KEY_SIZE mismatch");
_Static_assert(MLKEM768_PRIVATE_KEY_SIZE == MLKEM_SECRETKEYBYTES,
               "MLKEM768_PRIVATE_KEY_SIZE mismatch");
_Static_assert(MLKEM768_KEY_PAIR_SEED_SIZE == 2 * MLKEM_SYMBYTES,
               "MLKEM768_KEY_PAIR_SEED_SIZE mismatch");
_Static_assert(MLKEM768_CIPHERTEXT_SIZE == MLKEM_CIPHERTEXTBYTES,
               "MLKEM768_CIPHERTEXT_SIZE mismatch");
_Static_assert(MLKEM768_ENCAPSULATION_SEED_SIZE == MLKEM_SYMBYTES,
               "MLKEM768_ENCAPSULATION_SEED_SIZE mismatch");
_Static_assert(MLKEM768_SHARED_SECRET_SIZE == MLKEM_SSBYTES,
               "MLKEM768_SHARED_SECRET_SIZE mismatch");

// Referenced by the vendored randomized API, which is not used here; the
// randomized variants below are built on top of the derandomized API using
// random_buffer().
void mlke_randombytes(uint8_t *out, size_t outlen) {
  random_buffer(out, outlen);
}

/**
 * @brief Checks that the encapsulation key is a valid ML-KEM public key.
 *
 * Implements the modulus check from FIPS 203, Section 7.2: every 12-bit
 * coefficient of the serialized polynomial vector must be smaller than q.
 * The vendored code does not perform this check itself.
 */
static bool mlkem768_embedded_check_public_key(
    const uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE]) {
  for (size_t i = 0; i < MLKEM_POLYVECBYTES; i += 3) {
    uint16_t c0 = public_key[i] | ((uint16_t)(public_key[i + 1] & 0x0f) << 8);
    uint16_t c1 = (public_key[i + 1] >> 4) | ((uint16_t)public_key[i + 2] << 4);
    if (c0 >= MLKEM_Q || c1 >= MLKEM_Q) {
      return false;
    }
  }
  return true;
}

bool mlkem768_embedded_generate_key_pair(
    uint8_t private_key[MLKEM768_PRIVATE_KEY_SIZE],
    uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE]) {
  uint8_t seed[MLKEM768_KEY_PAIR_SEED_SIZE] = {0};
  random_buffer(seed, sizeof(seed));

  bool ret = mlkem768_embedded_generate_key_pair_from_seed(seed, private_key,
                                                           public_key);

  // Clear buffers from stack
  memzero(seed, sizeof(seed));
  return ret;
}

bool mlkem768_embedded_generate_key_pair_from_seed(
    const uint8_t seed[MLKEM768_KEY_PAIR_SEED_SIZE],
    uint8_t private_key[MLKEM768_PRIVATE_KEY_SIZE],
    uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE]) {
  return crypto_kem_keypair_derand(public_key, private_key, seed) == 0;
}

bool mlkem768_embedded_encapsulate(
    const uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE],
    uint8_t ciphertext[MLKEM768_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM768_SHARED_SECRET_SIZE]) {
  uint8_t seed[MLKEM768_ENCAPSULATION_SEED_SIZE] = {0};
  random_buffer(seed, sizeof(seed));

  bool ret = mlkem768_embedded_encapsulate_from_seed(seed, public_key,
                                                     ciphertext, shared_secret);

  // Clear buffers from stack
  memzero(seed, sizeof(seed));
  return ret;
}

bool mlkem768_embedded_encapsulate_from_seed(
    const uint8_t seed[MLKEM768_ENCAPSULATION_SEED_SIZE],
    const uint8_t public_key[MLKEM768_PUBLIC_KEY_SIZE],
    uint8_t ciphertext[MLKEM768_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM768_SHARED_SECRET_SIZE]) {
  if (!mlkem768_embedded_check_public_key(public_key)) {
    return false;
  }

  return crypto_kem_enc_derand(ciphertext, shared_secret, public_key, seed) ==
         0;
}

bool mlkem768_embedded_decapsulate(
    const uint8_t private_key[MLKEM768_PRIVATE_KEY_SIZE],
    const uint8_t ciphertext[MLKEM768_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM768_SHARED_SECRET_SIZE]) {
  return crypto_kem_dec(shared_secret, ciphertext, private_key) == 0;
}
