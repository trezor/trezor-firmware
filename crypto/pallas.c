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

#include "pallas.h"

#include <string.h>

#include "memzero.h"

// All constants are generated from DarkFi's Rust and validated against
// doc/src/dev/trezor_drk_test_vectors.md via:
//   cargo test -p darkfi-sdk trezor_pallas_montgomery -- --ignored --nocapture
// Limbs are little-endian (limb[0] = least-significant 32 bits).

// F_p base-field modulus.
static const uint32_t FP_MOD[8] = {0x00000001, 0x992d30ed, 0x094cf91b,
                                   0x224698fc, 0x00000000, 0x00000000,
                                   0x00000000, 0x40000000};
// R^2 mod p, for to-Montgomery conversion.
static const uint32_t FP_R2[8] = {0x0000000f, 0x8c78ecb3, 0x8b0de0e7,
                                  0xd7d30dbd, 0xc3c95d18, 0x7797a99b,
                                  0x7b9cb714, 0x096d41af};

// F_q scalar-field modulus (= curve group order).
static const uint32_t FQ_MOD[8] = {0x00000001, 0x8c46eb21, 0x0994a8dd,
                                   0x224698fc, 0x00000000, 0x00000000,
                                   0x00000000, 0x40000000};
static const uint32_t FQ_R2[8] = {0x0000000f, 0xfc9678ff, 0x891a16e3,
                                  0x67bb433d, 0x04ccf590, 0x7fae2310,
                                  0x7ccfdaa9, 0x096d41af};

// -p^-1 mod 2^32 == -q^-1 mod 2^32 == 0xffffffff (both moduli end in ...0001).
static const uint32_t MONT_INV = 0xffffffff;

// SpendAuthG and NullifierK generators, coordinates in Montgomery form.
const pallas_point pallas_spend_auth_g = {
    /*.x =*/{{0x0abc8698, 0x490f248c, 0x3afc5a4a, 0x8f66e9e5, 0x35fe217d,
              0x8a4b3d04, 0x32c10d0b, 0x1088a0c6}},
    /*.y =*/{{0x3de44a97, 0xe6900acd, 0x2f7b5e04, 0x24ecf6ed, 0x1a7b961d,
              0x79d25b84, 0xfe9c580b, 0x0cfbbe1e}},
    /*.infinity =*/0};

const pallas_point pallas_nullifier_k = {
    /*.x =*/{{0x4b65bba8, 0x59aff11e, 0x6527fdf0, 0x2ce954cd, 0xe958b563,
              0x8be41ed4, 0xc690e3af, 0x1941927d}},
    /*.y =*/{{0x2c64e600, 0xa091d810, 0x8f910b8f, 0x8e4181b0, 0x2911a5df,
              0x665c3997, 0x3a3cf88b, 0x31799e1e}},
    /*.infinity =*/0};

// ---- limb <-> byte helpers --------------------------------------------

static void bytes_to_limbs(const uint8_t in[32], uint32_t out[8]) {
  for (int i = 0; i < 8; i++) {
    out[i] = (uint32_t)in[4 * i] | ((uint32_t)in[4 * i + 1] << 8) |
             ((uint32_t)in[4 * i + 2] << 16) | ((uint32_t)in[4 * i + 3] << 24);
  }
}

static void limbs_to_bytes(const uint32_t in[8], uint8_t out[32]) {
  for (int i = 0; i < 8; i++) {
    out[4 * i] = in[i] & 0xff;
    out[4 * i + 1] = (in[i] >> 8) & 0xff;
    out[4 * i + 2] = (in[i] >> 16) & 0xff;
    out[4 * i + 3] = (in[i] >> 24) & 0xff;
  }
}

// ---- core modular arithmetic (constant-time conditional reductions) ----

