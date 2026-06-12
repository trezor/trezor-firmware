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

// Poseidon P128Pow5T3 over the Pallas base field, matching DarkFi's
// poseidon_hash (halo2_gadgets ConstantLength domain). Width T=3, rate=2,
// R_F=8, R_P=56, S-box x^5. Used for coin commitments, nullifiers, and ivk.

#include "pallas.h"
#include "pallas_poseidon_constants.h"

#include <string.h>

#include "memzero.h"

// MDS and round constants are stored as raw little-endian limbs; wrap them as
// field elements (they are already in Montgomery form).
static void load_fe(const uint32_t limbs[8], pallas_fe *out) {
  for (int i = 0; i < 8; i++) out->v[i] = limbs[i];
}

// x^5 S-box.
static void sbox(const pallas_fe *x, pallas_fe *out) {
  pallas_fe x2, x4;
  pallas_fp_mul(x, x, &x2);    // x^2
  pallas_fp_mul(&x2, &x2, &x4);  // x^4
  pallas_fp_mul(&x4, x, out);    // x^5
}

// state = MDS * state
static void apply_mds(pallas_fe state[3]) {
  pallas_fe ns[3];
  for (int i = 0; i < 3; i++) {
    pallas_fe acc;
    memzero(&acc, sizeof(acc));  // 0 in Montgomery form is all-zero limbs
    for (int j = 0; j < 3; j++) {
      pallas_fe m, term;
      load_fe(POSEIDON_MDS[i][j], &m);
      pallas_fp_mul(&m, &state[j], &term);
      pallas_fp_add(&acc, &term, &acc);
    }
    ns[i] = acc;
  }
  state[0] = ns[0];
  state[1] = ns[1];
  state[2] = ns[2];
}

static void full_round(pallas_fe state[3], int round) {
  for (int i = 0; i < 3; i++) {
    pallas_fe rc, t;
    load_fe(POSEIDON_RC[round][i], &rc);
    pallas_fp_add(&state[i], &rc, &t);
    sbox(&t, &state[i]);
  }
  apply_mds(state);
}

static void partial_round(pallas_fe state[3], int round) {
  for (int i = 0; i < 3; i++) {
    pallas_fe rc, t;
    load_fe(POSEIDON_RC[round][i], &rc);
    pallas_fp_add(&state[i], &rc, &t);
    state[i] = t;
  }
  // S-box only on the first word.
  pallas_fe s0 = state[0];
  sbox(&s0, &state[0]);
  apply_mds(state);
}

static void permute(pallas_fe state[3]) {
  int round = 0;
  for (int i = 0; i < POSEIDON_HALF_FULL; i++) full_round(state, round++);
  for (int i = 0; i < POSEIDON_PARTIAL_ROUNDS; i++) partial_round(state, round++);
  for (int i = 0; i < POSEIDON_HALF_FULL; i++) full_round(state, round++);
}

// Initial capacity element for ConstantLength<L>: F::from_u128(L << 64), i.e.
// the integer L*2^64, converted to a field element (Montgomery form).
static void capacity_element(uint64_t l, pallas_fe *out) {
  uint8_t le[32] = {0};
  // value = l << 64 -> bytes 8..15 hold l (little-endian).
  for (int i = 0; i < 8; i++) {
    le[8 + i] = (uint8_t)((l >> (8 * i)) & 0xff);
  }
  pallas_fp_from_bytes(le, out);
}

void pallas_poseidon_hash2(const uint8_t a[32], const uint8_t b[32],
                           uint8_t out[32]) {
  pallas_fe state[3];
  // state = [a, b, capacity(2)]; L=2 == RATE, so no padding, single permute.
  pallas_fp_from_bytes(a, &state[0]);
  pallas_fp_from_bytes(b, &state[1]);
  capacity_element(2, &state[2]);
  permute(state);
  pallas_fp_to_bytes(&state[0], out);
  memzero(state, sizeof(state));
}

void pallas_poseidon_hash3(const uint8_t a[32], const uint8_t b[32],
                           const uint8_t c[32], uint8_t out[32]) {
  // L=3, RATE=2: absorb [a,b] -> permute -> absorb [c, pad=0] -> permute.
  pallas_fe state[3];
  pallas_fp_from_bytes(a, &state[0]);
  pallas_fp_from_bytes(b, &state[1]);
  capacity_element(3, &state[2]);
  permute(state);

  // Second block: add c into rate position 0, zero pad into position 1.
  pallas_fe cf;
  pallas_fp_from_bytes(c, &cf);
  pallas_fp_add(&state[0], &cf, &state[0]);
  // padding element is 0 -> state[1] unchanged.
  permute(state);

  pallas_fp_to_bytes(&state[0], out);
  memzero(state, sizeof(state));
  memzero(&cf, sizeof(cf));
}
