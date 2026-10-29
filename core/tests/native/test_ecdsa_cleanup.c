/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Observe calls from the actual crypto archive via linker wrapping. Inspect
 * stack buffers only inside memzero, while their owner frame is still live. */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "ecdsa_internal.h"
#include "memzero.h"
#include "nist256p1.h"
#include "rfc6979.h"
#include "secp256k1.h"

static bignum256 *live_nonce;
static rfc6979_state *live_rng;
static unsigned generations, nonce_erases, rng_erases, rejected;
void __real_memzero(void *p, size_t length);
void __real_generate_k_rfc6979(bignum256 *k, rfc6979_state *rng);
void __real_init_rfc6979(const uint8_t *key, const uint8_t *hash,
                         const ecdsa_curve *curve, rfc6979_state *rng);

void __wrap_init_rfc6979(const uint8_t *key, const uint8_t *hash,
                         const ecdsa_curve *curve, rfc6979_state *rng) {
  assert(!live_rng);
  live_rng = rng;
  __real_init_rfc6979(key, hash, curve, rng);
}
void __wrap_generate_k_rfc6979(bignum256 *k, rfc6979_state *rng) {
  assert(rng == live_rng);
  assert(!live_nonce || live_nonce == k);
  live_nonce = k;
  __real_generate_k_rfc6979(k, rng);
  assert(!bn_is_zero(k));
  generations++;
}
void __wrap_memzero(void *p, size_t length) {
  __real_memzero(p, length);
  if (p == live_nonce && length == sizeof(*live_nonce)) {
    for (size_t i = 0; i < length; i++) assert(((uint8_t *)p)[i] == 0);
    nonce_erases++;
    live_nonce = NULL;
  }
  if (p == live_rng && length == sizeof(*live_rng)) {
    for (size_t i = 0; i < length; i++) assert(((uint8_t *)p)[i] == 0);
    rng_erases++;
    live_rng = NULL;
  }
}
static int reject_once(uint8_t recovery, uint8_t signature[64]) {
  (void)recovery;
  (void)signature;
  return rejected++ != 0;
}
/* Entropy is only used for arithmetic blinding. */
uint32_t random32(void) { return 0x87654321; }
void random_buffer(uint8_t *out, size_t length) { memset(out, 0x5a, length); }

int main(void) {
  const ecdsa_curve *curves[] = {&nist256p1, &secp256k1};
  uint8_t key[32] = {0}, digest[32], signature[64], public_key[33];
  key[31] = 1;
  for (size_t i = 0; i < 2; i++) {
    const ecdsa_curve *curve = curves[i];
    memset(digest, 0x42, sizeof(digest));
    generations = nonce_erases = rng_erases = rejected = 0;
    assert(!tc_ecdsa_sign_digest(curve, key, digest, signature, NULL, NULL));
    assert(generations >= 1 && nonce_erases == 1 && rng_erases == 1);
    assert(!live_nonce && !live_rng);
    assert(!tc_ecdsa_get_public_key33(curve, key, public_key));
    assert(!tc_ecdsa_verify_digest(curve, public_key, signature, digest));
    generations = nonce_erases = rng_erases = 0;
    assert(!tc_ecdsa_sign_digest(curve, key, digest, signature, NULL,
                                 reject_once));
    assert(generations >= 2 && rejected == 2 && nonce_erases == 1 &&
           rng_erases == 1);
    assert(!live_nonce && !live_rng);
    generations = nonce_erases = rng_erases = 0;
    memset(digest, 0, sizeof(digest));
    assert(tc_ecdsa_sign_digest(curve, key, digest, signature, NULL, NULL));
    assert(generations == 0 && nonce_erases == 0 && rng_erases == 1);
    assert(!live_nonce && !live_rng);
  }
  puts("linked ECDSA nonce and RFC6979 cleanup tests passed");
}

/* Match the firmware archive's assert/fatal ABI and fail the host test. */
#include <stdlib.h>
void __attribute__((noreturn)) __assert_impl(const char *file, int line) {
  fprintf(stderr, "firmware assertion: %s:%d\n", file, line);
  abort();
}
void __attribute__((noreturn)) system_exit_error(const char *title,
                                                 const char *message,
                                                 const char *footer) {
  (void)footer;
  fprintf(stderr, "firmware fatal: %s: %s\n", title, message);
  abort();
}
