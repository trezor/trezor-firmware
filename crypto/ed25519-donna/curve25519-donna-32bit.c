/*
	Public domain by Andrew M. <liquidsun@gmail.com>
	See: https://github.com/floodyberry/curve25519-donna

	32 bit integer curve25519 implementation
*/

#include "ed25519-donna.h"

static const uint32_t reduce_mask_25 = (1 << 25) - 1;
static const uint32_t reduce_mask_26 = (1 << 26) - 1;

/* out = in */
void curve25519_copy(bignum25519 out, const bignum25519 in) {
	out[0] = in[0];
	out[1] = in[1];
	out[2] = in[2];
	out[3] = in[3];
	out[4] = in[4];
	out[5] = in[5];
	out[6] = in[6];
	out[7] = in[7];
	out[8] = in[8];
	out[9] = in[9];
}

/* out = a + b */
void curve25519_add(bignum25519 out, const bignum25519 a, const bignum25519 b) {
	out[0] = a[0] + b[0];
	out[1] = a[1] + b[1];
	out[2] = a[2] + b[2];
	out[3] = a[3] + b[3];
	out[4] = a[4] + b[4];
	out[5] = a[5] + b[5];
	out[6] = a[6] + b[6];
	out[7] = a[7] + b[7];
	out[8] = a[8] + b[8];
	out[9] = a[9] + b[9];
}

void curve25519_add_after_basic(bignum25519 out, const bignum25519 a, const bignum25519 b) {
	uint32_t c = 0;
	out[0] = a[0] + b[0]    ; c = (out[0] >> 26); out[0] &= reduce_mask_26;
	out[1] = a[1] + b[1] + c; c = (out[1] >> 25); out[1] &= reduce_mask_25;
	out[2] = a[2] + b[2] + c; c = (out[2] >> 26); out[2] &= reduce_mask_26;
	out[3] = a[3] + b[3] + c; c = (out[3] >> 25); out[3] &= reduce_mask_25;
	out[4] = a[4] + b[4] + c; c = (out[4] >> 26); out[4] &= reduce_mask_26;
	out[5] = a[5] + b[5] + c; c = (out[5] >> 25); out[5] &= reduce_mask_25;
	out[6] = a[6] + b[6] + c; c = (out[6] >> 26); out[6] &= reduce_mask_26;
	out[7] = a[7] + b[7] + c; c = (out[7] >> 25); out[7] &= reduce_mask_25;
	out[8] = a[8] + b[8] + c; c = (out[8] >> 26); out[8] &= reduce_mask_26;
	out[9] = a[9] + b[9] + c; c = (out[9] >> 25); out[9] &= reduce_mask_25;
	out[0] += 19 * c;
}

void curve25519_add_reduce(bignum25519 out, const bignum25519 a, const bignum25519 b) {
	uint32_t c = 0;
	out[0] = a[0] + b[0]    ; c = (out[0] >> 26); out[0] &= reduce_mask_26;
	out[1] = a[1] + b[1] + c; c = (out[1] >> 25); out[1] &= reduce_mask_25;
	out[2] = a[2] + b[2] + c; c = (out[2] >> 26); out[2] &= reduce_mask_26;
	out[3] = a[3] + b[3] + c; c = (out[3] >> 25); out[3] &= reduce_mask_25;
	out[4] = a[4] + b[4] + c; c = (out[4] >> 26); out[4] &= reduce_mask_26;
	out[5] = a[5] + b[5] + c; c = (out[5] >> 25); out[5] &= reduce_mask_25;
	out[6] = a[6] + b[6] + c; c = (out[6] >> 26); out[6] &= reduce_mask_26;
	out[7] = a[7] + b[7] + c; c = (out[7] >> 25); out[7] &= reduce_mask_25;
	out[8] = a[8] + b[8] + c; c = (out[8] >> 26); out[8] &= reduce_mask_26;
	out[9] = a[9] + b[9] + c; c = (out[9] >> 25); out[9] &= reduce_mask_25;
	out[0] += 19 * c;
}

/* multiples of p */
static const uint32_t twoP0       = 0x07ffffda;
static const uint32_t twoP13579   = 0x03fffffe;
static const uint32_t twoP2468    = 0x07fffffe;
static const uint32_t fourP0      = 0x0fffffb4;
static const uint32_t fourP13579  = 0x07fffffc;
static const uint32_t fourP2468   = 0x0ffffffc;

/* out = a - b */
void curve25519_sub(bignum25519 out, const bignum25519 a, const bignum25519 b) {
	uint32_t c = 0;
	out[0] = twoP0     + a[0] - b[0]    ; c = (out[0] >> 26); out[0] &= reduce_mask_26;
	out[1] = twoP13579 + a[1] - b[1] + c; c = (out[1] >> 25); out[1] &= reduce_mask_25;
	out[2] = twoP2468  + a[2] - b[2] + c; c = (out[2] >> 26); out[2] &= reduce_mask_26;
	out[3] = twoP13579 + a[3] - b[3] + c; c = (out[3] >> 25); out[3] &= reduce_mask_25;
	out[4] = twoP2468  + a[4] - b[4] + c;
	out[5] = twoP13579 + a[5] - b[5]    ;
	out[6] = twoP2468  + a[6] - b[6]    ;
	out[7] = twoP13579 + a[7] - b[7]    ;
	out[8] = twoP2468  + a[8] - b[8]    ;
	out[9] = twoP13579 + a[9] - b[9]    ;
}