// CIOS Montgomery multiplication: out = a * b * R^-1 mod n, R = 2^256.
// Correct whenever at least one of a, b is < n (the result is then < 2n and one
// conditional subtraction suffices). Operands and output are 8x32-bit LE limbs.
static void mont_mul(const uint32_t a[8], const uint32_t b[8],
                     const uint32_t n[8], uint32_t out[8]) {
  uint32_t t[10] = {0};  // s + 2 = 10 words
  for (int i = 0; i < 8; i++) {
    uint64_t c = 0;
    for (int j = 0; j < 8; j++) {
      uint64_t s = (uint64_t)t[j] + (uint64_t)a[j] * b[i] + c;
      t[j] = (uint32_t)s;
      c = s >> 32;
    }
    uint64_t s = (uint64_t)t[8] + c;
    t[8] = (uint32_t)s;
    t[9] = (uint32_t)(s >> 32);

    uint32_t m = (uint32_t)((uint64_t)t[0] * MONT_INV);
    (void)n;  // MONT_INV already encodes -n^-1 mod 2^32
    s = (uint64_t)t[0] + (uint64_t)m * n[0];
    c = s >> 32;
    for (int j = 1; j < 8; j++) {
      s = (uint64_t)t[j] + (uint64_t)m * n[j] + c;
      t[j - 1] = (uint32_t)s;
      c = s >> 32;
    }
    s = (uint64_t)t[8] + c;
    t[7] = (uint32_t)s;
    t[8] = t[9] + (uint32_t)(s >> 32);
  }

  // Final conditional subtraction: if (t[0..8]) >= n then subtract n.
  uint32_t r[8];
  uint32_t borrow = 0;
  for (int j = 0; j < 8; j++) {
    uint64_t d = (uint64_t)t[j] - n[j] - borrow;
    r[j] = (uint32_t)d;
    borrow = (uint32_t)((d >> 32) & 1);
  }
  uint64_t d = (uint64_t)t[8] - borrow;
  borrow = (uint32_t)((d >> 32) & 1);
  uint32_t mask = borrow - 1;  // 0xffffffff if t>=n (use r), else 0
  for (int j = 0; j < 8; j++) {
    out[j] = (r[j] & mask) | (t[j] & ~mask);
  }
  memzero(t, sizeof(t));
  memzero(r, sizeof(r));
}

// out = a + b mod n (a, b < n).
static void add_mod(const uint32_t a[8], const uint32_t b[8],
                    const uint32_t n[8], uint32_t out[8]) {
  uint32_t t[9];
  uint64_t c = 0;
  for (int j = 0; j < 8; j++) {
    uint64_t s = (uint64_t)a[j] + b[j] + c;
    t[j] = (uint32_t)s;
    c = s >> 32;
  }
  t[8] = (uint32_t)c;
  uint32_t r[8];
  uint32_t borrow = 0;
  for (int j = 0; j < 8; j++) {
    uint64_t dd = (uint64_t)t[j] - n[j] - borrow;
    r[j] = (uint32_t)dd;
    borrow = (uint32_t)((dd >> 32) & 1);
  }
  uint64_t dd = (uint64_t)t[8] - borrow;
  borrow = (uint32_t)((dd >> 32) & 1);
  uint32_t mask = borrow - 1;
  for (int j = 0; j < 8; j++) {
    out[j] = (r[j] & mask) | (t[j] & ~mask);
  }
}

// out = a - b mod n (a, b < n).
static void sub_mod(const uint32_t a[8], const uint32_t b[8],
                    const uint32_t n[8], uint32_t out[8]) {
  uint32_t r[8];
  uint32_t borrow = 0;
  for (int j = 0; j < 8; j++) {
    uint64_t dd = (uint64_t)a[j] - b[j] - borrow;
    r[j] = (uint32_t)dd;
    borrow = (uint32_t)((dd >> 32) & 1);
  }
  uint32_t mask = 0u - borrow;  // 0xffffffff if a<b
  uint64_t c = 0;
  for (int j = 0; j < 8; j++) {
    uint64_t s = (uint64_t)r[j] + (n[j] & mask) + c;
    out[j] = (uint32_t)s;
    c = s >> 32;
  }
}

static int limbs_is_zero(const uint32_t a[8]) {
  uint32_t acc = 0;
  for (int j = 0; j < 8; j++) acc |= a[j];
  return acc == 0;
}

// Constant-time conditional move of a field element: if flag (0/1), r = a.
static void fe_cmov(pallas_fe *r, const pallas_fe *a, uint32_t flag) {
  uint32_t mask = 0u - (flag & 1u);  // 0x00000000 or 0xffffffff
  for (int j = 0; j < 8; j++) {
    r->v[j] = (r->v[j] & ~mask) | (a->v[j] & mask);
  }
}

// ---- F_p public API ----------------------------------------------------

