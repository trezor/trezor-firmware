/*
	Public domain by Andrew M. <liquidsun@gmail.com>
*/

#include "ed25519-donna.h"

/*
	Arithmetic modulo the group order n = 2^252 +  27742317777372353535851937790883648493 = 7237005577332262213973186563042994240857116359379907606001950938285454250989

	k = 32
	b = 1 << 8 = 256
	m = 2^252 + 27742317777372353535851937790883648493 = 0x1000000000000000000000000000000014def9dea2f79cd65812631a5cf5d3ed
	mu = floor( b^(k*2) / m ) = 0xfffffffffffffffffffffffffffffffeb2106215d086329a7ed9ce5a30a2c131b
*/

static const bignum256modm modm_m = {
	0x1cf5d3ed, 0x20498c69, 0x2f79cd65, 0x37be77a8,
	0x00000014,	0x00000000, 0x00000000,	0x00000000,
	0x00001000
};

static const bignum256modm modm_mu = {
	0x0a2c131b, 0x3673968c, 0x06329a7e, 0x01885742,
	0x3fffeb21, 0x3fffffff, 0x3fffffff, 0x3fffffff,
	0x000fffff
};

static bignum256modm_element_t
lt_modm(bignum256modm_element_t a, bignum256modm_element_t b) {
	return (a - b) >> 31;
}

/* see HAC, Alg. 14.42 Step 4 */
void reduce256_modm(bignum256modm r) {
	bignum256modm t = {0};
	bignum256modm_element_t b = 0, pb = 0, mask = 0;

	/* t = r - m */
	pb = 0;
	pb += modm_m[0]; b = lt_modm(r[0], pb); t[0] = (r[0] - pb + (b << 30)); pb = b;
	pb += modm_m[1]; b = lt_modm(r[1], pb); t[1] = (r[1] - pb + (b << 30)); pb = b;
	pb += modm_m[2]; b = lt_modm(r[2], pb); t[2] = (r[2] - pb + (b << 30)); pb = b;
	pb += modm_m[3]; b = lt_modm(r[3], pb); t[3] = (r[3] - pb + (b << 30)); pb = b;
	pb += modm_m[4]; b = lt_modm(r[4], pb); t[4] = (r[4] - pb + (b << 30)); pb = b;
	pb += modm_m[5]; b = lt_modm(r[5], pb); t[5] = (r[5] - pb + (b << 30)); pb = b;
	pb += modm_m[6]; b = lt_modm(r[6], pb); t[6] = (r[6] - pb + (b << 30)); pb = b;
	pb += modm_m[7]; b = lt_modm(r[7], pb); t[7] = (r[7] - pb + (b << 30)); pb = b;
	pb += modm_m[8]; b = lt_modm(r[8], pb); t[8] = (r[8] - pb + (b << 16));

	/* keep r if r was smaller than m */
	mask = b - 1;
	r[0] ^= mask & (r[0] ^ t[0]);
	r[1] ^= mask & (r[1] ^ t[1]);
	r[2] ^= mask & (r[2] ^ t[2]);
	r[3] ^= mask & (r[3] ^ t[3]);
	r[4] ^= mask & (r[4] ^ t[4]);
	r[5] ^= mask & (r[5] ^ t[5]);
	r[6] ^= mask & (r[6] ^ t[6]);
	r[7] ^= mask & (r[7] ^ t[7]);
	r[8] ^= mask & (r[8] ^ t[8]);
}