/* out = in * scalar */
void curve25519_scalar_product(bignum25519 out, const bignum25519 in, const uint32_t scalar) {
	uint64_t a = 0;
	uint32_t c = 0;
	a = mul32x32_64(in[0], scalar);     out[0] = (uint32_t)a & reduce_mask_26; c = (uint32_t)(a >> 26);
	a = mul32x32_64(in[1], scalar) + c; out[1] = (uint32_t)a & reduce_mask_25; c = (uint32_t)(a >> 25);
	a = mul32x32_64(in[2], scalar) + c; out[2] = (uint32_t)a & reduce_mask_26; c = (uint32_t)(a >> 26);
	a = mul32x32_64(in[3], scalar) + c; out[3] = (uint32_t)a & reduce_mask_25; c = (uint32_t)(a >> 25);
	a = mul32x32_64(in[4], scalar) + c; out[4] = (uint32_t)a & reduce_mask_26; c = (uint32_t)(a >> 26);
	a = mul32x32_64(in[5], scalar) + c; out[5] = (uint32_t)a & reduce_mask_25; c = (uint32_t)(a >> 25);
	a = mul32x32_64(in[6], scalar) + c; out[6] = (uint32_t)a & reduce_mask_26; c = (uint32_t)(a >> 26);
	a = mul32x32_64(in[7], scalar) + c; out[7] = (uint32_t)a & reduce_mask_25; c = (uint32_t)(a >> 25);
	a = mul32x32_64(in[8], scalar) + c; out[8] = (uint32_t)a & reduce_mask_26; c = (uint32_t)(a >> 26);
	a = mul32x32_64(in[9], scalar) + c; out[9] = (uint32_t)a & reduce_mask_25; c = (uint32_t)(a >> 25);
	                                    out[0] += c * 19;
}

/* out = a - b, where a is the result of a basic op (add,sub) */
void curve25519_sub_after_basic(bignum25519 out, const bignum25519 a, const bignum25519 b) {
	uint32_t c = 0;
	out[0] = fourP0     + a[0] - b[0]    ; c = (out[0] >> 26); out[0] &= reduce_mask_26;
	out[1] = fourP13579 + a[1] - b[1] + c; c = (out[1] >> 25); out[1] &= reduce_mask_25;
	out[2] = fourP2468  + a[2] - b[2] + c; c = (out[2] >> 26); out[2] &= reduce_mask_26;
	out[3] = fourP13579 + a[3] - b[3] + c; c = (out[3] >> 25); out[3] &= reduce_mask_25;
	out[4] = fourP2468  + a[4] - b[4] + c; c = (out[4] >> 26); out[4] &= reduce_mask_26;
	out[5] = fourP13579 + a[5] - b[5] + c; c = (out[5] >> 25); out[5] &= reduce_mask_25;
	out[6] = fourP2468  + a[6] - b[6] + c; c = (out[6] >> 26); out[6] &= reduce_mask_26;
	out[7] = fourP13579 + a[7] - b[7] + c; c = (out[7] >> 25); out[7] &= reduce_mask_25;
	out[8] = fourP2468  + a[8] - b[8] + c; c = (out[8] >> 26); out[8] &= reduce_mask_26;
	out[9] = fourP13579 + a[9] - b[9] + c; c = (out[9] >> 25); out[9] &= reduce_mask_25;
	out[0] += 19 * c;
}

void curve25519_sub_reduce(bignum25519 out, const bignum25519 a, const bignum25519 b) {
	uint32_t c = 0;
	out[0] = fourP0     + a[0] - b[0]    ; c = (out[0] >> 26); out[0] &= reduce_mask_26;
	out[1] = fourP13579 + a[1] - b[1] + c; c = (out[1] >> 25); out[1] &= reduce_mask_25;
	out[2] = fourP2468  + a[2] - b[2] + c; c = (out[2] >> 26); out[2] &= reduce_mask_26;
	out[3] = fourP13579 + a[3] - b[3] + c; c = (out[3] >> 25); out[3] &= reduce_mask_25;
	out[4] = fourP2468  + a[4] - b[4] + c; c = (out[4] >> 26); out[4] &= reduce_mask_26;
	out[5] = fourP13579 + a[5] - b[5] + c; c = (out[5] >> 25); out[5] &= reduce_mask_25;
	out[6] = fourP2468  + a[6] - b[6] + c; c = (out[6] >> 26); out[6] &= reduce_mask_26;
	out[7] = fourP13579 + a[7] - b[7] + c; c = (out[7] >> 25); out[7] &= reduce_mask_25;
	out[8] = fourP2468  + a[8] - b[8] + c; c = (out[8] >> 26); out[8] &= reduce_mask_26;
	out[9] = fourP13579 + a[9] - b[9] + c; c = (out[9] >> 25); out[9] &= reduce_mask_25;
	out[0] += 19 * c;
}

