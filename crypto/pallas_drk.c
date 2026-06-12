/**
 * Copyright (C) 2020-2026 Dyne.org foundation
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

// DarkFi DRK hierarchical-deterministic and key-hierarchy derivation on Pallas,
// matching src/sdk/src/crypto/hd.rs and src/sdk/src/crypto/keys_hierarchy.rs.
// Uses BLAKE2b (HD PRF + Expand PRF), the Pallas field/curve, and Poseidon.
// See doc/src/dev/trezor_drk_test_vectors.md for the cross-repo vectors.
//
// All of `ak`, `rk` and `pk_d` live on the NullifierK fixed base (the same
// generator as PublicKey::from_secret and schnorr.rs), so spend authorization
// is a stock DarkFi Schnorr signature verifiable by the unchanged on-chain
// verifier.

#include "pallas.h"

#include <string.h>

#include "blake2b.h"
#include "memzero.h"

// Personalizations (<= 16 bytes, matching blake2b_simd Params::personal()).
#define DRK_EXPAND_DOMAIN "DarkFi:Expand"
#define EXPAND_ASK 0x06
#define EXPAND_NK 0x07

// HD derivation personalizations (hd.rs).
#define DRK_HD_KEY_DOMAIN "DarkFi:HDKey"
#define DRK_HD_CHAIN_DOMAIN "DarkFi:HDChain"
// Hardened-derivation marker, as in BIP-32.
#define DRK_HD_HARDENED 0x80000000u

// BLAKE2b with a <=16-byte personalization over a list of parts, producing
// `outlen` bytes (32 or 64). blake2b_simd zero-pads the personalization to 16
// bytes; Trezor's blake2b_InitPersonal requires exactly 16, so pass a
// zero-padded buffer.
static void drk_blake2b_personal(const char *domain, size_t outlen,
                                 const uint8_t *const parts[],
                                 const size_t lens[], size_t nparts,
                                 uint8_t *out) {
  uint8_t personal[16] = {0};
  memcpy(personal, domain, strlen(domain));
  blake2b_state S;
  blake2b_InitPersonal(&S, outlen, personal, sizeof(personal));
  for (size_t i = 0; i < nparts; i++) {
    blake2b_Update(&S, parts[i], lens[i]);
  }
  blake2b_Final(&S, out, outlen);
}

// --- HD derivation (hd.rs) ---------------------------------------------

void pallas_hd_master(const uint8_t *seed, size_t seed_len, uint8_t sk_out[32],
                      uint8_t cc_out[32]) {
  const uint8_t *parts[1] = {seed};
  size_t lens[1] = {seed_len};

  uint8_t wide[64];
  drk_blake2b_personal(DRK_HD_KEY_DOMAIN, 64, parts, lens, 1, wide);
  pallas_fp_from_wide_bytes(wide, sk_out);  // ToBase, wide-reduced
  drk_blake2b_personal(DRK_HD_CHAIN_DOMAIN, 32, parts, lens, 1, cc_out);
  memzero(wide, sizeof(wide));
}

void pallas_hd_child(const uint8_t sk[32], const uint8_t cc[32], uint32_t index,
                     uint8_t sk_out[32], uint8_t cc_out[32]) {
  // The hardened bit is always forced on; the index is mixed in little-endian.
  uint32_t i = index | DRK_HD_HARDENED;
  uint8_t i_le[4] = {(uint8_t)(i & 0xff), (uint8_t)((i >> 8) & 0xff),
                     (uint8_t)((i >> 16) & 0xff), (uint8_t)((i >> 24) & 0xff)};

  const uint8_t *parts[3] = {cc, sk, i_le};
  size_t lens[3] = {32, 32, 4};

  uint8_t wide[64];
  drk_blake2b_personal(DRK_HD_KEY_DOMAIN, 64, parts, lens, 3, wide);
  pallas_fp_from_wide_bytes(wide, sk_out);  // ToBase, wide-reduced
  drk_blake2b_personal(DRK_HD_CHAIN_DOMAIN, 32, parts, lens, 3, cc_out);
  memzero(wide, sizeof(wide));
}

void pallas_hd_account(const uint8_t *seed, size_t seed_len, uint32_t account,
                       uint8_t sk_out[32]) {
  uint8_t msk[32], mcc[32], ccc[32];
  pallas_hd_master(seed, seed_len, msk, mcc);
  pallas_hd_child(msk, mcc, account, sk_out, ccc);
  memzero(msk, sizeof(msk));
  memzero(mcc, sizeof(mcc));
  memzero(ccc, sizeof(ccc));
}

// Expand(sk, t) = BLAKE2b-512(personal="DarkFi:Expand", msg = sk_le || t).
static void drk_expand(const uint8_t sk[32], uint8_t t, uint8_t out64[64]) {
  const uint8_t *parts[2] = {sk, &t};
  size_t lens[2] = {32, 1};
  drk_blake2b_personal(DRK_EXPAND_DOMAIN, 64, parts, lens, 2, out64);
}

void pallas_drk_derive_ask(const uint8_t sk[32], uint8_t ask_out[32]) {
  uint8_t wide[64];
  drk_expand(sk, EXPAND_ASK, wide);
  pallas_fq_reduce_wide(wide, ask_out);  // ToScalar
  memzero(wide, sizeof(wide));
}

void pallas_drk_derive_nk(const uint8_t sk[32], uint8_t nk_out[32]) {
  uint8_t wide[64];
  drk_expand(sk, EXPAND_NK, wide);
  pallas_fp_from_wide_bytes(wide, nk_out);  // ToBase
  memzero(wide, sizeof(wide));
}

void pallas_drk_nullifier(const uint8_t nk[32], const uint8_t coin[32],
                          uint8_t nf_out[32]) {
  pallas_poseidon_hash2(nk, coin, nf_out);
}

// hash_to_scalar(personal="DarkFi:Schnorr", concatenated parts) -> F_q.
// This is the same domain the on-chain Schnorr verifier uses, so a randomized
// spend-authorization signature produced here is accepted unchanged.
#define DRK_SCHNORR_DOMAIN "DarkFi:Schnorr"

static void schnorr_hash_to_scalar(const uint8_t *const parts[],
                                    const size_t lens[], size_t nparts,
                                    uint8_t out[32]) {
  uint8_t wide[64];
  drk_blake2b_personal(DRK_SCHNORR_DOMAIN, 64, parts, lens, nparts, wide);
  pallas_fq_reduce_wide(wide, out);
  memzero(wide, sizeof(wide));
}

void pallas_spend_auth_sign_full(const uint8_t ask[32], const uint8_t alpha[32],
                                 const uint8_t *msg, size_t msg_len,
                                 pallas_point *commit_pt, pallas_point *rk_pt,
                                 uint8_t commit_out[32], uint8_t rk_out[32],
                                 uint8_t response_out[32]) {
  // rsk = ask + alpha
  uint8_t rsk[32];
  pallas_scalar_add(ask, alpha, rsk);

  // mask = ToScalar(H(rsk || msg))
  uint8_t mask[32];
  {
    const uint8_t *parts[2] = {rsk, msg};
    size_t lens[2] = {32, msg_len};
    schnorr_hash_to_scalar(parts, lens, 2, mask);
  }

  // commit = mask * NullifierK ; rk = rsk * NullifierK
  pallas_point_mul(mask, &pallas_nullifier_k, commit_pt);
  pallas_point_mul(rsk, &pallas_nullifier_k, rk_pt);
  pallas_point_to_bytes(commit_pt, commit_out);
  pallas_point_to_bytes(rk_pt, rk_out);

  // challenge = ToScalar(H(commit || rk || msg))
  uint8_t challenge[32];
  {
    const uint8_t *parts[3] = {commit_out, rk_out, msg};
    size_t lens[3] = {32, 32, msg_len};
    schnorr_hash_to_scalar(parts, lens, 3, challenge);
  }

  // response = mask + challenge * rsk
  uint8_t cr[32];
  pallas_scalar_mul(challenge, rsk, cr);
  pallas_scalar_add(mask, cr, response_out);

  memzero(rsk, sizeof(rsk));
  memzero(mask, sizeof(mask));
  memzero(challenge, sizeof(challenge));
  memzero(cr, sizeof(cr));
}

void pallas_spend_auth_sign(const uint8_t ask[32], const uint8_t alpha[32],
                            const uint8_t *msg, size_t msg_len,
                            uint8_t commit_out[32], uint8_t rk_out[32],
                            uint8_t response_out[32]) {
  pallas_point commit_pt, rk_pt;
  pallas_spend_auth_sign_full(ask, alpha, msg, msg_len, &commit_pt, &rk_pt,
                              commit_out, rk_out, response_out);
  memzero(&commit_pt, sizeof(commit_pt));
  memzero(&rk_pt, sizeof(rk_pt));
}

int pallas_spend_auth_verify_full(const pallas_point *commit_pt,
                                  const pallas_point *rk_pt,
                                  const uint8_t commit_enc[32],
                                  const uint8_t rk_enc[32],
                                  const uint8_t response[32],
                                  const uint8_t *msg, size_t msg_len) {
  // challenge = ToScalar(H(commit || rk || msg))
  uint8_t challenge[32];
  const uint8_t *parts[3] = {commit_enc, rk_enc, msg};
  size_t lens[3] = {32, 32, msg_len};
  schnorr_hash_to_scalar(parts, lens, 3, challenge);

  // lhs = response * NullifierK ; check lhs == commit + challenge * rk
  pallas_point lhs, crk, rhs;
  pallas_point_mul(response, &pallas_nullifier_k, &lhs);
  pallas_point_mul(challenge, rk_pt, &crk);
  pallas_point_add(commit_pt, &crk, &rhs);

  uint8_t a[32], b[32];
  pallas_point_to_bytes(&lhs, a);
  pallas_point_to_bytes(&rhs, b);
  int ok = memcmp(a, b, 32) == 0;

  memzero(challenge, sizeof(challenge));
  memzero(&lhs, sizeof(lhs));
  memzero(&crk, sizeof(crk));
  memzero(&rhs, sizeof(rhs));
  return ok;
}

void pallas_drk_derive_ak(const uint8_t sk[32], uint8_t ak_out[32]) {
  uint8_t ask[32];
  pallas_drk_derive_ask(sk, ask);
  pallas_point ak;
  pallas_point_mul(ask, &pallas_nullifier_k, &ak);  // ak = ask * NullifierK
  pallas_point_to_bytes(&ak, ak_out);
  memzero(ask, sizeof(ask));
  memzero(&ak, sizeof(ak));
}

void pallas_drk_derive_pk_d(const uint8_t ivk[32], uint8_t pk_d_out[32]) {
  // pk_d = ivk * NullifierK (PublicKey::from_secret(ivk)).
  pallas_point pk_d;
  pallas_point_mul(ivk, &pallas_nullifier_k, &pk_d);
  pallas_point_to_bytes(&pk_d, pk_d_out);
  memzero(&pk_d, sizeof(pk_d));
}

void pallas_drk_derive_ivk_from_sk(const uint8_t sk[32], uint8_t ivk_out[32]) {
  // ask -> ak (as a point), nk; ivk = ToBase(poseidon([ak_x, ak_y, nk])).
  uint8_t ask[32], nk[32];
  pallas_drk_derive_ask(sk, ask);
  pallas_drk_derive_nk(sk, nk);

  pallas_point ak;
  pallas_point_mul(ask, &pallas_nullifier_k, &ak);  // ak = ask * NullifierK

  uint8_t ak_x[32], ak_y[32];
  pallas_fp_to_bytes(&ak.x, ak_x);
  pallas_fp_to_bytes(&ak.y, ak_y);

  // ivk = poseidon_hash([ak_x, ak_y, nk]) is kept as a base-field element (a
  // stock DarkFi SecretKey), so the canonical LE bytes are copied directly.
  uint8_t h[32];
  pallas_poseidon_hash3(ak_x, ak_y, nk, h);
  memcpy(ivk_out, h, 32);

  memzero(ask, sizeof(ask));
  memzero(nk, sizeof(nk));
  memzero(&ak, sizeof(ak));
  memzero(ak_x, sizeof(ak_x));
  memzero(ak_y, sizeof(ak_y));
  memzero(h, sizeof(h));
}