/*
	Barrett reduction,  see HAC, Alg. 14.42

	Instead of passing in x, pre-process in to q1 and r1 for efficiency
*/
void barrett_reduce256_modm(bignum256modm r, const bignum256modm q1, const bignum256modm r1) {
	bignum256modm q3 = {0}, r2 = {0};
	uint64_t c = 0;
	bignum256modm_element_t f = 0, b = 0, pb = 0;

	/* q1 = x >> 248 = 264 bits = 9 30 bit elements
	   q2 = mu * q1
	   q3 = (q2 / 256(32+1)) = q2 / (2^8)^(32+1) = q2 >> 264 */
	c  = mul32x32_64(modm_mu[0], q1[7]) + mul32x32_64(modm_mu[1], q1[6]) + mul32x32_64(modm_mu[2], q1[5]) + mul32x32_64(modm_mu[3], q1[4]) + mul32x32_64(modm_mu[4], q1[3]) + mul32x32_64(modm_mu[5], q1[2]) + mul32x32_64(modm_mu[6], q1[1]) + mul32x32_64(modm_mu[7], q1[0]);
	c >>= 30;
	c += mul32x32_64(modm_mu[0], q1[8]) + mul32x32_64(modm_mu[1], q1[7]) + mul32x32_64(modm_mu[2], q1[6]) + mul32x32_64(modm_mu[3], q1[5]) + mul32x32_64(modm_mu[4], q1[4]) + mul32x32_64(modm_mu[5], q1[3]) + mul32x32_64(modm_mu[6], q1[2]) + mul32x32_64(modm_mu[7], q1[1]) + mul32x32_64(modm_mu[8], q1[0]);
	f = (bignum256modm_element_t)c; q3[0] = (f >> 24) & 0x3f; c >>= 30;
	c += mul32x32_64(modm_mu[1], q1[8]) + mul32x32_64(modm_mu[2], q1[7]) + mul32x32_64(modm_mu[3], q1[6]) + mul32x32_64(modm_mu[4], q1[5]) + mul32x32_64(modm_mu[5], q1[4]) + mul32x32_64(modm_mu[6], q1[3]) + mul32x32_64(modm_mu[7], q1[2]) + mul32x32_64(modm_mu[8], q1[1]);
	f = (bignum256modm_element_t)c; q3[0] |= (f << 6) & 0x3fffffff; q3[1] = (f >> 24) & 0x3f; c >>= 30;
	c += mul32x32_64(modm_mu[2], q1[8]) + mul32x32_64(modm_mu[3], q1[7]) + mul32x32_64(modm_mu[4], q1[6]) + mul32x32_64(modm_mu[5], q1[5]) + mul32x32_64(modm_mu[6], q1[4]) + mul32x32_64(modm_mu[7], q1[3]) + mul32x32_64(modm_mu[8], q1[2]);
	f = (bignum256modm_element_t)c; q3[1] |= (f << 6) & 0x3fffffff; q3[2] = (f >> 24) & 0x3f; c >>= 30;
	c += mul32x32_64(modm_mu[3], q1[8]) + mul32x32_64(modm_mu[4], q1[7]) + mul32x32_64(modm_mu[5], q1[6]) + mul32x32_64(modm_mu[6], q1[5]) + mul32x32_64(modm_mu[7], q1[4]) + mul32x32_64(modm_mu[8], q1[3]);
	f = (bignum256modm_element_t)c; q3[2] |= (f << 6) & 0x3fffffff; q3[3] = (f >> 24) & 0x3f; c >>= 30;
	c += mul32x32_64(modm_mu[4], q1[8]) + mul32x32_64(modm_mu[5], q1[7]) + mul32x32_64(modm_mu[6], q1[6]) + mul32x32_64(modm_mu[7], q1[5]) + mul32x32_64(modm_mu[8], q1[4]);
	f = (bignum256modm_element_t)c; q3[3] |= (f << 6) & 0x3fffffff; q3[4] = (f >> 24) & 0x3f; c >>= 30;
	c += mul32x32_64(modm_mu[5], q1[8]) + mul32x32_64(modm_mu[6], q1[7]) + mul32x32_64(modm_mu[7], q1[6]) + mul32x32_64(modm_mu[8], q1[5]);
	f = (bignum256modm_element_t)c; q3[4] |= (f << 6) & 0x3fffffff; q3[5] = (f >> 24) & 0x3f; c >>= 30;
	c += mul32x32_64(modm_mu[6], q1[8]) + mul32x32_64(modm_mu[7], q1[7]) + mul32x32_64(modm_mu[8], q1[6]);
	f = (bignum256modm_element_t)c; q3[5] |= (f << 6) & 0x3fffffff; q3[6] = (f >> 24) & 0x3f; c >>= 30;
	c += mul32x32_64(modm_mu[7], q1[8]) + mul32x32_64(modm_mu[8], q1[7]);
	f = (bignum256modm_element_t)c; q3[6] |= (f << 6) & 0x3fffffff; q3[7] = (f >> 24) & 0x3f; c >>= 30;
	c += mul32x32_64(modm_mu[8], q1[8]);
	f = (bignum256modm_element_t)c; q3[7] |= (f << 6) & 0x3fffffff; q3[8] = (bignum256modm_element_t)(c >> 24);

	/* r1 = (x mod 256^(32+1)) = x mod (2^8)(32+1) = x & ((1 << 264) - 1)
	   r2 = (q3 * m) mod (256^(32+1)) = (q3 * m) & ((1 << 264) - 1) */
	c = mul32x32_64(modm_m[0], q3[0]);
	r2[0] = (bignum256modm_element_t)(c & 0x3fffffff); c >>= 30;
	c += mul32x32_64(modm_m[0], q3[1]) + mul32x32_64(modm_m[1], q3[0]);
	r2[1] = (bignum256modm_element_t)(c & 0x3fffffff); c >>= 30;
	c += mul32x32_64(modm_m[0], q3[2]) + mul32x32_64(modm_m[1], q3[1]) + mul32x32_64(modm_m[2], q3[0]);
	r2[2] = (bignum256modm_element_t)(c & 0x3fffffff); c >>= 30;
	c += mul32x32_64(modm_m[0], q3[3]) + mul32x32_64(modm_m[1], q3[2]) + mul32x32_64(modm_m[2], q3[1]) + mul32x32_64(modm_m[3], q3[0]);
	r2[3] = (bignum256modm_element_t)(c & 0x3fffffff); c >>= 30;
	c += mul32x32_64(modm_m[0], q3[4]) + mul32x32_64(modm_m[1], q3[3]) + mul32x32_64(modm_m[2], q3[2]) + mul32x32_64(modm_m[3], q3[1]) + mul32x32_64(modm_m[4], q3[0]);
	r2[4] = (bignum256modm_element_t)(c & 0x3fffffff); c >>= 30;
	c += mul32x32_64(modm_m[0], q3[5]) + mul32x32_64(modm_m[1], q3[4]) + mul32x32_64(modm_m[2], q3[3]) + mul32x32_64(modm_m[3], q3[2]) + mul32x32_64(modm_m[4], q3[1]) + mul32x32_64(modm_m[5], q3[0]);
	r2[5] = (bignum256modm_element_t)(c & 0x3fffffff); c >>= 30;
	c += mul32x32_64(modm_m[0], q3[6]) + mul32x32_64(modm_m[1], q3[5]) + mul32x32_64(modm_m[2], q3[4]) + mul32x32_64(modm_m[3], q3[3]) + mul32x32_64(modm_m[4], q3[2]) + mul32x32_64(modm_m[5], q3[1]) + mul32x32_64(modm_m[6], q3[0]);
	r2[6] = (bignum256modm_element_t)(c & 0x3fffffff); c >>= 30;
	c += mul32x32_64(modm_m[0], q3[7]) + mul32x32_64(modm_m[1], q3[6]) + mul32x32_64(modm_m[2], q3[5]) + mul32x32_64(modm_m[3], q3[4]) + mul32x32_64(modm_m[4], q3[3]) + mul32x32_64(modm_m[5], q3[2]) + mul32x32_64(modm_m[6], q3[1]) + mul32x32_64(modm_m[7], q3[0]);
	r2[7] = (bignum256modm_element_t)(c & 0x3fffffff); c >>= 30;
	c += mul32x32_64(modm_m[0], q3[8]) + mul32x32_64(modm_m[1], q3[7]) + mul32x32_64(modm_m[2], q3[6]) + mul32x32_64(modm_m[3], q3[5]) + mul32x32_64(modm_m[4], q3[4]) + mul32x32_64(modm_m[5], q3[3]) + mul32x32_64(modm_m[6], q3[2]) + mul32x32_64(modm_m[7], q3[1]) + mul32x32_64(modm_m[8], q3[0]);
	r2[8] = (bignum256modm_element_t)(c & 0xffffff);

	/* r = r1 - r2
	   if (r < 0) r += (1 << 264) */
	pb = 0;
	pb += r2[0]; b = lt_modm(r1[0], pb); r[0] = (r1[0] - pb + (b << 30)); pb = b;
	pb += r2[1]; b = lt_modm(r1[1], pb); r[1] = (r1[1] - pb + (b << 30)); pb = b;
	pb += r2[2]; b = lt_modm(r1[2], pb); r[2] = (r1[2] - pb + (b << 30)); pb = b;
	pb += r2[3]; b = lt_modm(r1[3], pb); r[3] = (r1[3] - pb + (b << 30)); pb = b;
	pb += r2[4]; b = lt_modm(r1[4], pb); r[4] = (r1[4] - pb + (b << 30)); pb = b;
	pb += r2[5]; b = lt_modm(r1[5], pb); r[5] = (r1[5] - pb + (b << 30)); pb = b;
	pb += r2[6]; b = lt_modm(r1[6], pb); r[6] = (r1[6] - pb + (b << 30)); pb = b;
	pb += r2[7]; b = lt_modm(r1[7], pb); r[7] = (r1[7] - pb + (b << 30)); pb = b;
	pb += r2[8]; b = lt_modm(r1[8], pb); r[8] = (r1[8] - pb + (b << 24));

	reduce256_modm(r);
	reduce256_modm(r);
}