/* out = -a */
void curve25519_neg(bignum25519 out, const bignum25519 a) {
	uint32_t c = 0;
	out[0] = twoP0     - a[0]    ; c = (out[0] >> 26); out[0] &= reduce_mask_26;
	out[1] = twoP13579 - a[1] + c; c = (out[1] >> 25); out[1] &= reduce_mask_25;
	out[2] = twoP2468  - a[2] + c; c = (out[2] >> 26); out[2] &= reduce_mask_26;
	out[3] = twoP13579 - a[3] + c; c = (out[3] >> 25); out[3] &= reduce_mask_25;
	out[4] = twoP2468  - a[4] + c; c = (out[4] >> 26); out[4] &= reduce_mask_26;
	out[5] = twoP13579 - a[5] + c; c = (out[5] >> 25); out[5] &= reduce_mask_25;
	out[6] = twoP2468  - a[6] + c; c = (out[6] >> 26); out[6] &= reduce_mask_26;
	out[7] = twoP13579 - a[7] + c; c = (out[7] >> 25); out[7] &= reduce_mask_25;
	out[8] = twoP2468  - a[8] + c; c = (out[8] >> 26); out[8] &= reduce_mask_26;
	out[9] = twoP13579 - a[9] + c; c = (out[9] >> 25); out[9] &= reduce_mask_25;
	out[0] += 19 * c;
}

/* out = a * b */
#define curve25519_mul_noinline curve25519_mul
void curve25519_mul(bignum25519 out, const bignum25519 a, const bignum25519 b) {
	uint32_t r0 = 0, r1 = 0, r2 = 0, r3 = 0, r4 = 0, r5 = 0, r6 = 0, r7 = 0, r8 = 0, r9 = 0;
	uint32_t s0 = 0, s1 = 0, s2 = 0, s3 = 0, s4 = 0, s5 = 0, s6 = 0, s7 = 0, s8 = 0, s9 = 0;
	uint64_t m0 = 0, m1 = 0, m2 = 0, m3 = 0, m4 = 0, m5 = 0, m6 = 0, m7 = 0, m8 = 0, m9 = 0, c = 0;
	uint32_t p = 0;

	r0 = b[0];
	r1 = b[1];
	r2 = b[2];
	r3 = b[3];
	r4 = b[4];
	r5 = b[5];
	r6 = b[6];
	r7 = b[7];
	r8 = b[8];
	r9 = b[9];

	s0 = a[0];
	s1 = a[1];
	s2 = a[2];
	s3 = a[3];
	s4 = a[4];
	s5 = a[5];
	s6 = a[6];
	s7 = a[7];
	s8 = a[8];
	s9 = a[9];

	m1 = mul32x32_64(r0, s1) + mul32x32_64(r1, s0);
	m3 = mul32x32_64(r0, s3) + mul32x32_64(r1, s2) + mul32x32_64(r2, s1) + mul32x32_64(r3, s0);
	m5 = mul32x32_64(r0, s5) + mul32x32_64(r1, s4) + mul32x32_64(r2, s3) + mul32x32_64(r3, s2) + mul32x32_64(r4, s1) + mul32x32_64(r5, s0);
	m7 = mul32x32_64(r0, s7) + mul32x32_64(r1, s6) + mul32x32_64(r2, s5) + mul32x32_64(r3, s4) + mul32x32_64(r4, s3) + mul32x32_64(r5, s2) + mul32x32_64(r6, s1) + mul32x32_64(r7, s0);
	m9 = mul32x32_64(r0, s9) + mul32x32_64(r1, s8) + mul32x32_64(r2, s7) + mul32x32_64(r3, s6) + mul32x32_64(r4, s5) + mul32x32_64(r5, s4) + mul32x32_64(r6, s3) + mul32x32_64(r7, s2) + mul32x32_64(r8, s1) + mul32x32_64(r9, s0);

	r1 *= 2;
	r3 *= 2;
	r5 *= 2;
	r7 *= 2;

	m0 = mul32x32_64(r0, s0);
	m2 = mul32x32_64(r0, s2) + mul32x32_64(r1, s1) + mul32x32_64(r2, s0);
	m4 = mul32x32_64(r0, s4) + mul32x32_64(r1, s3) + mul32x32_64(r2, s2) + mul32x32_64(r3, s1) + mul32x32_64(r4, s0);
	m6 = mul32x32_64(r0, s6) + mul32x32_64(r1, s5) + mul32x32_64(r2, s4) + mul32x32_64(r3, s3) + mul32x32_64(r4, s2) + mul32x32_64(r5, s1) + mul32x32_64(r6, s0);
	m8 = mul32x32_64(r0, s8) + mul32x32_64(r1, s7) + mul32x32_64(r2, s6) + mul32x32_64(r3, s5) + mul32x32_64(r4, s4) + mul32x32_64(r5, s3) + mul32x32_64(r6, s2) + mul32x32_64(r7, s1) + mul32x32_64(r8, s0);

	r1 *= 19;
	r2 *= 19;
	r3 = (r3 / 2) * 19;
	r4 *= 19;
	r5 = (r5 / 2) * 19;
	r6 *= 19;
	r7 = (r7 / 2) * 19;
	r8 *= 19;
	r9 *= 19;

	m1 += (mul32x32_64(r9, s2) + mul32x32_64(r8, s3) + mul32x32_64(r7, s4) + mul32x32_64(r6, s5) + mul32x32_64(r5, s6) + mul32x32_64(r4, s7) + mul32x32_64(r3, s8) + mul32x32_64(r2, s9));
	m3 += (mul32x32_64(r9, s4) + mul32x32_64(r8, s5) + mul32x32_64(r7, s6) + mul32x32_64(r6, s7) + mul32x32_64(r5, s8) + mul32x32_64(r4, s9));
	m5 += (mul32x32_64(r9, s6) + mul32x32_64(r8, s7) + mul32x32_64(r7, s8) + mul32x32_64(r6, s9));
	m7 += (mul32x32_64(r9, s8) + mul32x32_64(r8, s9));

	r3 *= 2;
	r5 *= 2;
	r7 *= 2;
	r9 *= 2;

	m0 += (mul32x32_64(r9, s1) + mul32x32_64(r8, s2) + mul32x32_64(r7, s3) + mul32x32_64(r6, s4) + mul32x32_64(r5, s5) + mul32x32_64(r4, s6) + mul32x32_64(r3, s7) + mul32x32_64(r2, s8) + mul32x32_64(r1, s9));
	m2 += (mul32x32_64(r9, s3) + mul32x32_64(r8, s4) + mul32x32_64(r7, s5) + mul32x32_64(r6, s6) + mul32x32_64(r5, s7) + mul32x32_64(r4, s8) + mul32x32_64(r3, s9));
	m4 += (mul32x32_64(r9, s5) + mul32x32_64(r8, s6) + mul32x32_64(r7, s7) + mul32x32_64(r6, s8) + mul32x32_64(r5, s9));
	m6 += (mul32x32_64(r9, s7) + mul32x32_64(r8, s8) + mul32x32_64(r7, s9));
	m8 += (mul32x32_64(r9, s9));

	                             r0 = (uint32_t)m0 & reduce_mask_26; c = (m0 >> 26);
	m1 += c;                     r1 = (uint32_t)m1 & reduce_mask_25; c = (m1 >> 25);
	m2 += c;                     r2 = (uint32_t)m2 & reduce_mask_26; c = (m2 >> 26);
	m3 += c;                     r3 = (uint32_t)m3 & reduce_mask_25; c = (m3 >> 25);
	m4 += c;                     r4 = (uint32_t)m4 & reduce_mask_26; c = (m4 >> 26);
	m5 += c;                     r5 = (uint32_t)m5 & reduce_mask_25; c = (m5 >> 25);
	m6 += c;                     r6 = (uint32_t)m6 & reduce_mask_26; c = (m6 >> 26);
	m7 += c;                     r7 = (uint32_t)m7 & reduce_mask_25; c = (m7 >> 25);
	m8 += c;                     r8 = (uint32_t)m8 & reduce_mask_26; c = (m8 >> 26);
	m9 += c;                     r9 = (uint32_t)m9 & reduce_mask_25; p = (uint32_t)(m9 >> 25);
	m0 = r0 + mul32x32_64(p,19); r0 = (uint32_t)m0 & reduce_mask_26; p = (uint32_t)(m0 >> 26);
	r1 += p;

	out[0] = r0;
	out[1] = r1;
	out[2] = r2;
	out[3] = r3;
	out[4] = r4;
	out[5] = r5;
	out[6] = r6;
	out[7] = r7;
	out[8] = r8;
	out[9] = r9;
}