void pallas_fp_add(const pallas_fe *a, const pallas_fe *b, pallas_fe *out) {
  add_mod(a->v, b->v, FP_MOD, out->v);
}
void pallas_fp_sub(const pallas_fe *a, const pallas_fe *b, pallas_fe *out) {
  sub_mod(a->v, b->v, FP_MOD, out->v);
}
void pallas_fp_mul(const pallas_fe *a, const pallas_fe *b, pallas_fe *out) {
  mont_mul(a->v, b->v, FP_MOD, out->v);
}

void pallas_fp_from_bytes(const uint8_t in[32], pallas_fe *out) {
  uint32_t a[8];
  bytes_to_limbs(in, a);
  mont_mul(a, FP_R2, FP_MOD, out->v);  // a -> a*R mod p
  memzero(a, sizeof(a));
}

void pallas_fp_to_bytes(const pallas_fe *a, uint8_t out[32]) {
  static const uint32_t ONE[8] = {1, 0, 0, 0, 0, 0, 0, 0};
  uint32_t r[8];
  mont_mul(a->v, ONE, FP_MOD, r);  // a*R * 1 * R^-1 = a
  limbs_to_bytes(r, out);
  memzero(r, sizeof(r));
}

int pallas_fp_is_zero(const pallas_fe *a) { return limbs_is_zero(a->v); }

int pallas_fp_is_odd(const pallas_fe *a) {
  uint8_t b[32];
  pallas_fp_to_bytes(a, b);
  int odd = b[0] & 1;
  memzero(b, sizeof(b));
  return odd;
}

// out = a^-1 mod p via Fermat: a^(p-2). Inputs/outputs in Montgomery form.
void pallas_fp_inv(const pallas_fe *a, pallas_fe *out) {
  // exponent e = p - 2 (p ends in ...0001, so only the low limbs borrow).
  uint32_t e[8];
  uint32_t borrow = 2;
  for (int j = 0; j < 8; j++) {
    uint64_t d = (uint64_t)FP_MOD[j] - borrow;
    e[j] = (uint32_t)d;
    borrow = (uint32_t)((d >> 32) & 1);
  }

  // result = Montgomery 1 = R mod p = mont_mul(1, R2).
  static const uint32_t ONE[8] = {1, 0, 0, 0, 0, 0, 0, 0};
  pallas_fe result;
  mont_mul(ONE, FP_R2, FP_MOD, result.v);
  pallas_fe base = *a;

  for (int i = 255; i >= 0; i--) {
    pallas_fp_mul(&result, &result, &result);  // square
    uint32_t bit = (e[i >> 5] >> (i & 31)) & 1;
    if (bit) {
      pallas_fp_mul(&result, &base, &result);
    }
  }
  *out = result;
  memzero(&base, sizeof(base));
  memzero(e, sizeof(e));
}

// ---- F_q public API ----------------------------------------------------

void pallas_fq_add(const pallas_fe *a, const pallas_fe *b, pallas_fe *out) {
  add_mod(a->v, b->v, FQ_MOD, out->v);
}
void pallas_fq_mul(const pallas_fe *a, const pallas_fe *b, pallas_fe *out) {
  mont_mul(a->v, b->v, FQ_MOD, out->v);
}
void pallas_fq_from_bytes(const uint8_t in[32], pallas_fe *out) {
  uint32_t a[8];
  bytes_to_limbs(in, a);
  mont_mul(a, FQ_R2, FQ_MOD, out->v);
  memzero(a, sizeof(a));
}
void pallas_fq_to_bytes(const pallas_fe *a, uint8_t out[32]) {
  static const uint32_t ONE[8] = {1, 0, 0, 0, 0, 0, 0, 0};
  uint32_t r[8];
  mont_mul(a->v, ONE, FQ_MOD, r);
  limbs_to_bytes(r, out);
  memzero(r, sizeof(r));
}