/* addition modulo m */
void add256_modm(bignum256modm r, const bignum256modm x, const bignum256modm y) {
	bignum256modm_element_t c = 0;

	c  = x[0] + y[0]; r[0] = c & 0x3fffffff; c >>= 30;
	c += x[1] + y[1]; r[1] = c & 0x3fffffff; c >>= 30;
	c += x[2] + y[2]; r[2] = c & 0x3fffffff; c >>= 30;
	c += x[3] + y[3]; r[3] = c & 0x3fffffff; c >>= 30;
	c += x[4] + y[4]; r[4] = c & 0x3fffffff; c >>= 30;
	c += x[5] + y[5]; r[5] = c & 0x3fffffff; c >>= 30;
	c += x[6] + y[6]; r[6] = c & 0x3fffffff; c >>= 30;
	c += x[7] + y[7]; r[7] = c & 0x3fffffff; c >>= 30;
	c += x[8] + y[8]; r[8] = c;

	reduce256_modm(r);
}

/* -x modulo m */
void neg256_modm(bignum256modm r, const bignum256modm x) {
	bignum256modm_element_t b = 0, pb = 0;

	/* r = m - x */
	pb = 0;
	pb += x[0]; b = lt_modm(modm_m[0], pb); r[0] = (modm_m[0] - pb + (b << 30)); pb = b;
	pb += x[1]; b = lt_modm(modm_m[1], pb); r[1] = (modm_m[1] - pb + (b << 30)); pb = b;
	pb += x[2]; b = lt_modm(modm_m[2], pb); r[2] = (modm_m[2] - pb + (b << 30)); pb = b;
	pb += x[3]; b = lt_modm(modm_m[3], pb); r[3] = (modm_m[3] - pb + (b << 30)); pb = b;
	pb += x[4]; b = lt_modm(modm_m[4], pb); r[4] = (modm_m[4] - pb + (b << 30)); pb = b;
	pb += x[5]; b = lt_modm(modm_m[5], pb); r[5] = (modm_m[5] - pb + (b << 30)); pb = b;
	pb += x[6]; b = lt_modm(modm_m[6], pb); r[6] = (modm_m[6] - pb + (b << 30)); pb = b;
	pb += x[7]; b = lt_modm(modm_m[7], pb); r[7] = (modm_m[7] - pb + (b << 30)); pb = b;
	pb += x[8]; b = lt_modm(modm_m[8], pb); r[8] = (modm_m[8] - pb + (b << 16));

	// if x==0, reduction is required
	reduce256_modm(r);
}

