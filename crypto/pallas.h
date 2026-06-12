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

// Pallas curve (y^2 = x^3 + 5) support for DarkFi DRK on-device key custody.
//
// Pallas is one of the two Pasta curves. Its base field F_p and scalar field
// F_q are both ~2^254, which is *below* the secp256k1-sized window that Trezor's
// bignum.c fast-reduction assumes (2^256 - 2^224 <= prime <= 2^256). We
// therefore implement self-contained constant-time CIOS Montgomery arithmetic
// here instead of reusing bignum.c / ecdsa.c for the field layer.
//
// Field elements are 8 x 32-bit limbs, little-endian (limb[0] is least
// significant), held in Montgomery form (value * R mod n, R = 2^256). All
// constants are generated from DarkFi's Rust and validated against
// doc/src/dev/trezor_drk_test_vectors.md.

#ifndef __PALLAS_H__
#define __PALLAS_H__

#include <stddef.h>
#include <stdint.h>

#define PALLAS_LIMBS 8

// A field element: 8 x 32-bit little-endian limbs, in Montgomery form.
typedef struct {
  uint32_t v[PALLAS_LIMBS];
} pallas_fe;

// An affine curve point. `infinity != 0` marks the point at infinity, in which
// case x and y are unspecified.
typedef struct {
  pallas_fe x;
  pallas_fe y;
  int infinity;
} pallas_point;

// --- F_p (base field) ---------------------------------------------------
// out = a + b, a - b, a * b (mod p), with a,b,out in Montgomery form.
void pallas_fp_add(const pallas_fe *a, const pallas_fe *b, pallas_fe *out);
void pallas_fp_sub(const pallas_fe *a, const pallas_fe *b, pallas_fe *out);
void pallas_fp_mul(const pallas_fe *a, const pallas_fe *b, pallas_fe *out);
// out = a^-1 mod p (out=0 if a=0).
void pallas_fp_inv(const pallas_fe *a, pallas_fe *out);
// Convert to/from Montgomery form and 32-byte little-endian canonical bytes.
void pallas_fp_from_bytes(const uint8_t in[32], pallas_fe *out);
void pallas_fp_to_bytes(const pallas_fe *a, uint8_t out[32]);
int pallas_fp_is_zero(const pallas_fe *a);
int pallas_fp_is_odd(const pallas_fe *a);  // parity of the canonical integer

// --- F_q (scalar field) -------------------------------------------------
void pallas_fq_add(const pallas_fe *a, const pallas_fe *b, pallas_fe *out);
void pallas_fq_mul(const pallas_fe *a, const pallas_fe *b, pallas_fe *out);
void pallas_fq_from_bytes(const uint8_t in[32], pallas_fe *out);
void pallas_fq_to_bytes(const pallas_fe *a, uint8_t out[32]);
// Reduce a 64-byte little-endian integer mod q into Montgomery form (the
// "from_uniform_bytes" / hash-to-scalar primitive).
void pallas_fq_from_wide_bytes(const uint8_t in[64], pallas_fe *out);

// --- Curve --------------------------------------------------------------
// The two DarkFi fixed-base generators.
extern const pallas_point pallas_spend_auth_g;
extern const pallas_point pallas_nullifier_k;

void pallas_point_set_infinity(pallas_point *p);
void pallas_point_add(const pallas_point *a, const pallas_point *b,
                      pallas_point *out);
void pallas_point_double(const pallas_point *a, pallas_point *out);
// out = k * p, with k a 32-byte little-endian scalar (canonical, < q).
void pallas_point_mul(const uint8_t k[32], const pallas_point *p,
                      pallas_point *out);
// DarkFi GroupEncoding::to_bytes: 32-byte LE x, top bit of byte[31] = y parity.
void pallas_point_to_bytes(const pallas_point *p, uint8_t out[32]);

// --- Poseidon P128Pow5T3 over F_p --------------------------------------
// Hash of two field elements (the DarkFi poseidon_hash([a, b]) primitive, used
// for coin commitments, nullifiers, and ivk). Inputs/outputs are 32-byte
// little-endian canonical F_p elements.
void pallas_poseidon_hash2(const uint8_t a[32], const uint8_t b[32],
                           uint8_t out[32]);
// Hash of three field elements (poseidon_hash([a, b, c]), used for ivk).
void pallas_poseidon_hash3(const uint8_t a[32], const uint8_t b[32],
                           const uint8_t c[32], uint8_t out[32]);

// Reduce a 64-byte little-endian integer mod p into a canonical F_p element
// (the from_uniform_bytes primitive for the base field).
void pallas_fp_from_wide_bytes(const uint8_t in[64], uint8_t out[32]);
// Same, mod q, returning canonical 32-byte LE (scalar from_uniform_bytes).
void pallas_fq_reduce_wide(const uint8_t in[64], uint8_t out[32]);

// --- DarkFi HD derivation (hd.rs) --------------------------------------
// Hierarchical-deterministic spend keys, mirroring ZIP-32 for Orchard. Every
// node is a (sk, chain_code) pair. Derivation is hardened-only: the child PRF
// always mixes in the parent secret.
//
//   master:    sk = ToBase(BLAKE2b("DarkFi:HDKey",   seed))
//              cc =        BLAKE2b("DarkFi:HDChain",  seed)
//   child(i):  sk'= ToBase(BLAKE2b("DarkFi:HDKey",   cc||sk||(i|2^31)_le))
//              cc'=        BLAKE2b("DarkFi:HDChain",  cc||sk||(i|2^31)_le)
//   account(seed, i) = child(i).sk     (single-level layout drk uses)
//
// `seed` is opaque entropy (wallets pass the 64-byte BIP-39 seed).
void pallas_hd_master(const uint8_t *seed, size_t seed_len, uint8_t sk_out[32],
                      uint8_t cc_out[32]);
