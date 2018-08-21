//
// Created by Dusan Klinec on 29/04/2018.
//

#include <assert.h>
#include "ge25519.h"

static const uint32_t reduce_mask_25 = (1 << 25) - 1;
static const uint32_t reduce_mask_26 = (1 << 26) - 1;

/* sqrt(x) is such an integer y that 0 <= y <= p - 1, y % 2 = 0, and y^2 = x (mod p). */
/* d = -121665 / 121666 */
static const bignum25519 ALIGN(16) fe_d = {
		0x35978a3, 0x0d37284, 0x3156ebd, 0x06a0a0e, 0x001c029, 0x179e898, 0x3a03cbb, 0x1ce7198, 0x2e2b6ff, 0x1480db3}; /* d */
static const bignum25519 ALIGN(16) fe_sqrtm1 = {
		0x20ea0b0, 0x186c9d2, 0x08f189d, 0x035697f, 0x0bd0c60, 0x1fbd7a7, 0x2804c9e, 0x1e16569, 0x004fc1d, 0x0ae0c92}; /* sqrt(-1) */
//static const bignum25519 ALIGN(16) fe_d2 = {
//		0x2b2f159, 0x1a6e509, 0x22add7a, 0x0d4141d, 0x0038052, 0x0f3d130, 0x3407977, 0x19ce331, 0x1c56dff, 0x0901b67}; /* 2 * d */

/* A = 2 * (1 - d) / (1 + d) = 486662 */
static const bignum25519 ALIGN(16) fe_ma2 = {
		0x33de3c9, 0x1fff236, 0x3ffffff, 0x1ffffff, 0x3ffffff, 0x1ffffff, 0x3ffffff, 0x1ffffff, 0x3ffffff, 0x1ffffff}; /* -A^2 */
static const bignum25519 ALIGN(16) fe_ma = {
		0x3f892e7, 0x1ffffff, 0x3ffffff, 0x1ffffff, 0x3ffffff, 0x1ffffff, 0x3ffffff, 0x1ffffff, 0x3ffffff, 0x1ffffff}; /* -A */
static const bignum25519 ALIGN(16) fe_fffb1 = {
		0x1e3bdff, 0x025a2b3, 0x18e5bab, 0x0ba36ac, 0x0b9afed, 0x004e61c, 0x31d645f, 0x09d1bea, 0x102529e, 0x0063810}; /* sqrt(-2 * A * (A + 2)) */
static const bignum25519 ALIGN(16) fe_fffb2 = {
		0x383650d, 0x066df27, 0x10405a4, 0x1cfdd48, 0x2b887f2, 0x1e9a041, 0x1d7241f, 0x0612dc5, 0x35fba5d, 0x0cbe787}; /* sqrt(2 * A * (A + 2)) */
static const bignum25519 ALIGN(16) fe_fffb3 = {
		0x0cfd387, 0x1209e3a, 0x3bad4fc, 0x18ad34d, 0x2ff6c02, 0x0f25d12, 0x15cdfe0, 0x0e208ed, 0x32eb3df, 0x062d7bb}; /* sqrt(-sqrt(-1) * A * (A + 2)) */
static const bignum25519 ALIGN(16) fe_fffb4 = {
		0x2b39186, 0x14640ed, 0x14930a7, 0x04509fa, 0x3b91bf0, 0x0f7432e, 0x07a443f, 0x17f24d8, 0x031067d, 0x0690fcc}; /* sqrt(sqrt(-1) * A * (A + 2)) */

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
	unsigned char s[32];
	curve25519_contract(s, f);
	return s[0] & 1;
}

int curve25519_isnonzero(const bignum25519 f) {
	unsigned char s[32];
	curve25519_contract(s, f);
	return ((((int) (s[0] | s[1] | s[2] | s[3] | s[4] | s[5] | s[6] | s[7] | s[8] |
									s[9] | s[10] | s[11] | s[12] | s[13] | s[14] | s[15] | s[16] | s[17] |
									s[18] | s[19] | s[20] | s[21] | s[22] | s[23] | s[24] | s[25] | s[26] |
									s[27] | s[28] | s[29] | s[30] | s[31]) - 1) >> 8) + 1) & 0x1;
}