/* consts for subtraction, > p */
/* Emilia Kasper trick, https://www.imperialviolet.org/2010/12/04/ecc.html */
static const uint32_t twoP[] = {
		0x5cf5d3ed, 0x60498c68, 0x6f79cd64, 0x77be77a7, 0x40000013, 0x3fffffff, 0x3fffffff, 0x3fffffff, 0xfff};

/* subtraction x-y % m */
void sub256_modm(bignum256modm r, const bignum256modm x, const bignum256modm y) {
	bignum256modm_element_t c = 0;
	c  = twoP[0] + x[0] - y[0]; r[0] = c & 0x3fffffff; c >>= 30;
	c += twoP[1] + x[1] - y[1]; r[1] = c & 0x3fffffff; c >>= 30;
	c += twoP[2] + x[2] - y[2]; r[2] = c & 0x3fffffff; c >>= 30;
	c += twoP[3] + x[3] - y[3]; r[3] = c & 0x3fffffff; c >>= 30;
	c += twoP[4] + x[4] - y[4]; r[4] = c & 0x3fffffff; c >>= 30;
	c += twoP[5] + x[5] - y[5]; r[5] = c & 0x3fffffff; c >>= 30;
	c += twoP[6] + x[6] - y[6]; r[6] = c & 0x3fffffff; c >>= 30;
	c += twoP[7] + x[7] - y[7]; r[7] = c & 0x3fffffff; c >>= 30;
	c += twoP[8] + x[8] - y[8]; r[8] = c;
	reduce256_modm(r);
}

