/**
 * Copyright (C) 2020-2026 Dyne.org foundation
 *
 * Standalone native test for crypto/pallas.c (self-contained Montgomery field
 * arithmetic + Pallas curve). Validates against the reference vectors emitted by
 *   cargo test -p darkfi-sdk trezor_pallas_montgomery -- --ignored --nocapture
 *   cargo test -p darkfi-sdk trezor_pallas_constants  -- --ignored --nocapture
 * (recorded in doc/src/dev/trezor_drk_test_vectors.md).
 *
 * Build (no external deps):
 *   cc -I. -I.. -O2 tests/test_pallas.c pallas.c pallas_poseidon.c pallas_drk.c memzero.c blake2b.c -o tests/test_pallas
 */

#include <stdio.h>
#include <string.h>

#include "pallas.h"

static int failures = 0;

static void hexparse(const char *hex, uint8_t *out, size_t outlen) {
  for (size_t i = 0; i < outlen; i++) {
    unsigned int byte = 0;
    sscanf(hex + 2 * i, "%2x", &byte);
    out[i] = (uint8_t)byte;
  }
}

static void check_bytes(const char *name, const uint8_t *got,
                        const char *want_hex, size_t len) {
  uint8_t want[64];
  hexparse(want_hex, want, len);
  if (memcmp(got, want, len) == 0) {
    printf("  ok   %s\n", name);
  } else {
    printf("  FAIL %s\n       got  ", name);
    for (size_t i = 0; i < len; i++) printf("%02x", got[i]);
    printf("\n       want %s\n", want_hex);
    failures++;
  }
}