// Reduce a 512-bit little-endian integer mod q into Montgomery form. This is
// the from_uniform_bytes / hash-to-scalar primitive (BLAKE2b-512 digest -> F_q).
//
// Write in = lo + hi*2^256 with lo, hi < 2^256 and R = 2^256. We want the
// Montgomery image out = (in mod q) * R = in * R = lo*R + hi*R^2 (mod q).
// With mont_mul(x, R2) = x * R2 * R^-1 = x * R:
//   lo*R   = mont_mul(lo, R2)
//   hi*R^2 = mont_mul(mont_mul(hi, R2), R2)   // (hi*R) then * R again
void pallas_fq_from_wide_bytes(const uint8_t in[64], pallas_fe *out) {
  uint32_t lo[8], hi[8];
  bytes_to_limbs(in, lo);
  bytes_to_limbs(in + 32, hi);

  pallas_fe mlo, mhi;
  mont_mul(lo, FQ_R2, FQ_MOD, mlo.v);      // lo * R
  mont_mul(hi, FQ_R2, FQ_MOD, mhi.v);      // hi * R
  mont_mul(mhi.v, FQ_R2, FQ_MOD, mhi.v);   // (hi * R) * R = hi * R^2
  add_mod(mlo.v, mhi.v, FQ_MOD, out->v);

  memzero(lo, sizeof(lo));
  memzero(hi, sizeof(hi));
  memzero(&mlo, sizeof(mlo));
  memzero(&mhi, sizeof(mhi));
}

// Reduce 64-byte LE integer mod q, return canonical 32-byte LE (ToScalar).
void pallas_fq_reduce_wide(const uint8_t in[64], uint8_t out[32]) {
  pallas_fe m;
  pallas_fq_from_wide_bytes(in, &m);
  pallas_fq_to_bytes(&m, out);
  memzero(&m, sizeof(m));
}

// Reduce 64-byte LE integer mod p, return canonical 32-byte LE (ToBase).
void pallas_fp_from_wide_bytes(const uint8_t in[64], uint8_t out[32]) {
  uint32_t lo[8], hi[8];
  bytes_to_limbs(in, lo);
  bytes_to_limbs(in + 32, hi);

  pallas_fe mlo, mhi;
  mont_mul(lo, FP_R2, FP_MOD, mlo.v);      // lo * R
  mont_mul(hi, FP_R2, FP_MOD, mhi.v);      // hi * R
  mont_mul(mhi.v, FP_R2, FP_MOD, mhi.v);   // hi * R^2
  pallas_fe sum;
  add_mod(mlo.v, mhi.v, FP_MOD, sum.v);
  pallas_fp_to_bytes(&sum, out);

  memzero(lo, sizeof(lo));
  memzero(hi, sizeof(hi));
  memzero(&mlo, sizeof(mlo));
  memzero(&mhi, sizeof(mhi));
  memzero(&sum, sizeof(sum));
}

// ---- F_q scalar helpers (canonical bytes in/out) ----------------------

void pallas_scalar_add(const uint8_t a[32], const uint8_t b[32],
                       uint8_t out[32]) {
  uint32_t la[8], lb[8], lr[8];
  bytes_to_limbs(a, la);
  bytes_to_limbs(b, lb);
  add_mod(la, lb, FQ_MOD, lr);  // both < q
  limbs_to_bytes(lr, out);
  memzero(la, sizeof(la));
  memzero(lb, sizeof(lb));
  memzero(lr, sizeof(lr));
}

void pallas_scalar_mul(const uint8_t a[32], const uint8_t b[32],
                       uint8_t out[32]) {
  pallas_fe ma, mb, mr;
  pallas_fq_from_bytes(a, &ma);  // a*R
  pallas_fq_from_bytes(b, &mb);  // b*R
  mont_mul(ma.v, mb.v, FQ_MOD, mr.v);  // a*b*R
  pallas_fq_to_bytes(&mr, out);        // a*b
  memzero(&ma, sizeof(ma));
  memzero(&mb, sizeof(mb));
  memzero(&mr, sizeof(mr));
}

// ---- Curve (complete projective formulas, constant-time) --------------
//
// Homogeneous projective coordinates (X:Y:Z); the affine point is (X/Z, Y/Z)
// and the identity is (0:1:0). We use the Renes-Costello-Batina (2015) complete
// addition formulas for short-Weierstrass curves with a = 0 (Algorithm 7), which
// are exception-free: the same code correctly handles P+Q, P+P, P+(-P) and the
// identity, with no input-dependent branches. b3 = 3*b = 15.

typedef struct {
  pallas_fe x, y, z;
} proj;

// b3 = 15 in Montgomery form, initialized once.
static pallas_fe PROJ_B3;
static int PROJ_B3_READY = 0;
static void proj_init(void) {
  if (!PROJ_B3_READY) {
    uint8_t fifteen[32] = {15};
    pallas_fp_from_bytes(fifteen, &PROJ_B3);
    PROJ_B3_READY = 1;
  }
}