/* multiplication modulo m */
void mul256_modm(bignum256modm r, const bignum256modm x, const bignum256modm y) {
	bignum256modm r1 = {0}, q1 = {0};
	uint64_t c = 0;
	bignum256modm_element_t f = 0;

	/* r1 = (x mod 256^(32+1)) = x mod (2^8)(31+1) = x & ((1 << 264) - 1)
	   q1 = x >> 248 = 264 bits = 9 30 bit elements */
	c = mul32x32_64(x[0], y[0]);
	f = (bignum256modm_element_t)c; r1[0] = (f & 0x3fffffff); c >>= 30;
	c += mul32x32_64(x[0], y[1]) + mul32x32_64(x[1], y[0]);
	f = (bignum256modm_element_t)c; r1[1] = (f & 0x3fffffff); c >>= 30;
	c += mul32x32_64(x[0], y[2]) + mul32x32_64(x[1], y[1]) + mul32x32_64(x[2], y[0]);
	f = (bignum256modm_element_t)c; r1[2] = (f & 0x3fffffff); c >>= 30;
	c += mul32x32_64(x[0], y[3]) + mul32x32_64(x[1], y[2]) + mul32x32_64(x[2], y[1]) + mul32x32_64(x[3], y[0]);
	f = (bignum256modm_element_t)c; r1[3] = (f & 0x3fffffff); c >>= 30;
	c += mul32x32_64(x[0], y[4]) + mul32x32_64(x[1], y[3]) + mul32x32_64(x[2], y[2]) + mul32x32_64(x[3], y[1]) + mul32x32_64(x[4], y[0]);
	f = (bignum256modm_element_t)c; r1[4] = (f & 0x3fffffff); c >>= 30;
	c += mul32x32_64(x[0], y[5]) + mul32x32_64(x[1], y[4]) + mul32x32_64(x[2], y[3]) + mul32x32_64(x[3], y[2]) + mul32x32_64(x[4], y[1]) + mul32x32_64(x[5], y[0]);
	f = (bignum256modm_element_t)c; r1[5] = (f & 0x3fffffff); c >>= 30;
	c += mul32x32_64(x[0], y[6]) + mul32x32_64(x[1], y[5]) + mul32x32_64(x[2], y[4]) + mul32x32_64(x[3], y[3]) + mul32x32_64(x[4], y[2]) + mul32x32_64(x[5], y[1]) + mul32x32_64(x[6], y[0]);
	f = (bignum256modm_element_t)c; r1[6] = (f & 0x3fffffff); c >>= 30;
	c += mul32x32_64(x[0], y[7]) + mul32x32_64(x[1], y[6]) + mul32x32_64(x[2], y[5]) + mul32x32_64(x[3], y[4]) + mul32x32_64(x[4], y[3]) + mul32x32_64(x[5], y[2]) + mul32x32_64(x[6], y[1]) + mul32x32_64(x[7], y[0]);
	f = (bignum256modm_element_t)c; r1[7] = (f & 0x3fffffff); c >>= 30;
	c += mul32x32_64(x[0], y[8]) + mul32x32_64(x[1], y[7]) + mul32x32_64(x[2], y[6]) + mul32x32_64(x[3], y[5]) + mul32x32_64(x[4], y[4]) + mul32x32_64(x[5], y[3]) + mul32x32_64(x[6], y[2]) + mul32x32_64(x[7], y[1]) + mul32x32_64(x[8], y[0]);
	f = (bignum256modm_element_t)c; r1[8] = (f & 0x00ffffff); q1[0] = (f >> 8) & 0x3fffff; c >>= 30;
	c += mul32x32_64(x[1], y[8]) + mul32x32_64(x[2], y[7]) + mul32x32_64(x[3], y[6]) + mul32x32_64(x[4], y[5]) + mul32x32_64(x[5], y[4]) + mul32x32_64(x[6], y[3]) + mul32x32_64(x[7], y[2]) + mul32x32_64(x[8], y[1]);
	f = (bignum256modm_element_t)c; q1[0] = (q1[0] | (f << 22)) & 0x3fffffff; q1[1] = (f >> 8) & 0x3fffff; c >>= 30;
	c += mul32x32_64(x[2], y[8]) + mul32x32_64(x[3], y[7]) + mul32x32_64(x[4], y[6]) + mul32x32_64(x[5], y[5]) + mul32x32_64(x[6], y[4]) + mul32x32_64(x[7], y[3]) + mul32x32_64(x[8], y[2]);
	f = (bignum256modm_element_t)c; q1[1] = (q1[1] | (f << 22)) & 0x3fffffff; q1[2] = (f >> 8) & 0x3fffff; c >>= 30;
	c += mul32x32_64(x[3], y[8]) + mul32x32_64(x[4], y[7]) + mul32x32_64(x[5], y[6]) + mul32x32_64(x[6], y[5]) + mul32x32_64(x[7], y[4]) + mul32x32_64(x[8], y[3]);
	f = (bignum256modm_element_t)c; q1[2] = (q1[2] | (f << 22)) & 0x3fffffff; q1[3] = (f >> 8) & 0x3fffff; c >>= 30;
	c += mul32x32_64(x[4], y[8]) + mul32x32_64(x[5], y[7]) + mul32x32_64(x[6], y[6]) + mul32x32_64(x[7], y[5]) + mul32x32_64(x[8], y[4]);
	f = (bignum256modm_element_t)c; q1[3] = (q1[3] | (f << 22)) & 0x3fffffff; q1[4] = (f >> 8) & 0x3fffff; c >>= 30;
	c += mul32x32_64(x[5], y[8]) + mul32x32_64(x[6], y[7]) + mul32x32_64(x[7], y[6]) + mul32x32_64(x[8], y[5]);
	f = (bignum256modm_element_t)c; q1[4] = (q1[4] | (f << 22)) & 0x3fffffff; q1[5] = (f >> 8) & 0x3fffff; c >>= 30;
	c += mul32x32_64(x[6], y[8]) + mul32x32_64(x[7], y[7]) + mul32x32_64(x[8], y[6]);
	f = (bignum256modm_element_t)c; q1[5] = (q1[5] | (f << 22)) & 0x3fffffff; q1[6] = (f >> 8) & 0x3fffff; c >>= 30;
	c += mul32x32_64(x[7], y[8]) + mul32x32_64(x[8], y[7]);
	f = (bignum256modm_element_t)c; q1[6] = (q1[6] | (f << 22)) & 0x3fffffff; q1[7] = (f >> 8) & 0x3fffff; c >>= 30;
	c += mul32x32_64(x[8], y[8]);
	f = (bignum256modm_element_t)c; q1[7] = (q1[7] | (f << 22)) & 0x3fffffff; q1[8] = (f >> 8) & 0x3fffff;

	barrett_reduce256_modm(r, q1, r1);
}