int main(void) {
  printf("Pallas Montgomery field / curve vectors\n");

  // --- (0) round-trip: bytes -> F_p -> bytes -------------------------------
  {
    const char *hex =
        "f0debc9a78563412000000000000000000000000000000000000000000000000";
    uint8_t in[32], out[32];
    hexparse(hex, in, 32);
    pallas_fe a;
    pallas_fp_from_bytes(in, &a);
    pallas_fp_to_bytes(&a, out);
    check_bytes("F_p byte round-trip", out, hex, 32);
  }

  // --- (1) F_p multiply: a*b mod p ----------------------------------------
  {
    uint8_t ab[32], bb[32], out[32];
    hexparse("f0debc9a78563412000000000000000000000000000000000000000000000000",
             ab, 32);
    hexparse("21436587a9cbed0f000000000000000000000000000000000000000000000000",
             bb, 32);
    pallas_fe a, b, r;
    pallas_fp_from_bytes(ab, &a);
    pallas_fp_from_bytes(bb, &b);
    pallas_fp_mul(&a, &b, &r);
    pallas_fp_to_bytes(&r, out);
    check_bytes(
        "F_p mul a*b", out,
        "f08c61e58fd8362242d777ad00fa210100000000000000000000000000000000", 32);
  }

  // --- (2) F_p inverse: a * a^-1 == 1 -------------------------------------
  {
    uint8_t ab[32], out[32];
    hexparse("f0debc9a78563412000000000000000000000000000000000000000000000000",
             ab, 32);
    pallas_fe a, ai, prod;
    pallas_fp_from_bytes(ab, &a);
    pallas_fp_inv(&a, &ai);
    pallas_fp_mul(&a, &ai, &prod);
    pallas_fp_to_bytes(&prod, out);
    check_bytes(
        "F_p a*a^-1 == 1", out,
        "0100000000000000000000000000000000000000000000000000000000000000", 32);
  }

  // --- (3) generators lie on y^2 = x^3 + 5 --------------------------------
  {
    const pallas_point *pts[2] = {&pallas_spend_auth_g, &pallas_nullifier_k};
    const char *names[2] = {"SpendAuthG on-curve", "NullifierK on-curve"};
    // 5 in Montgomery form: from_bytes of the integer 5.
    uint8_t five_le[32] = {5};
    pallas_fe five;
    pallas_fp_from_bytes(five_le, &five);
    for (int i = 0; i < 2; i++) {
      pallas_fe y2, x2, x3, rhs;
      pallas_fp_mul(&pts[i]->y, &pts[i]->y, &y2);  // y^2
      pallas_fp_mul(&pts[i]->x, &pts[i]->x, &x2);  // x^2
      pallas_fp_mul(&x2, &pts[i]->x, &x3);         // x^3
      pallas_fp_add(&x3, &five, &rhs);             // x^3 + 5
      uint8_t a[32], b[32];
      pallas_fp_to_bytes(&y2, a);
      pallas_fp_to_bytes(&rhs, b);
      if (memcmp(a, b, 32) == 0) {
        printf("  ok   %s\n", names[i]);
      } else {
        printf("  FAIL %s\n", names[i]);
        failures++;
      }
    }
  }

  // --- (4) compressed encoding of SpendAuthG ------------------------------
  {
    uint8_t enc[32];
    pallas_point_to_bytes(&pallas_spend_auth_g, enc);
    check_bytes(
        "SpendAuthG to_bytes", enc,
        "63c975b884721a8d0ca1707be30c7f0c5f445f3e7c188d3b06d6f128b32355b7", 32);
  }

  // --- (5) point add: SpendAuthG + NullifierK -----------------------------
  {
    pallas_point r;
    pallas_point_add(&pallas_spend_auth_g, &pallas_nullifier_k, &r);
    uint8_t x[32], y[32];
    pallas_fp_to_bytes(&r.x, x);
    pallas_fp_to_bytes(&r.y, y);
    check_bytes(
        "SpendAuthG+NullifierK x", x,
        "3fce9e29250cb7e92eb87377354326485157f9b99845e6c7a78c0131b7406415", 32);
    check_bytes(
        "SpendAuthG+NullifierK y", y,
        "97a1f514700c79e4eb6156a14c8bc85af3c28a70787c46784e66792a3cfc6f10", 32);
  }

  // --- (6) scalar mul: k * SpendAuthG -------------------------------------
  {
    uint8_t k[32];
    hexparse("0df0fecaefbeadde000000000000000000000000000000000000000000000000",
             k, 32);
    pallas_point r;
    pallas_point_mul(k, &pallas_spend_auth_g, &r);
    uint8_t x[32], y[32];
    pallas_fp_to_bytes(&r.x, x);
    pallas_fp_to_bytes(&r.y, y);
    check_bytes(
        "k*SpendAuthG x", x,
        "b0d5443c365099d6acf7450722333cfb17018c3e27584bf4c0b3533e8d34e80c", 32);
    check_bytes(
        "k*SpendAuthG y", y,
        "14d3381e51f50d2c204d06e744fb58b2e4856f0f2f0e9f407ddf1dae2cdd3e1f", 32);
  }

  // --- (7) DarkFi ak = ask * NullifierK with ask=1 must equal NullifierK ---
  {
    uint8_t one[32] = {1};
    uint8_t ak[32], g[32];
    pallas_spend_auth_pubkey(one, ak);
    pallas_point_to_bytes(&pallas_nullifier_k, g);
    if (memcmp(ak, g, 32) == 0) {
      printf("  ok   ak(ask=1) == NullifierK\n");
    } else {
      printf("  FAIL ak(ask=1) == NullifierK\n");
      failures++;
    }
  }

  // --- (8) Poseidon hash([1, 2]) and hash([0, 0]) -------------------------
  {
    uint8_t one[32] = {1}, two[32] = {2}, zero[32] = {0}, out[32];
    pallas_poseidon_hash2(one, two, out);
    check_bytes(
        "poseidon([1,2])", out,
        "4ce3bd9407dc758983c62390ce00463beb82796eb0d40a0398993cb4eca55535", 32);
    pallas_poseidon_hash2(zero, zero, out);
    check_bytes(
        "poseidon([0,0])", out,
        "7a515983cec6c21e27c2f24fbc31c54d698400d33300ebc7f4677cb71b529403", 32);
  }

  // --- (8b) HD derivation vs reference vectors ---------------------------
  // seed[i] = (i*3 + 11) mod 256, 64 bytes (doc/src/dev/trezor_drk_test_vectors.md)
  {
    uint8_t seed[64];
    for (int i = 0; i < 64; i++) seed[i] = (uint8_t)((i * 3 + 11) & 0xff);

    uint8_t msk[32], mcc[32];
    pallas_hd_master(seed, sizeof(seed), msk, mcc);
    check_bytes(
        "hd master_sk", msk,
        "a86aaeca8d8b868a458f14b54b8d77a70fb602e5921c9f80918baab144140301", 32);
    check_bytes(
        "hd master_cc", mcc,
        "a0e8829d77beb343fe5096e3f89484a2871b3d069510f47b38e27d24226bbdd1", 32);

    uint8_t csk[32], ccc[32];
    pallas_hd_child(msk, mcc, 0, csk, ccc);
    check_bytes(
        "hd child0_sk", csk,
        "0e0bd3dd254ceea12d05fc902b3ea8977def94ee75905a2e80348e813d764132", 32);
    check_bytes(
        "hd child0_cc", ccc,
        "e71dddd63e11a30f4e5b6e2b74632523a2de50de94d369acaf0cc7039d4bcfe6", 32);

    uint8_t a0[32], a1[32];
    pallas_hd_account(seed, sizeof(seed), 0, a0);
    pallas_hd_account(seed, sizeof(seed), 1, a1);
    check_bytes(
        "hd account0_sk", a0,
        "0e0bd3dd254ceea12d05fc902b3ea8977def94ee75905a2e80348e813d764132", 32);
    check_bytes(
        "hd account1_sk", a1,
        "dacd62b821a9455297772a80d853aa088a26de3d6f686284f600ae9263fa282c", 32);
  }

  // --- (9) DRK key derivation vs reference vectors ------------------------
  // sk = 01080f16...d300 (from doc/src/dev/trezor_drk_test_vectors.md)
  {
    uint8_t sk[32];
    hexparse("01080f161d242b323940474e555c636a71787f868d949ba2a9b0b7bec5ccd300",
             sk, 32);
    uint8_t ask[32], nk[32], ivk[32], ak[32], pk_d[32];

    pallas_drk_derive_ask(sk, ask);
    check_bytes(
        "ask", ask,
        "bd3e05810cd60eb07b40207f0fb344aa3b7677f8574fb7e7c7a15144bee70d10", 32);

    pallas_drk_derive_ak(sk, ak);
    check_bytes(
        "ak", ak,
        "b623bf3d42cf1ee16f9db1343114614f853de2cc77aee95412a600c19516eab0", 32);

    pallas_drk_derive_nk(sk, nk);
    check_bytes(
        "nk", nk,
        "279eb4ce7e8100e805842475f7860266ee201f87ec91c080563504832818782a", 32);

    pallas_drk_derive_ivk_from_sk(sk, ivk);
    check_bytes(
        "ivk", ivk,
        "bceab0147a26863e018dbccc2db18260c96967df2813b9a1fc242618916dc13d", 32);

    pallas_drk_derive_pk_d(ivk, pk_d);
    check_bytes(
        "pk_d", pk_d,
        "d0632aac9222ff179a5599dcf2b2fbd6d9bc9d093709bb66da78711c7a357e1f", 32);

    // coin = poseidon([1,2]); nf = poseidon([ivk, coin])
    uint8_t one[32] = {1}, two[32] = {2}, coin[32], nf[32];
    pallas_poseidon_hash2(one, two, coin);
    check_bytes(
        "coin", coin,
        "4ce3bd9407dc758983c62390ce00463beb82796eb0d40a0398993cb4eca55535", 32);
    pallas_drk_nullifier(ivk, coin, nf);
    check_bytes(
        "nf", nf,
        "d300c19107782d48a97d36ddf9cf619e562dc149a20ff0d1cf6fd0f39b7c752e", 32);
  }

  // --- (9b) complete-formula edge cases (exception-free addition) ---------
  {
    pallas_point g = pallas_spend_auth_g;
    // P + (-P) == identity
    pallas_point negg, sum;
    pallas_point_neg(&g, &negg);
    pallas_point_add(&g, &negg, &sum);
    if (sum.infinity) {
      printf("  ok   P + (-P) == identity\n");
    } else {
      printf("  FAIL P + (-P) == identity\n");
      failures++;
    }
    // P + identity == P
    pallas_point id, r;
    pallas_point_set_infinity(&id);
    pallas_point_add(&g, &id, &r);
    uint8_t a[32], b[32];
    pallas_point_to_bytes(&r, a);
    pallas_point_to_bytes(&g, b);
    if (memcmp(a, b, 32) == 0) {
      printf("  ok   P + identity == P\n");
    } else {
      printf("  FAIL P + identity == P\n");
      failures++;
    }
    // P + P (add) == 2P (double)
    pallas_point dbl_add, dbl;
    pallas_point_add(&g, &g, &dbl_add);
    pallas_point_double(&g, &dbl);
    pallas_point_to_bytes(&dbl_add, a);
    pallas_point_to_bytes(&dbl, b);
    if (memcmp(a, b, 32) == 0) {
      printf("  ok   P + P == 2P\n");
    } else {
      printf("  FAIL P + P == 2P\n");
      failures++;
    }
  }

  // --- (10) spend-auth signature vs reference vectors + relations ---------
  {
    uint8_t ask[32], alpha[32];
    hexparse("bd3e05810cd60eb07b40207f0fb344aa3b7677f8574fb7e7c7a15144bee70d10",
             ask, 32);
    // alpha is the fixed canonical base-field element from the reference doc.
    hexparse("03080d12171c21262b30353a3f44494e53585d62676c71767b80858a8f949900",
             alpha, 32);
    const char *msg = "darkfi spend authorization";

    pallas_point commit_pt, rk_pt;
    uint8_t commit[32], rk[32], response[32];
    pallas_spend_auth_sign_full(ask, alpha, (const uint8_t *)msg, strlen(msg),
                                &commit_pt, &rk_pt, commit, rk, response);

    // Deterministic-nonce signature must match the SDK byte-for-byte.
    check_bytes(
        "spend-auth rk", rk,
        "30813b2ab4c612a49a861c90fbebd1a992c4935fc7cae1d3b130cfa3b83d9127", 32);
    check_bytes(
        "spend-auth commit", commit,
        "b317c617f67d1aa53b0b07edba4a7522aa3f66db68e4a73c49166a4376456005", 32);
    check_bytes(
        "spend-auth response", response,
        "046014935e293919df3ff217b727a9bfc3c34bcf55211550ffc781146c65e33b", 32);

    // rk must equal (ask+alpha)*NullifierK (the randomized public key).
    uint8_t rsk[32], rk_check[32];
    pallas_scalar_add(ask, alpha, rsk);
    pallas_point rkp;
    pallas_point_mul(rsk, &pallas_nullifier_k, &rkp);
    pallas_point_to_bytes(&rkp, rk_check);
    if (memcmp(rk, rk_check, 32) == 0) {
      printf("  ok   spend-auth rk == (ask+alpha)*NullifierK\n");
    } else {
      printf("  FAIL spend-auth rk == (ask+alpha)*NullifierK\n");
      failures++;
    }

    // The signature must verify against rk and msg.
    int ok = pallas_spend_auth_verify_full(&commit_pt, &rk_pt, commit, rk,
                                            response, (const uint8_t *)msg,
                                            strlen(msg));
    if (ok) {
      printf("  ok   spend-auth signature verifies\n");
    } else {
      printf("  FAIL spend-auth signature verifies\n");
      failures++;
    }

    // Tamper: flipping a response bit must break verification.
    uint8_t bad[32];
    memcpy(bad, response, 32);
    bad[0] ^= 0x01;
    int bad_ok = pallas_spend_auth_verify_full(&commit_pt, &rk_pt, commit, rk,
                                               bad, (const uint8_t *)msg,
                                               strlen(msg));
    if (!bad_ok) {
      printf("  ok   spend-auth rejects tampered response\n");
    } else {
      printf("  FAIL spend-auth rejects tampered response\n");
      failures++;
    }
  }

  if (failures == 0) {
    printf("ALL PASS\n");
    return 0;
  }
  printf("%d FAILURE(S)\n", failures);
  return 1;
}