static void proj_set_identity(proj *p) {
  memzero(&p->x, sizeof(p->x));
  uint8_t one[32] = {1};
  pallas_fp_from_bytes(one, &p->y);
  memzero(&p->z, sizeof(p->z));
}

static void affine_to_proj(const pallas_point *a, proj *p) {
  if (a->infinity) {
    proj_set_identity(p);
    return;
  }
  p->x = a->x;
  p->y = a->y;
  uint8_t one[32] = {1};
  pallas_fp_from_bytes(one, &p->z);  // Z = 1
}

// Complete addition: out = p + q. RCB 2015, Algorithm 7 (a = 0).
static void proj_add(const proj *p, const proj *q, proj *out) {
  pallas_fe t0, t1, t2, t3, t4, x3, y3, z3;
  pallas_fp_mul(&p->x, &q->x, &t0);  // t0 = X1*X2
  pallas_fp_mul(&p->y, &q->y, &t1);  // t1 = Y1*Y2
  pallas_fp_mul(&p->z, &q->z, &t2);  // t2 = Z1*Z2
  pallas_fp_add(&p->x, &p->y, &t3);  // t3 = X1+Y1
  pallas_fp_add(&q->x, &q->y, &t4);  // t4 = X2+Y2
  pallas_fp_mul(&t3, &t4, &t3);      // t3 = (X1+Y1)*(X2+Y2)
  pallas_fp_add(&t0, &t1, &t4);      // t4 = t0+t1
  pallas_fp_sub(&t3, &t4, &t3);      // t3 = t3 - t4
  pallas_fp_add(&p->y, &p->z, &t4);  // t4 = Y1+Z1
  pallas_fp_add(&q->y, &q->z, &x3);  // x3 = Y2+Z2
  pallas_fp_mul(&t4, &x3, &t4);      // t4 = (Y1+Z1)*(Y2+Z2)
  pallas_fp_add(&t1, &t2, &x3);      // x3 = t1+t2
  pallas_fp_sub(&t4, &x3, &t4);      // t4 = t4 - x3
  pallas_fp_add(&p->x, &p->z, &x3);  // x3 = X1+Z1
  pallas_fp_add(&q->x, &q->z, &y3);  // y3 = X2+Z2
  pallas_fp_mul(&x3, &y3, &x3);      // x3 = (X1+Z1)*(X2+Z2)
  pallas_fp_add(&t0, &t2, &y3);      // y3 = t0+t2
  pallas_fp_sub(&x3, &y3, &y3);      // y3 = x3 - y3
  // a = 0 path:
  pallas_fp_add(&t0, &t0, &x3);      // x3 = t0+t0
  pallas_fp_add(&x3, &t0, &t0);      // t0 = x3+t0  (= 3*X1X2)
  pallas_fp_mul(&PROJ_B3, &t2, &t2); // t2 = b3*t2
  pallas_fp_add(&t1, &t2, &z3);      // z3 = t1+t2
  pallas_fp_sub(&t1, &t2, &t1);      // t1 = t1-t2
  pallas_fp_mul(&PROJ_B3, &y3, &y3); // y3 = b3*y3
  pallas_fp_mul(&t4, &y3, &x3);      // x3 = t4*y3
  pallas_fp_mul(&t3, &t1, &t2);      // t2 = t3*t1
  pallas_fp_sub(&t2, &x3, &x3);      // x3 = t2-x3
  pallas_fp_mul(&y3, &t0, &y3);      // y3 = y3*t0
  pallas_fp_mul(&t1, &z3, &t1);      // t1 = t1*z3
  pallas_fp_add(&t1, &y3, &y3);      // y3 = t1+y3
  pallas_fp_mul(&t0, &t3, &t0);      // t0 = t0*t3
  pallas_fp_mul(&z3, &t4, &z3);      // z3 = z3*t4
  pallas_fp_add(&z3, &t0, &z3);      // z3 = z3+t0
  out->x = x3;
  out->y = y3;
  out->z = z3;
}

// Constant-time conditional move of a projective point.
static void proj_cmov(proj *r, const proj *a, uint32_t flag) {
  fe_cmov(&r->x, &a->x, flag);
  fe_cmov(&r->y, &a->y, flag);
  fe_cmov(&r->z, &a->z, flag);
}