void expand256_modm(bignum256modm out, const unsigned char *in, size_t len) {
	unsigned char work[64] = {0};
	bignum256modm_element_t x[16] = {0};
	bignum256modm q1 = {0};

	memcpy(work, in, len);
	x[0] = U8TO32_LE(work +  0);
	x[1] = U8TO32_LE(work +  4);
	x[2] = U8TO32_LE(work +  8);
	x[3] = U8TO32_LE(work + 12);
	x[4] = U8TO32_LE(work + 16);
	x[5] = U8TO32_LE(work + 20);
	x[6] = U8TO32_LE(work + 24);
	x[7] = U8TO32_LE(work + 28);
	x[8] = U8TO32_LE(work + 32);
	x[9] = U8TO32_LE(work + 36);
	x[10] = U8TO32_LE(work + 40);
	x[11] = U8TO32_LE(work + 44);
	x[12] = U8TO32_LE(work + 48);
	x[13] = U8TO32_LE(work + 52);
	x[14] = U8TO32_LE(work + 56);
	x[15] = U8TO32_LE(work + 60);

	/* r1 = (x mod 256^(32+1)) = x mod (2^8)(31+1) = x & ((1 << 264) - 1) */
	out[0] = (                         x[0]) & 0x3fffffff;
	out[1] = ((x[ 0] >> 30) | (x[ 1] <<  2)) & 0x3fffffff;
	out[2] = ((x[ 1] >> 28) | (x[ 2] <<  4)) & 0x3fffffff;
	out[3] = ((x[ 2] >> 26) | (x[ 3] <<  6)) & 0x3fffffff;
	out[4] = ((x[ 3] >> 24) | (x[ 4] <<  8)) & 0x3fffffff;
	out[5] = ((x[ 4] >> 22) | (x[ 5] << 10)) & 0x3fffffff;
	out[6] = ((x[ 5] >> 20) | (x[ 6] << 12)) & 0x3fffffff;
	out[7] = ((x[ 6] >> 18) | (x[ 7] << 14)) & 0x3fffffff;
	out[8] = ((x[ 7] >> 16) | (x[ 8] << 16)) & 0x00ffffff;

	/* 8*31 = 248 bits, no need to reduce */
	if (len < 32)
		return;

	/* q1 = x >> 248 = 264 bits = 9 30 bit elements */
	q1[0] = ((x[ 7] >> 24) | (x[ 8] <<  8)) & 0x3fffffff;
	q1[1] = ((x[ 8] >> 22) | (x[ 9] << 10)) & 0x3fffffff;
	q1[2] = ((x[ 9] >> 20) | (x[10] << 12)) & 0x3fffffff;
	q1[3] = ((x[10] >> 18) | (x[11] << 14)) & 0x3fffffff;
	q1[4] = ((x[11] >> 16) | (x[12] << 16)) & 0x3fffffff;
	q1[5] = ((x[12] >> 14) | (x[13] << 18)) & 0x3fffffff;
	q1[6] = ((x[13] >> 12) | (x[14] << 20)) & 0x3fffffff;
	q1[7] = ((x[14] >> 10) | (x[15] << 22)) & 0x3fffffff;
	q1[8] = ((x[15] >>  8)                );

	barrett_reduce256_modm(out, q1, out);
}

