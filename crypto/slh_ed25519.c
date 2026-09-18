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

#include "slh_ed25519.h"

#include <string.h>

#include "ed25519-donna/ed25519.h"
#include "memzero.h"
#include "rand.h"
#include "sha2.h"
#include "sha3.h"

// Single compilation unit build of the vendored SPHINCS+ reference
// implementation. The PARAMS macro selects the sha2-128s parameter set used
// by the boot header signatures. All internal symbols are namespaced with
// the SPX_ prefix, the crypto_sign_* API and the SHA-2 helpers remain
// global.
#define PARAMS sphincs-sha2-128s
#include "../vendor/sphincsplus/ref/address.c"
#include "../vendor/sphincsplus/ref/fors.c"
#include "../vendor/sphincsplus/ref/hash_sha2.c"
#include "../vendor/sphincsplus/ref/merkle.c"
#include "../vendor/sphincsplus/ref/sha2.c"
#include "../vendor/sphincsplus/ref/sign.c"
#include "../vendor/sphincsplus/ref/thash_sha2_simple.c"
#include "../vendor/sphincsplus/ref/utils.c"
#include "../vendor/sphincsplus/ref/utilsx1.c"
#include "../vendor/sphincsplus/ref/wots.c"
#include "../vendor/sphincsplus/ref/wotsx1.c"

#define SLH_ED25519_SLH_SIGNATURE_SIZE SPX_BYTES
#define SLH_ED25519_SLH_PUBLIC_KEY_SIZE SPX_PK_BYTES
#define SLH_ED25519_ED25519_KEY_SIZE 32

_Static_assert(SLH_ED25519_PUBLIC_KEY_SIZE ==
                   SLH_ED25519_SLH_PUBLIC_KEY_SIZE + SLH_ED25519_ED25519_KEY_SIZE,
               "SLH_ED25519_PUBLIC_KEY_SIZE mismatch");
_Static_assert(SLH_ED25519_SIGNATURE_SIZE ==
                   SLH_ED25519_SLH_SIGNATURE_SIZE + sizeof(ed25519_signature),
               "SLH_ED25519_SIGNATURE_SIZE mismatch");

// Referenced by the vendored crypto_sign_signature() to generate the
// signature randomizer.
void randombytes(unsigned char *x, unsigned long long xlen) {
  random_buffer(x, (size_t)xlen);
}

/**
 * @brief Derives the SPHINCS+ key pair and the Ed25519 private key from the
 * hybrid private key.
 */
static bool slh_ed25519_expand_private_key(
    const uint8_t private_key[SLH_ED25519_PRIVATE_KEY_SIZE],
    uint8_t slh_public_key[SLH_ED25519_SLH_PUBLIC_KEY_SIZE],
    uint8_t slh_private_key[SPX_SK_BYTES],
    ed25519_secret_key ed25519_private_key) {
  uint8_t expanded[CRYPTO_SEEDBYTES + SLH_ED25519_ED25519_KEY_SIZE] = {0};
  shake256(private_key, SLH_ED25519_PRIVATE_KEY_SIZE, expanded,
           sizeof(expanded));

  bool ret =
      crypto_sign_seed_keypair(slh_public_key, slh_private_key, expanded) == 0;
  memcpy(ed25519_private_key, expanded + CRYPTO_SEEDBYTES,
         SLH_ED25519_ED25519_KEY_SIZE);

  // Clear buffers from stack
  memzero(expanded, sizeof(expanded));
  return ret;
}

/**
 * @brief Computes the digest signed by the Ed25519 part.
 *
 * The digest covers both the message and the SPHINCS+ signature, so the
 * Ed25519 signature authenticates the SPHINCS+ signature.
 */
static void slh_ed25519_ext_digest(
    const uint8_t *message, size_t message_size,
    const uint8_t slh_signature[SLH_ED25519_SLH_SIGNATURE_SIZE],
    uint8_t digest[SHA256_DIGEST_LENGTH]) {
  SHA256_CTX ctx = {0};
  sha256_Init(&ctx);
  sha256_Update(&ctx, message, message_size);
  sha256_Update(&ctx, slh_signature, SLH_ED25519_SLH_SIGNATURE_SIZE);
  sha256_Final(&ctx, digest);
}