void curve25519_reduce(bignum25519 out, const bignum25519 in) {
	uint32_t c;
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

static void curve25519_divpowm1(bignum25519 r, const bignum25519 u, const bignum25519 v) {
	bignum25519 v3={0}, uv7={0}, t0={0}, t1={0}, t2={0};
	int i;

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
  uint32_t x0,x1,x2,x3,x4,x5,x6,x7;
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

int ge25519_check(const ge25519 *r){
	/* return (z % q != 0 and
						 x * y % q == z * t % q and
						(y * y - x * x - z * z - ed25519.d * t * t) % q == 0)
	 */

	bignum25519 z={0}, lhs={0}, rhs={0}, tmp={0}, res={0};
	curve25519_reduce(z, r->z);

	curve25519_mul(lhs, r->x, r->y);
	curve25519_mul(rhs, r->z, r->t);
	curve25519_sub_reduce(lhs, lhs, rhs);

	curve25519_square(res, r->y);
	curve25519_square(tmp, r->x);
	curve25519_sub_reduce(res, res, tmp);
	curve25519_square(tmp, r->z);
	curve25519_sub_reduce(res, res, tmp);
	curve25519_square(tmp, r->t);
	curve25519_mul(tmp, tmp, ge25519_ecd);
	curve25519_sub_reduce(res, res, tmp);

	const int c1 = curve25519_isnonzero(z);
	const int c2 = curve25519_isnonzero(lhs);
	const int c3 = curve25519_isnonzero(res);
	return c1 & (c2^0x1) & (c3^0x1);
}

int ge25519_eq(const ge25519 *a, const ge25519 *b){
	int eq = 1;
	bignum25519 t1={0}, t2={0};

	eq &= ge25519_check(a);
	eq &= ge25519_check(b);

	curve25519_mul(t1, a->x, b->z);
	curve25519_mul(t2, b->x, a->z);
	curve25519_sub_reduce(t1, t1, t2);
	eq &= curve25519_isnonzero(t1) ^ 1;

	curve25519_mul(t1, a->y, b->z);
	curve25519_mul(t2, b->y, a->z);
	curve25519_sub_reduce(t1, t1, t2);
	eq &= curve25519_isnonzero(t1) ^ 1;

	return eq;
}

void ge25519_copy(ge25519 *dst, const ge25519 *src){
	curve25519_copy(dst->x, src->x);
	curve25519_copy(dst->y, src->y);
	curve25519_copy(dst->z, src->z);
	curve25519_copy(dst->t, src->t);
}

void ge25519_set_base(ge25519 *r){
	ge25519_copy(r, &ge25519_basepoint);
}

void ge25519_mul8(ge25519 *r, const ge25519 *t) {
	ge25519_double_partial(r, t);
	ge25519_double_partial(r, r);
	ge25519_double(r, r);
}

void ge25519_neg_partial(ge25519 *r){
	curve25519_neg(r->x, r->x);
}

void ge25519_neg_full(ge25519 *r){
	curve25519_neg(r->x, r->x);
	curve25519_neg(r->t, r->t);
}

void ge25519_reduce(ge25519 *r, const ge25519 *t){
	curve25519_reduce(r->x, t->x);
	curve25519_reduce(r->y, t->y);
	curve25519_reduce(r->z, t->z);
	curve25519_reduce(r->t, t->t);
}

void ge25519_norm(ge25519 *r, const ge25519 * t){
	bignum25519 zinv;
	curve25519_recip(zinv, t->z);
	curve25519_mul(r->x, t->x, zinv);
	curve25519_mul(r->y, t->y, zinv);
	curve25519_mul(r->t, r->x, r->y);
	curve25519_set(r->z, 1);
}

void ge25519_add(ge25519 *r, const ge25519 *p, const ge25519 *q, unsigned char signbit) {
	ge25519_pniels P_ni;
	ge25519_p1p1 P_11;

	ge25519_full_to_pniels(&P_ni, q);
	ge25519_pnielsadd_p1p1(&P_11, p, &P_ni, signbit);
	ge25519_p1p1_to_full(r, &P_11);
}

void ge25519_fromfe_frombytes_vartime(ge25519 *r, const unsigned char *s){
	bignum25519 u={0}, v={0}, w={0}, x={0}, y={0}, z={0};
	unsigned char sign;

	curve25519_expand_reduce(u, s);

	curve25519_square(v, u);
	curve25519_add_reduce(v, v, v); /* 2 * u^2 */
	curve25519_set(w, 1);
	curve25519_add_reduce(w, v, w); /* w = 2 * u^2 + 1 */

	curve25519_square(x, w); /* w^2 */
	curve25519_mul(y, fe_ma2, v); /* -2 * A^2 * u^2 */
	curve25519_add_reduce(x, x, y); /* x = w^2 - 2 * A^2 * u^2 */

	curve25519_divpowm1(r->x, w, x); /* (w / x)^(m + 1) */
	curve25519_square(y, r->x);
	curve25519_mul(x, y, x);
	curve25519_sub_reduce(y, w, x);
	curve25519_copy(z, fe_ma);

	if (curve25519_isnonzero(y)) {
		curve25519_add_reduce(y, w, x);
		if (curve25519_isnonzero(y)) {
			goto negative;
		} else {
			curve25519_mul(r->x, r->x, fe_fffb1);
		}
	} else {
		curve25519_mul(r->x, r->x, fe_fffb2);
	}
	curve25519_mul(r->x, r->x, u); /* u * sqrt(2 * A * (A + 2) * w / x) */
	curve25519_mul(z, z, v); /* -2 * A * u^2 */
	sign = 0;
	goto setsign;
negative:
	curve25519_mul(x, x, fe_sqrtm1);
	curve25519_sub_reduce(y, w, x);
	if (curve25519_isnonzero(y)) {
		assert((curve25519_add_reduce(y, w, x), !curve25519_isnonzero(y)));
		curve25519_mul(r->x, r->x, fe_fffb3);
	} else {
		curve25519_mul(r->x, r->x, fe_fffb4);
	}
	/* r->x = sqrt(A * (A + 2) * w / x) */
	/* z = -A */
	sign = 1;
setsign:
	if (curve25519_isnegative(r->x) != sign) {
		assert(curve25519_isnonzero(r->x));
		curve25519_neg(r->x, r->x);
	}
	curve25519_add_reduce(r->z, z, w);
	curve25519_sub_reduce(r->y, z, w);
	curve25519_mul(r->x, r->x, r->z);

	// Partial form, saving from T coord computation .
	// Later is mul8 discarding T anyway.
	// rt = ((rx * ry % q) * inv(rz)) % q
	// curve25519_mul(x, r->x, r->y);
	// curve25519_recip(z, r->z);
	// curve25519_mul(r->t, x, z);

#if !defined(NDEBUG)
	{
		bignum25519 check_x={0}, check_y={0}, check_iz={0}, check_v={0};
		curve25519_recip(check_iz, r->z);
		curve25519_mul(check_x, r->x, check_iz);
		curve25519_mul(check_y, r->y, check_iz);
		curve25519_square(check_x, check_x);
		curve25519_square(check_y, check_y);
		curve25519_mul(check_v, check_x, check_y);
		curve25519_mul(check_v, fe_d, check_v);
		curve25519_add_reduce(check_v, check_v, check_x);
		curve25519_sub_reduce(check_v, check_v, check_y);
		curve25519_set(check_x, 1);
		curve25519_add_reduce(check_v, check_v, check_x);
		assert(!curve25519_isnonzero(check_v));
	}
#endif
}

int ge25519_unpack_vartime(ge25519 *r, const unsigned char *s){
	int res = ge25519_unpack_negative_vartime(r, s);
	ge25519_neg_full(r);
	return res;
}

void ge25519_scalarmult_base_wrapper(ge25519 *r, const bignum256modm s){
	ge25519_scalarmult_base_niels(r, ge25519_niels_base_multiples, s);
}