void expand_raw256_modm(bignum256modm out, const unsigned char in[32]) {
	bignum256modm_element_t x[8] = {0};

	x[0] = U8TO32_LE(in +  0);
	x[1] = U8TO32_LE(in +  4);
	x[2] = U8TO32_LE(in +  8);
	x[3] = U8TO32_LE(in + 12);
	x[4] = U8TO32_LE(in + 16);
	x[5] = U8TO32_LE(in + 20);
	x[6] = U8TO32_LE(in + 24);
	x[7] = U8TO32_LE(in + 28);

	out[0] = (                         x[0]) & 0x3fffffff;
	out[1] = ((x[ 0] >> 30) | (x[ 1] <<  2)) & 0x3fffffff;
	out[2] = ((x[ 1] >> 28) | (x[ 2] <<  4)) & 0x3fffffff;
	out[3] = ((x[ 2] >> 26) | (x[ 3] <<  6)) & 0x3fffffff;
	out[4] = ((x[ 3] >> 24) | (x[ 4] <<  8)) & 0x3fffffff;
	out[5] = ((x[ 4] >> 22) | (x[ 5] << 10)) & 0x3fffffff;
	out[6] = ((x[ 5] >> 20) | (x[ 6] << 12)) & 0x3fffffff;
	out[7] = ((x[ 6] >> 18) | (x[ 7] << 14)) & 0x3fffffff;
	out[8] = ((x[ 7] >> 16)                ) & 0x0000ffff;
}

int is_reduced256_modm(const bignum256modm in)
{
	int i = 0;
	uint32_t res1 = 0;
	uint32_t res2 = 0;
	for (i = 8; i >= 0; i--) {
		res1 = (res1 << 1) | (in[i] < modm_m[i]);
		res2 = (res2 << 1) | (in[i] > modm_m[i]);
	}
	return res1 > res2;
}

void contract256_modm(unsigned char out[32], const bignum256modm in) {
	U32TO8_LE(out +  0, (in[0]      ) | (in[1] << 30));
	U32TO8_LE(out +  4, (in[1] >>  2) | (in[2] << 28));
	U32TO8_LE(out +  8, (in[2] >>  4) | (in[3] << 26));
	U32TO8_LE(out + 12, (in[3] >>  6) | (in[4] << 24));
	U32TO8_LE(out + 16, (in[4] >>  8) | (in[5] << 22));
	U32TO8_LE(out + 20, (in[5] >> 10) | (in[6] << 20));
	U32TO8_LE(out + 24, (in[6] >> 12) | (in[7] << 18));
	U32TO8_LE(out + 28, (in[7] >> 14) | (in[8] << 16));
}

void contract256_window4_modm(signed char r[64], const bignum256modm in) {
	char carry = 0;
	signed char *quads = r;
	bignum256modm_element_t i = 0, j = 0, v = 0;

	for (i = 0; i < 8; i += 2) {
		v = in[i];
		for (j = 0; j < 7; j++) {
			*quads++ = (v & 15);
			v >>= 4;
		}
		v |= (in[i+1] << 2);
		for (j = 0; j < 8; j++) {
			*quads++ = (v & 15);
			v >>= 4;
		}
	}
	v = in[8];
	*quads++ = (v & 15); v >>= 4;
	*quads++ = (v & 15); v >>= 4;
	*quads++ = (v & 15); v >>= 4;
	*quads++ = (v & 15); v >>= 4;

	/* making it signed */
	carry = 0;
	for(i = 0; i < 63; i++) {
		r[i] += carry;
		r[i+1] += (r[i] >> 4);
		r[i] &= 15;
		carry = (r[i] >> 3);
		r[i] -= (carry << 4);
	}
	r[63] += carry;
}

void contract256_slidingwindow_modm(signed char r[256], const bignum256modm s, int windowsize) {
	int i = 0, j = 0, k = 0, b = 0;
	int m = (1 << (windowsize - 1)) - 1, soplen = 256;
	signed char *bits = r;
	bignum256modm_element_t v = 0;

	/* first put the binary expansion into r  */
	for (i = 0; i < 8; i++) {
		v = s[i];
		for (j = 0; j < 30; j++, v >>= 1)
			*bits++ = (v & 1);
	}
	v = s[8];
	for (j = 0; j < 16; j++, v >>= 1)
		*bits++ = (v & 1);

	/* Making it sliding window */
	for (j = 0; j < soplen; j++) {
		if (!r[j])
			continue;

		for (b = 1; (b < (soplen - j)) && (b <= 6); b++) {
			if ((r[j] + (r[j + b] << b)) <= m) {
				r[j] += r[j + b] << b;
				r[j + b] = 0;
			} else if ((r[j] - (r[j + b] << b)) >= -m) {
				r[j] -= r[j + b] << b;
				for (k = j + b; k < soplen; k++) {
					if (!r[k]) {
						r[k] = 1;
						break;
					}
					r[k] = 0;
				}
			} else if (r[j + b]) {
				break;
			}
		}
	}
}