/* out = in * in */
void curve25519_square(bignum25519 out, const bignum25519 in) {
	uint32_t r0 = 0, r1 = 0, r2 = 0, r3 = 0, r4 = 0, r5 = 0, r6 = 0, r7 = 0, r8 = 0, r9 = 0;
	uint32_t d6 = 0, d7 = 0, d8 = 0, d9 = 0;
	uint64_t m0 = 0, m1 = 0, m2 = 0, m3 = 0, m4 = 0, m5 = 0, m6 = 0, m7 = 0, m8 = 0, m9 = 0, c = 0;
	uint32_t p = 0;

	r0 = in[0];
	r1 = in[1];
	r2 = in[2];
	r3 = in[3];
	r4 = in[4];
	r5 = in[5];
	r6 = in[6];
	r7 = in[7];
	r8 = in[8];
	r9 = in[9];

	m0 = mul32x32_64(r0, r0);
	r0 *= 2;
	m1 = mul32x32_64(r0, r1);
	m2 = mul32x32_64(r0, r2) + mul32x32_64(r1, r1 * 2);
	r1 *= 2;
	m3 = mul32x32_64(r0, r3) + mul32x32_64(r1, r2    );
	m4 = mul32x32_64(r0, r4) + mul32x32_64(r1, r3 * 2) + mul32x32_64(r2, r2);
	r2 *= 2;
	m5 = mul32x32_64(r0, r5) + mul32x32_64(r1, r4    ) + mul32x32_64(r2, r3);
	m6 = mul32x32_64(r0, r6) + mul32x32_64(r1, r5 * 2) + mul32x32_64(r2, r4) + mul32x32_64(r3, r3 * 2);
	r3 *= 2;
	m7 = mul32x32_64(r0, r7) + mul32x32_64(r1, r6    ) + mul32x32_64(r2, r5) + mul32x32_64(r3, r4    );
	m8 = mul32x32_64(r0, r8) + mul32x32_64(r1, r7 * 2) + mul32x32_64(r2, r6) + mul32x32_64(r3, r5 * 2) + mul32x32_64(r4, r4    );
	m9 = mul32x32_64(r0, r9) + mul32x32_64(r1, r8    ) + mul32x32_64(r2, r7) + mul32x32_64(r3, r6    ) + mul32x32_64(r4, r5 * 2);

	d6 = r6 * 19;
	d7 = r7 * 2 * 19;
	d8 = r8 * 19;
	d9 = r9 * 2 * 19;

	m0 += (mul32x32_64(d9, r1    ) + mul32x32_64(d8, r2    ) + mul32x32_64(d7, r3    ) + mul32x32_64(d6, r4 * 2) + mul32x32_64(r5, r5 * 2 * 19));
	m1 += (mul32x32_64(d9, r2 / 2) + mul32x32_64(d8, r3    ) + mul32x32_64(d7, r4    ) + mul32x32_64(d6, r5 * 2));
	m2 += (mul32x32_64(d9, r3    ) + mul32x32_64(d8, r4 * 2) + mul32x32_64(d7, r5 * 2) + mul32x32_64(d6, r6    ));
	m3 += (mul32x32_64(d9, r4    ) + mul32x32_64(d8, r5 * 2) + mul32x32_64(d7, r6    ));
	m4 += (mul32x32_64(d9, r5 * 2) + mul32x32_64(d8, r6 * 2) + mul32x32_64(d7, r7    ));
	m5 += (mul32x32_64(d9, r6    ) + mul32x32_64(d8, r7 * 2));
	m6 += (mul32x32_64(d9, r7 * 2) + mul32x32_64(d8, r8    ));
	m7 += (mul32x32_64(d9, r8    ));
	m8 += (mul32x32_64(d9, r9    ));

	                             r0 = (uint32_t)m0 & reduce_mask_26; c = (m0 >> 26);
	m1 += c;                     r1 = (uint32_t)m1 & reduce_mask_25; c = (m1 >> 25);
	m2 += c;                     r2 = (uint32_t)m2 & reduce_mask_26; c = (m2 >> 26);
	m3 += c;                     r3 = (uint32_t)m3 & reduce_mask_25; c = (m3 >> 25);
	m4 += c;                     r4 = (uint32_t)m4 & reduce_mask_26; c = (m4 >> 26);
	m5 += c;                     r5 = (uint32_t)m5 & reduce_mask_25; c = (m5 >> 25);
	m6 += c;                     r6 = (uint32_t)m6 & reduce_mask_26; c = (m6 >> 26);
	m7 += c;                     r7 = (uint32_t)m7 & reduce_mask_25; c = (m7 >> 25);
	m8 += c;                     r8 = (uint32_t)m8 & reduce_mask_26; c = (m8 >> 26);
	m9 += c;                     r9 = (uint32_t)m9 & reduce_mask_25; p = (uint32_t)(m9 >> 25);
	m0 = r0 + mul32x32_64(p,19); r0 = (uint32_t)m0 & reduce_mask_26; p = (uint32_t)(m0 >> 26);
	r1 += p;

	out[0] = r0;
	out[1] = r1;
	out[2] = r2;
	out[3] = r3;
	out[4] = r4;
	out[5] = r5;
	out[6] = r6;
	out[7] = r7;
	out[8] = r8;
	out[9] = r9;
}