void pallas_hd_child(const uint8_t sk[32], const uint8_t cc[32], uint32_t index,
                     uint8_t sk_out[32], uint8_t cc_out[32]);
void pallas_hd_account(const uint8_t *seed, size_t seed_len, uint32_t account,
                       uint8_t sk_out[32]);

// --- DarkFi key derivation (Orchard-style hierarchy) -------------------
// All derivations use BLAKE2b with a <=16-byte personalization, matching
// DarkFi's blake2b_simd Params::personal(...).
//
// ask = ToScalar(Expand(sk, 0x06)),  nk = ToBase(Expand(sk, 0x07))
// where Expand(sk, t) = BLAKE2b-512(personal="DarkFi:Expand", msg = sk_le || t).
void pallas_drk_derive_ask(const uint8_t sk[32], uint8_t ask_out[32]);
void pallas_drk_derive_nk(const uint8_t sk[32], uint8_t nk_out[32]);

// ak = ask * NullifierK, the spend-auth public key (part of the FVK), as a
// 32-byte compressed point encoding.
void pallas_drk_derive_ak(const uint8_t sk[32], uint8_t ak_out[32]);

// pk_d = ivk * NullifierK, the address key, as a 32-byte compressed point.
void pallas_drk_derive_pk_d(const uint8_t ivk[32], uint8_t pk_d_out[32]);

// sk -> ivk = poseidon_hash([ak_x, ak_y, nk]) kept as a base-field SecretKey,
// computed from the spend key directly (re-derives ask, ak as a point, and nk).
// Writes 32-byte LE ivk. This is the device-side path that has the full ak.
void pallas_drk_derive_ivk_from_sk(const uint8_t sk[32], uint8_t ivk_out[32]);

// Nullifier nf = poseidon_hash([nk, coin]).
void pallas_drk_nullifier(const uint8_t nk[32], const uint8_t coin[32],
                          uint8_t nf_out[32]);

// --- F_q scalar helpers (for spend-auth signatures) --------------------
// out = a + b mod q, a * b mod q. Inputs/outputs are 32-byte LE canonical.
void pallas_scalar_add(const uint8_t a[32], const uint8_t b[32],
                       uint8_t out[32]);
void pallas_scalar_mul(const uint8_t a[32], const uint8_t b[32],
                       uint8_t out[32]);

// --- DarkFi spend-authorization signature ------------------------------
// The only operation that uses the secret tier. Given ask (device-only), a
// randomizer alpha, and a message, produce (commit, response) verifiable
// against the randomized key rk = (ask + alpha) * NullifierK by the *unchanged*
// on-chain DarkFi Schnorr verifier (same generator and "DarkFi:Schnorr"
// domain).
//
//   rsk       = ask + alpha
//   mask      = ToScalar(BLAKE2b("DarkFi:Schnorr", rsk || msg))
//   commit    = mask * NullifierK
//   rk        = rsk  * NullifierK
//   challenge = ToScalar(BLAKE2b("DarkFi:Schnorr", commit || rk || msg))
//   response  = mask + challenge * rsk
//
// commit_out and rk_out are 32-byte compressed point encodings; response_out is
// a 32-byte LE scalar. The signer also returns the full commit/rk points (the
// device needs the encodings; the points are exposed so a verifier need not
// decompress — point decompression requires Tonelli-Shanks sqrt which the
// device never needs since it only signs).
void pallas_spend_auth_sign_full(const uint8_t ask[32], const uint8_t alpha[32],
                                 const uint8_t *msg, size_t msg_len,
                                 pallas_point *commit_pt, pallas_point *rk_pt,
                                 uint8_t commit_out[32], uint8_t rk_out[32],
                                 uint8_t response_out[32]);

// Convenience wrapper returning only the wire encodings.
void pallas_spend_auth_sign(const uint8_t ask[32], const uint8_t alpha[32],
                            const uint8_t *msg, size_t msg_len,
                            uint8_t commit_out[32], uint8_t rk_out[32],
                            uint8_t response_out[32]);

// Negate a point: out = -p = (x, -y).
void pallas_point_neg(const pallas_point *p, pallas_point *out);

// Verify a spend-auth signature given the full commit/rk points:
//   response * NullifierK - challenge * rk == commit
// challenge = ToScalar(BLAKE2b("DarkFi:Schnorr", commit_enc || rk_enc || msg)).
// Returns 1 if valid, else 0.
int pallas_spend_auth_verify_full(const pallas_point *commit_pt,
                                  const pallas_point *rk_pt,
                                  const uint8_t commit_enc[32],
                                  const uint8_t rk_enc[32],
                                  const uint8_t response[32],
                                  const uint8_t *msg, size_t msg_len);

// --- DarkFi high-level helper ------------------------------------------
// ak = ask * NullifierK, encoded with pallas_point_to_bytes. `ask` is a
// 32-byte little-endian canonical F_q scalar.
void pallas_spend_auth_pubkey(const uint8_t ask[32], uint8_t ak_out[32]);

#endif