void set256_modm(bignum256modm r, uint64_t v) {
	r[0] = (bignum256modm_element_t) (v & 0x3fffffff); v >>= 30;
	r[1] = (bignum256modm_element_t) (v & 0x3fffffff); v >>= 30;
	r[2] = (bignum256modm_element_t) (v & 0x3fffffff);
	r[3] = 0;
	r[4] = 0;
	r[5] = 0;
	r[6] = 0;
	r[7] = 0;
	r[8] = 0;
}

int get256_modm(uint64_t * v, const bignum256modm r){
	*v = 0;
	int con1 = 0;

#define NONZ(x) ((((((int64_t)(x)) - 1) >> 32) + 1) & 1)
	bignum256modm_element_t c = 0;
	c  = r[0];  *v +=  (uint64_t)c & 0x3fffffff;        c >>= 30; // 30
	c += r[1];  *v += ((uint64_t)c & 0x3fffffff) << 30; c >>= 30; // 60
	c += r[2];  *v += ((uint64_t)c & 0xf)        << 60; con1 |= NONZ(c>>4); c >>= 30; // 64 bits
	c += r[3];                                          con1 |= NONZ(c); c >>= 30;
	c += r[4];                                          con1 |= NONZ(c); c >>= 30;
	c += r[5];                                          con1 |= NONZ(c); c >>= 30;
	c += r[6];                                          con1 |= NONZ(c); c >>= 30;
	c += r[7];                                          con1 |= NONZ(c); c >>= 30;
	c += r[8];                                          con1 |= NONZ(c); c >>= 30;
	                                                    con1 |= NONZ(c);
#undef NONZ

	return con1 ^ 1;
}

int eq256_modm(const bignum256modm x, const bignum256modm y){
	size_t differentbits = 0;
	int len = bignum256modm_limb_size;
	while (len--) {
		differentbits |= (*x++ ^ *y++);
	}
	return (int) (1 & ((differentbits - 1) >> bignum256modm_bits_per_limb));
}

int cmp256_modm(const bignum256modm x, const bignum256modm y){
	int len = 2*bignum256modm_limb_size;
	uint32_t a_gt = 0;
	uint32_t b_gt = 0;

	// 16B chunks
	while (len--) {
		const uint32_t ln = (const uint32_t) len;
		const uint32_t a = (x[ln>>1] >> 16*(ln & 1)) & 0xffff;
		const uint32_t b = (y[ln>>1] >> 16*(ln & 1)) & 0xffff;

		const uint32_t limb_a_gt = ((b - a) >> 16) & 1;
		const uint32_t limb_b_gt = ((a - b) >> 16) & 1;
		a_gt |= limb_a_gt & ~b_gt;
		b_gt |= limb_b_gt & ~a_gt;
	}

	return a_gt - b_gt;
}

int iszero256_modm(const bignum256modm x){
	size_t differentbits = 0;
	int len = bignum256modm_limb_size;
	while (len--) {
		differentbits |= (*x++);
	}
	return (int) (1 & ((differentbits - 1) >> bignum256modm_bits_per_limb));
}

void copy256_modm(bignum256modm r, const bignum256modm x){
	r[0] = x[0];
	r[1] = x[1];
	r[2] = x[2];
	r[3] = x[3];
	r[4] = x[4];
	r[5] = x[5];
	r[6] = x[6];
	r[7] = x[7];
	r[8] = x[8];
}

int check256_modm(const bignum256modm x){
	int ok = 1;
	bignum256modm t={0}, z={0};

	ok &= iszero256_modm(x) ^ 1;
	barrett_reduce256_modm(t, z, x);
	ok &= eq256_modm(t, x);
	return ok;
}

void mulsub256_modm(bignum256modm r, const bignum256modm a, const bignum256modm b, const bignum256modm c){
	//(cc - aa * bb) % l
	bignum256modm t={0};
	mul256_modm(t, a, b);
	sub256_modm(r, c, t);
}

void muladd256_modm(bignum256modm r, const bignum256modm a, const bignum256modm b, const bignum256modm c){
	//(cc + aa * bb) % l
	bignum256modm t={0};
	mul256_modm(t, a, b);
	add256_modm(r, c, t);
}