/* out = in ^ (2 * count) */
void curve25519_square_times(bignum25519 out, const bignum25519 in, int count) {
	uint32_t r0 = 0, r1 = 0, r2 = 0, r3 = 0, r4 = 0, r5 = 0, r6 = 0, r7 = 0, r8 = 0, r9 = 0;
	uint32_t d6 = 0, d7 = 0, d8 = 0, d9 = 0;
	uint64_t m0 = 0, m1 = 0, m2 = 0, m3 = 0, m4 = 0, m5 = 0, m6 = 0, m7 = 0, m8 = 0, m9 = 0, c = 0;
	uint32_t p = 0;

	r0 = in[0];
	r1 = in[1];
	r2 = in[2];
	r3 = in[3];
	r4 = in[4];
	r5 = in[5];
	r6 = in[6];
	r7 = in[7];
	r8 = in[8];
	r9 = in[9];

	do {
		m0 = mul32x32_64(r0, r0);
		r0 *= 2;
		m1 = mul32x32_64(r0, r1);
		m2 = mul32x32_64(r0, r2) + mul32x32_64(r1, r1 * 2);
		r1 *= 2;
		m3 = mul32x32_64(r0, r3) + mul32x32_64(r1, r2    );
		m4 = mul32x32_64(r0, r4) + mul32x32_64(r1, r3 * 2) + mul32x32_64(r2, r2);
		r2 *= 2;
		m5 = mul32x32_64(r0, r5) + mul32x32_64(r1, r4    ) + mul32x32_64(r2, r3);
		m6 = mul32x32_64(r0, r6) + mul32x32_64(r1, r5 * 2) + mul32x32_64(r2, r4) + mul32x32_64(r3, r3 * 2);
		r3 *= 2;
		m7 = mul32x32_64(r0, r7) + mul32x32_64(r1, r6    ) + mul32x32_64(r2, r5) + mul32x32_64(r3, r4    );
		m8 = mul32x32_64(r0, r8) + mul32x32_64(r1, r7 * 2) + mul32x32_64(r2, r6) + mul32x32_64(r3, r5 * 2) + mul32x32_64(r4, r4    );
		m9 = mul32x32_64(r0, r9) + mul32x32_64(r1, r8    ) + mul32x32_64(r2, r7) + mul32x32_64(r3, r6    ) + mul32x32_64(r4, r5 * 2);

		d6 = r6 * 19;
		d7 = r7 * 2 * 19;
		d8 = r8 * 19;
		d9 = r9 * 2 * 19;

		m0 += (mul32x32_64(d9, r1    ) + mul32x32_64(d8, r2    ) + mul32x32_64(d7, r3    ) + mul32x32_64(d6, r4 * 2) + mul32x32_64(r5, r5 * 2 * 19));
		m1 += (mul32x32_64(d9, r2 / 2) + mul32x32_64(d8, r3    ) + mul32x32_64(d7, r4    ) + mul32x32_64(d6, r5 * 2));
		m2 += (mul32x32_64(d9, r3    ) + mul32x32_64(d8, r4 * 2) + mul32x32_64(d7, r5 * 2) + mul32x32_64(d6, r6    ));
		m3 += (mul32x32_64(d9, r4    ) + mul32x32_64(d8, r5 * 2) + mul32x32_64(d7, r6    ));
		m4 += (mul32x32_64(d9, r5 * 2) + mul32x32_64(d8, r6 * 2) + mul32x32_64(d7, r7    ));
		m5 += (mul32x32_64(d9, r6    ) + mul32x32_64(d8, r7 * 2));
		m6 += (mul32x32_64(d9, r7 * 2) + mul32x32_64(d8, r8    ));
		m7 += (mul32x32_64(d9, r8    ));
		m8 += (mul32x32_64(d9, r9    ));

		                             r0 = (uint32_t)m0 & reduce_mask_26; c = (m0 >> 26);
		m1 += c;                     r1 = (uint32_t)m1 & reduce_mask_25; c = (m1 >> 25);
		m2 += c;                     r2 = (uint32_t)m2 & reduce_mask_26; c = (m2 >> 26);
		m3 += c;                     r3 = (uint32_t)m3 & reduce_mask_25; c = (m3 >> 25);
		m4 += c;                     r4 = (uint32_t)m4 & reduce_mask_26; c = (m4 >> 26);
		m5 += c;                     r5 = (uint32_t)m5 & reduce_mask_25; c = (m5 >> 25);
		m6 += c;                     r6 = (uint32_t)m6 & reduce_mask_26; c = (m6 >> 26);
		m7 += c;                     r7 = (uint32_t)m7 & reduce_mask_25; c = (m7 >> 25);
		m8 += c;                     r8 = (uint32_t)m8 & reduce_mask_26; c = (m8 >> 26);
		m9 += c;                     r9 = (uint32_t)m9 & reduce_mask_25; p = (uint32_t)(m9 >> 25);
		m0 = r0 + mul32x32_64(p,19); r0 = (uint32_t)m0 & reduce_mask_26; p = (uint32_t)(m0 >> 26);
		r1 += p;
	} while (--count);

	out[0] = r0;
	out[1] = r1;
	out[2] = r2;
	out[3] = r3;
	out[4] = r4;
	out[5] = r5;
	out[6] = r6;
	out[7] = r7;
	out[8] = r8;
	out[9] = r9;
}