static void proj_to_affine(const proj *p, pallas_point *out) {
  // If Z == 0, the point is the identity.
  if (pallas_fp_is_zero(&p->z)) {
    memzero(out, sizeof(*out));
    out->infinity = 1;
    return;
  }
  pallas_fe zinv;
  pallas_fp_inv(&p->z, &zinv);
  pallas_fp_mul(&p->x, &zinv, &out->x);
  pallas_fp_mul(&p->y, &zinv, &out->y);
  out->infinity = 0;
  memzero(&zinv, sizeof(zinv));
}

void pallas_point_set_infinity(pallas_point *p) {
  memzero(p, sizeof(*p));
  p->infinity = 1;
}

void pallas_point_add(const pallas_point *a, const pallas_point *b,
                      pallas_point *out) {
  proj_init();
  proj pa, pb, pr;
  affine_to_proj(a, &pa);
  affine_to_proj(b, &pb);
  proj_add(&pa, &pb, &pr);
  proj_to_affine(&pr, out);
}

void pallas_point_double(const pallas_point *a, pallas_point *out) {
  proj_init();
  proj pa, pr;
  affine_to_proj(a, &pa);
  proj_add(&pa, &pa, &pr);  // complete formula doubles correctly
  proj_to_affine(&pr, out);
}

// out = k * p. Constant-time double-and-add, most-significant bit first.
//
// We deliberately avoid the classic windowed method with a precomputed
// `table[16]` of projective points: at sizeof(proj) == 96 bytes that table is
// 1.5 KB on the stack, which overflows the device's small (16 KB) MicroPython
// C stack once the async/protobuf/UI frames are accounted for, hard-faulting
// the firmware. A plain bit-at-a-time ladder needs only a handful of `proj`
// temporaries (a few hundred bytes), comfortably within budget, at the cost of
// ~4x more point additions (still a few milliseconds for one scalar mul).
//
// Constant-time properties:
//   - every bit performs exactly one doubling and one addition, using the
//     complete (exception-free) RCB formula, with no identity short-circuit,
//   - the added point is chosen by a constant-time cmov between P and the
//     identity, so there is no secret-dependent branch or memory index.
void pallas_point_mul(const uint8_t k[32], const pallas_point *p,
                      pallas_point *out) {
  proj_init();

  proj pp;
  affine_to_proj(p, &pp);

  proj acc;
  proj_set_identity(&acc);

  for (int i = 255; i >= 0; i--) {
    // acc = 2 * acc
    proj dbl;
    proj_add(&acc, &acc, &dbl);
    acc = dbl;

    // sel = bit ? P : identity  (constant-time conditional move)
    uint32_t bit = (k[i >> 3] >> (i & 7)) & 1;
    proj sel;
    proj_set_identity(&sel);
    proj_cmov(&sel, &pp, bit);

    // acc = acc + sel
    proj r;
    proj_add(&acc, &sel, &r);
    acc = r;

    memzero(&sel, sizeof(sel));
  }

  proj_to_affine(&acc, out);
  memzero(&acc, sizeof(acc));
  memzero(&pp, sizeof(pp));
}

void pallas_point_neg(const pallas_point *p, pallas_point *out) {
  if (p->infinity) {
    pallas_point_set_infinity(out);
    return;
  }
  out->x = p->x;
  // -y = 0 - y mod p
  pallas_fe zero;
  memzero(&zero, sizeof(zero));
  pallas_fp_sub(&zero, &p->y, &out->y);
  out->infinity = 0;
}

void pallas_point_to_bytes(const pallas_point *p, uint8_t out[32]) {
  if (p->infinity) {
    memzero(out, 32);
    return;
  }
  pallas_fp_to_bytes(&p->x, out);
  if (pallas_fp_is_odd(&p->y)) {
    out[31] |= 0x80;
  }
}

void pallas_spend_auth_pubkey(const uint8_t ask[32], uint8_t ak_out[32]) {
  // ak = ask * NullifierK (the generator used by PublicKey and schnorr.rs).
  pallas_point ak;
  pallas_point_mul(ask, &pallas_nullifier_k, &ak);
  pallas_point_to_bytes(&ak, ak_out);
  memzero(&ak, sizeof(ak));
}
