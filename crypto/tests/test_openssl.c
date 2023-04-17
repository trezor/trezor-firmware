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

/* OpenSSL's SHA256_CTX/SHA512_CTX conflicts with our own */
#define SHA256_CTX _openssl_SHA256_CTX
#define SHA512_CTX _openssl_SHA512_CTX
#include <openssl/core_names.h>
#include <openssl/ecdsa.h>
#include <openssl/evp.h>
#undef SHA256_CTX
#undef SHA512_CTX

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "ecdsa.h"
#include "hasher.h"
#include "rand.h"

#include "nist256p1.h"
#include "secp256k1.h"

#include "memzero.h"

void openssl_check(unsigned int iterations, int nid, const ecdsa_curve *curve) {
  uint8_t sig[64], pub_key33[33], pub_key65[65], priv_key[32], msg[256];

  for (unsigned int iter = 0; iter < iterations; iter++) {
    // random message len between 1 and 256
    int msg_len = (random32() & 0xFF) + 1;
    // create random message
    random_buffer(msg, msg_len);

    // new ECDSA key
    EVP_PKEY_CTX *pkey_ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_EC, NULL);
    if (!pkey_ctx) {
      printf("EVP_PKEY_CTX_new_from_name failed\n");
      return;
    }

    if (EVP_PKEY_keygen_init(pkey_ctx) <= 0) {
      printf("EVP_PKEY_keygen_init failed\n");
      return;
    }

    if (EVP_PKEY_CTX_set_ec_paramgen_curve_nid(pkey_ctx, nid) <= 0) {
      printf("EVP_PKEY_CTX_set_ec_paramgen_curve_nid failed\n");
      return;
    }

    // generate the key
    EVP_PKEY *pkey = NULL;
    if (EVP_PKEY_keygen(pkey_ctx, &pkey) <= 0) {
      printf("EVP_PKEY_keygen failed\n");
      return;
    }
    EVP_PKEY_CTX_free(pkey_ctx);

    // copy key to buffer
    BIGNUM *K = NULL;
    if (!EVP_PKEY_get_bn_param(pkey, OSSL_PKEY_PARAM_PRIV_KEY, &K)) {
      printf("EVP_PKEY_get_bn_param failed\n");
      return;
    }
    int bn_off = sizeof(priv_key) - BN_num_bytes(K);
    memzero(priv_key, bn_off);
    BN_bn2bin(K, priv_key + bn_off);
    BN_free(K);

    // use our ECDSA signer to sign the message with the key
    if (ecdsa_sign(curve, HASHER_SHA2, priv_key, msg, msg_len, sig, NULL,
                   NULL) != 0) {
      printf("trezor-crypto signing failed\n");
      return;
    }

    // generate public key from private key
    if (ecdsa_get_public_key33(curve, priv_key, pub_key33) != 0) {
      printf("ecdsa_get_public_key33 failed\n");
      return;
    }

    if (ecdsa_get_public_key65(curve, priv_key, pub_key65) != 0) {
      printf("ecdsa_get_public_key65 failed\n");
      return;
    }

    // use our ECDSA verifier to verify the message signature
    if (ecdsa_verify(curve, HASHER_SHA2, pub_key65, sig, msg, msg_len) != 0) {
      printf("trezor-crypto verification failed (pub_key_len = 65)\n");
      return;
    }
    if (ecdsa_verify(curve, HASHER_SHA2, pub_key33, sig, msg, msg_len) != 0) {
      printf("trezor-crypto verification failed (pub_key_len = 33)\n");
      return;
    }

    // convert signature to DER which OpenSSL understands
    uint8_t sig_der[72] = {0};
    int sig_der_len = ecdsa_sig_to_der(sig, sig_der);

    // compute the digest of the message
    // note: these are OpenSSL functions, not our own
    EVP_MD_CTX *md_ctx = EVP_MD_CTX_new();
    if (!md_ctx) {
      printf("EVP_MD_CTX_new failed\n");
      return;
    }

    if (EVP_DigestVerifyInit(md_ctx, NULL, EVP_sha256(), NULL, pkey) <= 0) {
      printf("EVP_DigestVerifyInit failed\n");
      return;
    }

    if (EVP_DigestVerifyUpdate(md_ctx, msg, msg_len) <= 0) {
      printf("EVP_DigestVerifyUpdate failed\n");
      return;
    }

    // verify all went well, i.e. we can decrypt our signature with OpenSSL
    int v = EVP_DigestVerifyFinal(md_ctx, sig_der, sig_der_len);
    if (v != 1) {
      printf("OpenSSL verification failed (%d)\n", v);
      return;
    }

    EVP_MD_CTX_free(md_ctx);
    EVP_PKEY_free(pkey);

    if (((iter + 1) % 100) == 0) printf("Passed ... %d\n", iter + 1);
  }
  printf("All OK\n");
}

int main(int argc, char *argv[]) {
  if (argc != 2) {
    printf("Usage: test_openssl iterations\n");
    return 1;
  }

  unsigned int iterations;
  sscanf(argv[1], "%u", &iterations);

  printf("Testing secp256k1:\n");
  openssl_check(iterations, NID_secp256k1, &secp256k1);

  printf("Testing nist256p1:\n");
  openssl_check(iterations, NID_X9_62_prime256v1, &nist256p1);

  return 0;
}