/* Take a little-endian, 32-byte number and expand it into polynomial form */
void curve25519_expand(bignum25519 out, const unsigned char in[32]) {
	uint32_t x0 = 0, x1 = 0, x2 = 0, x3 = 0, x4 = 0, x5 = 0, x6 = 0, x7 = 0;
	#define F(s)							 \
			((((uint32_t)in[s + 0])      ) | \
			 (((uint32_t)in[s + 1]) <<  8) | \
			 (((uint32_t)in[s + 2]) << 16) | \
			 (((uint32_t)in[s + 3]) << 24))
	x0 = F(0);
	x1 = F(4);
	x2 = F(8);
	x3 = F(12);
	x4 = F(16);
	x5 = F(20);
	x6 = F(24);
	x7 = F(28);
	#undef F

	out[0] = (                        x0       ) & reduce_mask_26;
	out[1] = ((((uint64_t)x1 << 32) | x0) >> 26) & reduce_mask_25;
	out[2] = ((((uint64_t)x2 << 32) | x1) >> 19) & reduce_mask_26;
	out[3] = ((((uint64_t)x3 << 32) | x2) >> 13) & reduce_mask_25;
	out[4] = ((                       x3) >>  6) & reduce_mask_26;
	out[5] = (                        x4       ) & reduce_mask_25;
	out[6] = ((((uint64_t)x5 << 32) | x4) >> 25) & reduce_mask_26;
	out[7] = ((((uint64_t)x6 << 32) | x5) >> 19) & reduce_mask_25;
	out[8] = ((((uint64_t)x7 << 32) | x6) >> 12) & reduce_mask_26;
	out[9] = ((                       x7) >>  6) & reduce_mask_25; /* ignore the top bit */
}

/* Take a fully reduced polynomial form number and contract it into a
 * little-endian, 32-byte array
 */