bool slh_ed25519_generate_key_pair(
    uint8_t private_key[SLH_ED25519_PRIVATE_KEY_SIZE],
    uint8_t public_key[SLH_ED25519_PUBLIC_KEY_SIZE]) {
  random_buffer(private_key, SLH_ED25519_PRIVATE_KEY_SIZE);
  return slh_ed25519_derive_public_key(private_key, public_key);
}

bool slh_ed25519_derive_public_key(
    const uint8_t private_key[SLH_ED25519_PRIVATE_KEY_SIZE],
    uint8_t public_key[SLH_ED25519_PUBLIC_KEY_SIZE]) {
  uint8_t slh_private_key[SPX_SK_BYTES] = {0};
  ed25519_secret_key ed25519_private_key = {0};

  bool ret = slh_ed25519_expand_private_key(
      private_key, public_key, slh_private_key, ed25519_private_key);
  if (ret) {
    ed25519_publickey(ed25519_private_key,
                      public_key + SLH_ED25519_SLH_PUBLIC_KEY_SIZE);
  }

  // Clear buffers from stack
  memzero(slh_private_key, sizeof(slh_private_key));
  memzero(ed25519_private_key, sizeof(ed25519_private_key));
  return ret;
}

bool slh_ed25519_sign(const uint8_t private_key[SLH_ED25519_PRIVATE_KEY_SIZE],
                      const uint8_t *message, size_t message_size,
                      uint8_t signature[SLH_ED25519_SIGNATURE_SIZE]) {
  uint8_t slh_public_key[SLH_ED25519_SLH_PUBLIC_KEY_SIZE] = {0};
  uint8_t slh_private_key[SPX_SK_BYTES] = {0};
  ed25519_secret_key ed25519_private_key = {0};

  bool ret = slh_ed25519_expand_private_key(
      private_key, slh_public_key, slh_private_key, ed25519_private_key);

  size_t slh_signature_size = 0;
  if (ret) {
    ret = crypto_sign_signature(signature, &slh_signature_size, message,
                                message_size, slh_private_key) == 0 &&
          slh_signature_size == SLH_ED25519_SLH_SIGNATURE_SIZE;
  }

  if (ret) {
    uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
    slh_ed25519_ext_digest(message, message_size, signature, digest);
    ed25519_sign(digest, sizeof(digest), ed25519_private_key,
                 signature + SLH_ED25519_SLH_SIGNATURE_SIZE);
  }

  // Clear buffers from stack
  memzero(slh_private_key, sizeof(slh_private_key));
  memzero(ed25519_private_key, sizeof(ed25519_private_key));
  return ret;
}

bool slh_ed25519_verify(const uint8_t public_key[SLH_ED25519_PUBLIC_KEY_SIZE],
                        const uint8_t *message, size_t message_size,
                        const uint8_t signature[SLH_ED25519_SIGNATURE_SIZE]) {
  // Verify the Ed25519 signature first, so that the SPHINCS+ verifier
  // processes only authenticated input.
  uint8_t digest[SHA256_DIGEST_LENGTH] = {0};
  slh_ed25519_ext_digest(message, message_size, signature, digest);
  if (ed25519_sign_open(digest, sizeof(digest),
                        public_key + SLH_ED25519_SLH_PUBLIC_KEY_SIZE,
                        signature + SLH_ED25519_SLH_SIGNATURE_SIZE) != 0) {
    return false;
  }

  return crypto_sign_verify(signature, SLH_ED25519_SLH_SIGNATURE_SIZE, message,
                            message_size, public_key) == 0;
}

bool slh_ed25519_verify_2of2(
    const uint8_t public_key1[SLH_ED25519_PUBLIC_KEY_SIZE],
    const uint8_t public_key2[SLH_ED25519_PUBLIC_KEY_SIZE],
    const uint8_t *message, size_t message_size,
    const uint8_t signature1[SLH_ED25519_SIGNATURE_SIZE],
    const uint8_t signature2[SLH_ED25519_SIGNATURE_SIZE]) {
  if (memcmp(public_key1, public_key2, SLH_ED25519_PUBLIC_KEY_SIZE) == 0) {
    return false;
  }

  return slh_ed25519_verify(public_key1, message, message_size, signature1) &&
         slh_ed25519_verify(public_key2, message, message_size, signature2);
}