void curve25519_contract(unsigned char out[32], const bignum25519 in) {
	bignum25519 f = {0};
	curve25519_copy(f, in);

	#define carry_pass() \
		f[1] += f[0] >> 26; f[0] &= reduce_mask_26; \
		f[2] += f[1] >> 25; f[1] &= reduce_mask_25; \
		f[3] += f[2] >> 26; f[2] &= reduce_mask_26; \
		f[4] += f[3] >> 25; f[3] &= reduce_mask_25; \
		f[5] += f[4] >> 26; f[4] &= reduce_mask_26; \
		f[6] += f[5] >> 25; f[5] &= reduce_mask_25; \
		f[7] += f[6] >> 26; f[6] &= reduce_mask_26; \
		f[8] += f[7] >> 25; f[7] &= reduce_mask_25; \
		f[9] += f[8] >> 26; f[8] &= reduce_mask_26;

	#define carry_pass_full() \
		carry_pass() \
		f[0] += 19 * (f[9] >> 25); f[9] &= reduce_mask_25;

	#define carry_pass_final() \
		carry_pass() \
		f[9] &= reduce_mask_25;

	carry_pass_full()
	carry_pass_full()

	/* now t is between 0 and 2^255-1, properly carried. */
	/* case 1: between 0 and 2^255-20. case 2: between 2^255-19 and 2^255-1. */
	f[0] += 19;
	carry_pass_full()

	/* now between 19 and 2^255-1 in both cases, and offset by 19. */
	f[0] += (reduce_mask_26 + 1) - 19;
	f[1] += (reduce_mask_25 + 1) - 1;
	f[2] += (reduce_mask_26 + 1) - 1;
	f[3] += (reduce_mask_25 + 1) - 1;
	f[4] += (reduce_mask_26 + 1) - 1;
	f[5] += (reduce_mask_25 + 1) - 1;
	f[6] += (reduce_mask_26 + 1) - 1;
	f[7] += (reduce_mask_25 + 1) - 1;
	f[8] += (reduce_mask_26 + 1) - 1;
	f[9] += (reduce_mask_25 + 1) - 1;

	/* now between 2^255 and 2^256-20, and offset by 2^255. */
	carry_pass_final()

	#undef carry_pass
	#undef carry_full
	#undef carry_final

	f[1] <<= 2;
	f[2] <<= 3;
	f[3] <<= 5;
	f[4] <<= 6;
	f[6] <<= 1;
	f[7] <<= 3;
	f[8] <<= 4;
	f[9] <<= 6;

	#define F(i, s) \
		out[s+0] |= (unsigned char )(f[i] & 0xff); \
		out[s+1] = (unsigned char )((f[i] >> 8) & 0xff); \
		out[s+2] = (unsigned char )((f[i] >> 16) & 0xff); \
		out[s+3] = (unsigned char )((f[i] >> 24) & 0xff);

	out[0] = 0;
	out[16] = 0;
	F(0,0);
	F(1,3);
	F(2,6);
	F(3,9);
	F(4,12);
	F(5,16);
	F(6,19);
	F(7,22);
	F(8,25);
	F(9,28);
	#undef F
}

/* if (iswap) swap(a, b) */
void curve25519_swap_conditional(bignum25519 a, bignum25519 b, uint32_t iswap) {
	const uint32_t swap = (uint32_t)(-(int32_t)iswap);
	uint32_t x0 = 0, x1 = 0, x2 = 0, x3 = 0, x4 = 0, x5 = 0, x6 = 0, x7 = 0, x8 = 0, x9 = 0;

	x0 = swap & (a[0] ^ b[0]); a[0] ^= x0; b[0] ^= x0;
	x1 = swap & (a[1] ^ b[1]); a[1] ^= x1; b[1] ^= x1;
	x2 = swap & (a[2] ^ b[2]); a[2] ^= x2; b[2] ^= x2;
	x3 = swap & (a[3] ^ b[3]); a[3] ^= x3; b[3] ^= x3;
	x4 = swap & (a[4] ^ b[4]); a[4] ^= x4; b[4] ^= x4;
	x5 = swap & (a[5] ^ b[5]); a[5] ^= x5; b[5] ^= x5;
	x6 = swap & (a[6] ^ b[6]); a[6] ^= x6; b[6] ^= x6;
	x7 = swap & (a[7] ^ b[7]); a[7] ^= x7; b[7] ^= x7;
	x8 = swap & (a[8] ^ b[8]); a[8] ^= x8; b[8] ^= x8;
	x9 = swap & (a[9] ^ b[9]); a[9] ^= x9; b[9] ^= x9;
}

void curve25519_set(bignum25519 r, uint32_t x){
	 r[0] = x & reduce_mask_26; x >>= 26;
	 r[1] = x & reduce_mask_25;
	 r[2] = 0;
	 r[3] = 0;
	 r[4] = 0;
	 r[5] = 0;
	 r[6] = 0;
	 r[7] = 0;
	 r[8] = 0;
	 r[9] = 0;
}

void curve25519_set_d(bignum25519 r){
	curve25519_copy(r, ge25519_ecd);
}

void curve25519_set_2d(bignum25519 r){
	curve25519_copy(r, ge25519_ec2d);
}

void curve25519_set_sqrtneg1(bignum25519 r){
	curve25519_copy(r, ge25519_sqrtneg1);
}

int curve25519_isnegative(const bignum25519 f) {
	unsigned char s[32] = {0};
	curve25519_contract(s, f);
	return s[0] & 1;
}

int curve25519_isnonzero(const bignum25519 f) {
	unsigned char s[32] = {0};
	curve25519_contract(s, f);
	return ((((int) (s[0] | s[1] | s[2] | s[3] | s[4] | s[5] | s[6] | s[7] | s[8] |
									s[9] | s[10] | s[11] | s[12] | s[13] | s[14] | s[15] | s[16] | s[17] |
									s[18] | s[19] | s[20] | s[21] | s[22] | s[23] | s[24] | s[25] | s[26] |
									s[27] | s[28] | s[29] | s[30] | s[31]) - 1) >> 8) + 1) & 0x1;
}

void curve25519_reduce(bignum25519 out, const bignum25519 in) {
	uint32_t c = 0;
	out[0] = in[0]    ; c = (out[0] >> 26); out[0] &= reduce_mask_26;
	out[1] = in[1] + c; c = (out[1] >> 25); out[1] &= reduce_mask_25;
	out[2] = in[2] + c; c = (out[2] >> 26); out[2] &= reduce_mask_26;
	out[3] = in[3] + c; c = (out[3] >> 25); out[3] &= reduce_mask_25;
	out[4] = in[4] + c; c = (out[4] >> 26); out[4] &= reduce_mask_26;
	out[5] = in[5] + c; c = (out[5] >> 25); out[5] &= reduce_mask_25;
	out[6] = in[6] + c; c = (out[6] >> 26); out[6] &= reduce_mask_26;
	out[7] = in[7] + c; c = (out[7] >> 25); out[7] &= reduce_mask_25;
	out[8] = in[8] + c; c = (out[8] >> 26); out[8] &= reduce_mask_26;
	out[9] = in[9] + c; c = (out[9] >> 25); out[9] &= reduce_mask_25;
	out[0] += 19 * c;
}

void curve25519_divpowm1(bignum25519 r, const bignum25519 u, const bignum25519 v) {
	bignum25519 v3={0}, uv7={0}, t0={0}, t1={0}, t2={0};
	int i = 0;

	curve25519_square(v3, v);
	curve25519_mul(v3, v3, v); /* v3 = v^3 */
	curve25519_square(uv7, v3);
	curve25519_mul(uv7, uv7, v);
	curve25519_mul(uv7, uv7, u); /* uv7 = uv^7 */

	/*fe_pow22523(uv7, uv7);*/
	/* From fe_pow22523.c */

	curve25519_square(t0, uv7);
	curve25519_square(t1, t0);
	curve25519_square(t1, t1);
	curve25519_mul(t1, uv7, t1);
	curve25519_mul(t0, t0, t1);
	curve25519_square(t0, t0);
	curve25519_mul(t0, t1, t0);
	curve25519_square(t1, t0);
	for (i = 0; i < 4; ++i) {
		curve25519_square(t1, t1);
	}
	curve25519_mul(t0, t1, t0);
	curve25519_square(t1, t0);
	for (i = 0; i < 9; ++i) {
		curve25519_square(t1, t1);
	}
	curve25519_mul(t1, t1, t0);
	curve25519_square(t2, t1);
	for (i = 0; i < 19; ++i) {
		curve25519_square(t2, t2);
	}
	curve25519_mul(t1, t2, t1);
	for (i = 0; i < 10; ++i) {
		curve25519_square(t1, t1);
	}
	curve25519_mul(t0, t1, t0);
	curve25519_square(t1, t0);
	for (i = 0; i < 49; ++i) {
		curve25519_square(t1, t1);
	}
	curve25519_mul(t1, t1, t0);
	curve25519_square(t2, t1);
	for (i = 0; i < 99; ++i) {
		curve25519_square(t2, t2);
	}
	curve25519_mul(t1, t2, t1);
	for (i = 0; i < 50; ++i) {
		curve25519_square(t1, t1);
	}
	curve25519_mul(t0, t1, t0);
	curve25519_square(t0, t0);
	curve25519_square(t0, t0);
	curve25519_mul(t0, t0, uv7);

	/* End fe_pow22523.c */
	/* t0 = (uv^7)^((q-5)/8) */
	curve25519_mul(t0, t0, v3);
	curve25519_mul(r, t0, u); /* u^(m+1)v^(-(m+1)) */
}

void curve25519_expand_reduce(bignum25519 out, const unsigned char in[32]) {
  uint32_t x0 = 0, x1 = 0, x2 = 0, x3 = 0, x4 = 0, x5 = 0, x6 = 0, x7 = 0;
#define F(s) \
			((((uint32_t)in[s + 0])      ) | \
			 (((uint32_t)in[s + 1]) <<  8) | \
			 (((uint32_t)in[s + 2]) << 16) | \
			 (((uint32_t)in[s + 3]) << 24))
  x0 = F(0);
  x1 = F(4);
  x2 = F(8);
  x3 = F(12);
  x4 = F(16);
  x5 = F(20);
  x6 = F(24);
  x7 = F(28);
#undef F

	out[0] = (                        x0       ) & reduce_mask_26;
	out[1] = ((((uint64_t)x1 << 32) | x0) >> 26) & reduce_mask_25;
	out[2] = ((((uint64_t)x2 << 32) | x1) >> 19) & reduce_mask_26;
	out[3] = ((((uint64_t)x3 << 32) | x2) >> 13) & reduce_mask_25;
	out[4] = ((                       x3) >>  6) & reduce_mask_26;
	out[5] = (                        x4       ) & reduce_mask_25;
	out[6] = ((((uint64_t)x5 << 32) | x4) >> 25) & reduce_mask_26;
	out[7] = ((((uint64_t)x6 << 32) | x5) >> 19) & reduce_mask_25;
	out[8] = ((((uint64_t)x7 << 32) | x6) >> 12) & reduce_mask_26;
	out[9] = ((                       x7) >>  6); // & reduce_mask_25; /* ignore the top bit */
	out[0] += 19 * (out[9] >> 25);
	out[9] &= reduce_mask_25;
}
