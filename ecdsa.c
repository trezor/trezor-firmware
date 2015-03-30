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

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include "bignum.h"
#include "rand.h"
#include "sha2.h"
#include "ripemd160.h"
#include "hmac.h"
#include "ecdsa.h"
#include "base58.h"

// Set cp2 = cp1
void point_copy(const curve_point *cp1, curve_point *cp2)
{
	*cp2 = *cp1;
}

// cp2 = cp1 + cp2
void point_add(const curve_point *cp1, curve_point *cp2)
{
	int i;
	uint32_t temp;
	bignum256 lambda, inv, xr, yr;

	if (point_is_infinity(cp1)) {
		return;
	}
	if (point_is_infinity(cp2)) {
		point_copy(cp1, cp2);
		return;
	}
	if (point_is_equal(cp1, cp2)) {
		point_double(cp2);
		return;
	}
	if (point_is_negative_of(cp1, cp2)) {
		point_set_infinity(cp2);
		return;
	}

	bn_subtractmod(&(cp2->x), &(cp1->x), &inv, &prime256k1);
	bn_inverse(&inv, &prime256k1);
	bn_subtractmod(&(cp2->y), &(cp1->y), &lambda, &prime256k1);
	bn_multiply(&inv, &lambda, &prime256k1);

	// xr = lambda^2 - x1 - x2
	xr = lambda;
	bn_multiply(&xr, &xr, &prime256k1);
	temp = 1;
	for (i = 0; i < 9; i++) {
		temp += 0x3FFFFFFF + xr.val[i] + 2u * prime256k1.val[i] - cp1->x.val[i] - cp2->x.val[i];
		xr.val[i] = temp & 0x3FFFFFFF;
		temp >>= 30;
	}
	bn_fast_mod(&xr, &prime256k1);
	bn_mod(&xr, &prime256k1);

	// yr = lambda (x1 - xr) - y1
	bn_subtractmod(&(cp1->x), &xr, &yr, &prime256k1);
	bn_multiply(&lambda, &yr, &prime256k1);
	bn_subtractmod(&yr, &(cp1->y), &yr, &prime256k1);
	bn_fast_mod(&yr, &prime256k1);
	bn_mod(&yr, &prime256k1);

	cp2->x = xr;
	cp2->y = yr;
}

// cp = cp + cp
void point_double(curve_point *cp)
{
	int i;
	uint32_t temp;
	bignum256 lambda, xr, yr;

	if (point_is_infinity(cp)) {
		return;
	}
	if (bn_is_zero(&(cp->y))) {
		point_set_infinity(cp);
		return;
	}

	// lambda = 3/2 x^2 / y
	lambda = cp->y;
	bn_inverse(&lambda, &prime256k1);
	bn_multiply(&cp->x, &lambda, &prime256k1);
	bn_multiply(&cp->x, &lambda, &prime256k1);
	bn_mult_3_2(&lambda, &prime256k1);

	// xr = lambda^2 - 2*x
	xr = lambda;
	bn_multiply(&xr, &xr, &prime256k1);
	temp = 1;
	for (i = 0; i < 9; i++) {
		temp += 0x3FFFFFFF + xr.val[i] + 2u * (prime256k1.val[i] - cp->x.val[i]);
		xr.val[i] = temp & 0x3FFFFFFF;
		temp >>= 30;
	}
	bn_fast_mod(&xr, &prime256k1);
	bn_mod(&xr, &prime256k1);

	// yr = lambda (x - xr) - y
	bn_subtractmod(&(cp->x), &xr, &yr, &prime256k1);
	bn_multiply(&lambda, &yr, &prime256k1);
	bn_subtractmod(&yr, &(cp->y), &yr, &prime256k1);
	bn_fast_mod(&yr, &prime256k1);
	bn_mod(&yr, &prime256k1);

	cp->x = xr;
	cp->y = yr;
}

// set point to internal representation of point at infinity
void point_set_infinity(curve_point *p)
{
	bn_zero(&(p->x));
	bn_zero(&(p->y));
}

// return true iff p represent point at infinity
// both coords are zero in internal representation
int point_is_infinity(const curve_point *p)
{
	return bn_is_zero(&(p->x)) && bn_is_zero(&(p->y));
}

// return true iff both points are equal
int point_is_equal(const curve_point *p, const curve_point *q)
{
	return bn_is_equal(&(p->x), &(q->x)) && bn_is_equal(&(p->y), &(q->y));
}

// returns true iff p == -q
// expects p and q be valid points on curve other than point at infinity
int point_is_negative_of(const curve_point *p, const curve_point *q)
{
	// if P == (x, y), then -P would be (x, -y) on this curve
	if (!bn_is_equal(&(p->x), &(q->x))) {
		return 0;
	}
	
	// we shouldn't hit this for a valid point
	if (bn_is_zero(&(p->y))) {
		return 0;
	}
	
	return !bn_is_equal(&(p->y), &(q->y));
}

// Negate a (modulo prime) if cond is 0xffffffff, keep it if cond is 0.
// The timing of this function does not depend on cond.
static void conditional_negate(uint32_t cond, bignum256 *a, const bignum256 *prime)
{
	int j;
	uint32_t tmp = 1;
	for (j = 0; j < 8; j++) {
		tmp += 0x3fffffff + prime->val[j] - a->val[j];
		a->val[j] = ((tmp & 0x3fffffff) & cond) | (a->val[j] & ~cond);
		tmp >>= 30;
	}
	tmp += 0x3fffffff + prime->val[j] - a->val[j];
	a->val[j] = ((tmp & 0x3fffffff) & cond) | (a->val[j] & ~cond);
}

typedef struct jacobian_curve_point {
	bignum256 x, y, z;
} jacobian_curve_point;

static void curve_to_jacobian(const curve_point *p, jacobian_curve_point *jp) {
	int i;
	// randomize z coordinate
	for (i = 0; i < 8; i++) {
		jp->z.val[i] = random32() & 0x3FFFFFFF;
	}
	jp->z.val[8] = (random32() & 0x7fff) + 1;
	
	jp->x = jp->z;
	bn_multiply(&jp->z, &jp->x, &prime256k1);
	// x = z^2
	jp->y = jp->x;
	bn_multiply(&jp->z, &jp->y, &prime256k1);
	// y = z^3

	bn_multiply(&p->x, &jp->x, &prime256k1);
	bn_multiply(&p->y, &jp->y, &prime256k1);
	bn_mod(&jp->x, &prime256k1);
	bn_mod(&jp->y, &prime256k1);
}

static void jacobian_to_curve(const jacobian_curve_point *jp, curve_point *p) {
	p->y = jp->z;
	bn_mod(&p->y, &prime256k1);
	bn_inverse(&p->y, &prime256k1);
	// p->y = z^-1
	p->x = p->y;
	bn_multiply(&p->x, &p->x, &prime256k1);
	// p->x = z^-2
	bn_multiply(&p->x, &p->y, &prime256k1);
	// p->y = z^-3
	bn_multiply(&jp->x, &p->x, &prime256k1);
	// p->x = jp->x * z^-2
	bn_multiply(&jp->y, &p->y, &prime256k1);
	// p->y = jp->y * z^-3
	bn_mod(&p->x, &prime256k1);
	bn_mod(&p->y, &prime256k1);
}

static void point_jacobian_add(const curve_point *p1, jacobian_curve_point *p2) {
	bignum256 r, h;
	bignum256 rsq, hcb, hcby2, hsqx2;
	int j;
	uint64_t tmp1;

	/* usual algorithm:
	 *
	 * lambda  = (y1 - y2/z2^3) / (x1 - x2/z2^2)
	 * x3/z3^2 = lambda^2 - x1 - x2/z2^2
	 * y3/z3^3 = lambda * (x2/z2^2 - x3/z3^2) - y2/z2^3
	 *
	 * to get rid of fraction we set
	 *  r = (y1 * z2^3 - y2)  (the numerator of lambda * z2^3)
	 *  h = (x1 * z2^2 - x2)  (the denominator of lambda * z2^2)
	 * Hence,
	 *  lambda = r / (h*z2)
	 *
	 * With z3 = h*z2  (the denominator of lambda)
	 * we get x3 = lambda^2*z3^2 - x1*z3^2 - x2/z2^2*z3^2
	 *           = r^2 - x1*h^2*z2^2 - x2*h^2
	 *           = r^2 - h^2*(x1*z2^2 + x2)
	 *           = r^2 - h^2*(h + 2*x2)
	 *           = r^2 - h^3 - 2*h^2*x2
	 *    and y3 = (lambda * (x2/z2^2 - x3/z3^2) - y2/z2^3) * z3^3
	 *           = r * (h^2*x2 - x3) - h^3*y2
	 */
	 

	/* h = x1*z2^2 - x2
	 * r = y1*z2^3 - y2
	 * x3 = r^2 - h^3 - 2*h^2*x2
	 * y3 = r*(h^2*x2 - x3) - h^3*y2
	 * z3 = h*z2
	 */

	// h = x1 * z2^2 - x2;
	// r = y1 * z2^3 - y2;
	h = p2->z;
	bn_multiply(&h, &h, &prime256k1); // h = z2^2
	r = p2->z;
	bn_multiply(&h, &r, &prime256k1); // r = z2^3

	bn_multiply(&p1->x, &h, &prime256k1);
	bn_subtractmod(&h, &p2->x, &h, &prime256k1);
	// h = x1 * z2^2 - x2;

	bn_multiply(&p1->y, &r, &prime256k1);
	bn_subtractmod(&r, &p2->y, &r, &prime256k1);
	// r = y1 * z2^3 - y2;

	// hsqx2 = h^2
	hsqx2 = h;
	bn_multiply(&hsqx2, &hsqx2, &prime256k1);

	// hcb = h^3
	hcb = h;
	bn_multiply(&hsqx2, &hcb, &prime256k1);

	// hsqx2 = h^2 * x2
	bn_multiply(&p2->x, &hsqx2, &prime256k1);

	// hcby2 = h^3 * y2
	hcby2 = hcb;
	bn_multiply(&p2->y, &hcby2, &prime256k1);

	// rsq = r^2
	rsq = r;
	bn_multiply(&rsq, &rsq, &prime256k1);

	// z3 = h*z2
	bn_multiply(&h, &p2->z, &prime256k1);
	bn_mod(&p2->z, &prime256k1);

	// x3 = r^2 - h^3 - 2h^2x2
	tmp1 = 0;
	for (j = 0; j < 9; j++) {
		tmp1 += (uint64_t) rsq.val[j] + 4*prime256k1.val[j] - hcb.val[j] - 2*hsqx2.val[j];
		assert(tmp1 < 5 * 0x40000000ull);
		p2->x.val[j] = tmp1 & 0x3fffffff;
		tmp1 >>= 30;
	}
	bn_fast_mod(&p2->x, &prime256k1);
	bn_mod(&p2->x, &prime256k1);

	// y3 = r*(h^2x2 - x3) - y2*h^3
	bn_subtractmod(&hsqx2, &p2->x, &p2->y, &prime256k1);
	bn_multiply(&r, &p2->y, &prime256k1);
	bn_subtractmod(&p2->y, &hcby2, &p2->y, &prime256k1);
	bn_fast_mod(&p2->y, &prime256k1);
	bn_mod(&p2->y, &prime256k1);
}

static void point_jacobian_double(jacobian_curve_point *p) {
	bignum256 m, msq, ysq, xysq;
	int j;
	uint32_t tmp1;

	/* usual algorithm:
	 *
	 * lambda  = (3(x/z^2)^2 / 2y/z^3) = 3x^2/2yz
	 * x3/z3^2 = lambda^2 - 2x/z^2
	 * y3/z3^3 = lambda * (x/z^2 - x3/z3^2) - y/z^3
	 *
	 * to get rid of fraction we set
	 *  m = 3/2 x^2
	 * Hence,
	 *  lambda = m / yz
	 *
	 * With z3 = yz  (the denominator of lambda)
	 * we get x3 = lambda^2*z3^2 - 2*x/z^2*z3^2
	 *           = m^2 - 2*xy^2
	 *    and y3 = (lambda * (x/z^2 - x3/z3^2) - y/z^3) * z3^3
	 *           = m * (xy^2 - x3) - y^4
	 */
	 

	/* m = 3/2*x*x
	 * x3 = m^2 - 2*xy^2
	 * y3 = m*(xy^2 - x3) - 8y^4
	 * z3 = y*z
	 */

	m = p->x;
	bn_multiply(&m, &m, &prime256k1);
	bn_mult_3_2(&m, &prime256k1);

	// msq = m^2
	msq = m;
	bn_multiply(&msq, &msq, &prime256k1);
	// ysq = y^2
	ysq = p->y;
	bn_multiply(&ysq, &ysq, &prime256k1);
	// xysq = xy^2
	xysq = p->x;
	bn_multiply(&ysq, &xysq, &prime256k1);

	// z3 = yz
	bn_multiply(&p->y, &p->z, &prime256k1);
	bn_mod(&p->z, &prime256k1);

	// x3 = m^2 - 2*xy^2
	tmp1 = 0;
	for (j = 0; j < 9; j++) {
		tmp1 += msq.val[j] + 3*prime256k1.val[j] - 2*xysq.val[j];
		p->x.val[j] = tmp1 & 0x3fffffff;
		tmp1 >>= 30;
	}
	bn_fast_mod(&p->x, &prime256k1);
	bn_mod(&p->x, &prime256k1);

	// y3 = m*(xy^2 - x3) - y^4
	bn_subtractmod(&xysq, &p->x, &p->y, &prime256k1);
	bn_multiply(&m, &p->y, &prime256k1);
	bn_multiply(&ysq, &ysq, &prime256k1);
	bn_subtractmod(&p->y, &ysq, &p->y, &prime256k1);
	bn_fast_mod(&p->y, &prime256k1);
	bn_mod(&p->y, &prime256k1);
}

// res = k * p
void point_multiply(const bignum256 *k, const curve_point *p, curve_point *res)
{
	// this algorithm is loosely based on
	//  Katsuyuki Okeya and Tsuyoshi Takagi, The Width-w NAF Method Provides
	//  Small Memory and Fast Elliptic Scalar Multiplications Secure against
	//  Side Channel Attacks.
	assert (bn_is_less(k, &order256k1));

	int i, j;
	int pos, shift;
	bignum256 a;
	uint32_t is_even = (k->val[0] & 1) - 1;
	uint32_t bits, sign, nsign;
	jacobian_curve_point jres;
	curve_point pmult[8];

	// is_even = 0xffffffff if k is even, 0 otherwise.

	// add 2^256.
	// make number odd: subtract order256k1 if even
	uint32_t tmp = 1;
	uint32_t is_non_zero = 0;
	for (j = 0; j < 8; j++) {
		is_non_zero |= k->val[j];
		tmp += 0x3fffffff + k->val[j] - (order256k1.val[j] & is_even);
		a.val[j] = tmp & 0x3fffffff;
		tmp >>= 30;
	}
	is_non_zero |= k->val[j];
	a.val[j] = tmp + 0xffff + k->val[j] - (order256k1.val[j] & is_even);
	assert((a.val[0] & 1) != 0);

	// special case 0*p:  just return zero. We don't care about constant time.
	if (!is_non_zero) {
		point_set_infinity(res);
		return;
	}

	// Now a = k + 2^256 (mod order256k1) and a is odd.
	//
	// The idea is to bring the new a into the form.
	// sum_{i=0..64} a[i] 16^i,  where |a[i]| < 16 and a[i] is odd.
	// a[0] is odd, since a is odd.  If a[i] would be even, we can
	// add 1 to it and subtract 16 from a[i-1].  Afterwards,
	// a[64] = 1, which is the 2^256 that we added before.
	//
	// Since k = a - 2^256 (mod order256k1), we can compute
	//   k*p = sum_{i=0..63} a[i] 16^i * p
	//
	// We compute |a[i]| * p in advance for all possible
	// values of |a[i]| * p.  pmult[i] = (2*i+1) * p
	// We compute p, 3*p, ..., 15*p and store it in the table pmult.
	// store p^2 temporarily in pmult[7]
	pmult[7] = *p;
	point_double(&pmult[7]);
	// compute 3*p, etc by repeatedly adding p^2.
	pmult[0] = *p;
	for (i = 1; i < 8; i++) {
		pmult[i] = pmult[7];
		point_add(&pmult[i-1], &pmult[i]);
	}

	// now compute  res = sum_{i=0..63} a[i] * 16^i * p step by step,
	// starting with i = 63.
	// initialize jres = |a[63]| * p.
	// Note that a[i] = a>>(4*i) & 0xf if (a&0x10) != 0
	// and - (16 - (a>>(4*i) & 0xf)) otherwise.   We can compute this as
	//   ((a ^ (((a >> 4) & 1) - 1)) & 0xf) >> 1
	// since a is odd.
	bits = a.val[8] >> 12;
	sign = (bits >> 4) - 1;
	bits ^= sign;
	bits &= 15;
	curve_to_jacobian(&pmult[bits>>1], &jres);
	for (i = 62; i >= 0; i--) {
		// sign = sign(a[i+1])  (0xffffffff for negative, 0 for positive)
		// invariant jres = (-1)^sign sum_{j=i+1..63} (a[j] * 16^{j-i-1} * p)

		point_jacobian_double(&jres);
		point_jacobian_double(&jres);
		point_jacobian_double(&jres);
		point_jacobian_double(&jres);

		// get lowest 5 bits of a >> (i*4).
		pos = i*4/30; shift = i*4 % 30;
		bits = (a.val[pos+1]<<(30-shift) | a.val[pos] >> shift) & 31;
		nsign = (bits >> 4) - 1;
		bits ^= nsign;
		bits &= 15;

		// negate last result to make signs of this round and the
		// last round equal.
		conditional_negate(sign ^ nsign, &jres.z, &prime256k1);
		
		// add odd factor
		point_jacobian_add(&pmult[bits >> 1], &jres);
		sign = nsign;
	}
	conditional_negate(sign, &jres.z, &prime256k1);
	jacobian_to_curve(&jres, res);
}

#if USE_PRECOMPUTED_CP

// res = k * G
// k must be a normalized number with 0 <= k < order256k1
void scalar_multiply(const bignum256 *k, curve_point *res)
{
	assert (bn_is_less(k, &order256k1));

	int i, j;
	bignum256 a;
	uint32_t is_even = (k->val[0] & 1) - 1;
	uint32_t lowbits;
	jacobian_curve_point jres;

	// is_even = 0xffffffff if k is even, 0 otherwise.

	// add 2^256.
	// make number odd: subtract order256k1 if even
	uint32_t tmp = 1;
	uint32_t is_non_zero = 0;
	for (j = 0; j < 8; j++) {
		is_non_zero |= k->val[j];
		tmp += 0x3fffffff + k->val[j] - (order256k1.val[j] & is_even);
		a.val[j] = tmp & 0x3fffffff;
		tmp >>= 30;
	}
	is_non_zero |= k->val[j];
	a.val[j] = tmp + 0xffff + k->val[j] - (order256k1.val[j] & is_even);
	assert((a.val[0] & 1) != 0);

	// special case 0*G:  just return zero. We don't care about constant time.
	if (!is_non_zero) {
		point_set_infinity(res);
		return;
	}

	// Now a = k + 2^256 (mod order256k1) and a is odd.
	//
	// The idea is to bring the new a into the form.
	// sum_{i=0..64} a[i] 16^i,  where |a[i]| < 16 and a[i] is odd.
	// a[0] is odd, since a is odd.  If a[i] would be even, we can
	// add 1 to it and subtract 16 from a[i-1].  Afterwards,
	// a[64] = 1, which is the 2^256 that we added before.
	//
	// Since k = a - 2^256 (mod order256k1), we can compute
	//   k*G = sum_{i=0..63} a[i] 16^i * G
	//
	// We have a big table secp256k1_cp that stores all possible
	// values of |a[i]| 16^i * G.
	// secp256k1_cp[i][j] = (2*j+1) * 16^i * G

	// now compute  res = sum_{i=0..63} a[i] * 16^i * G step by step.
	// initial res = |a[0]| * G.  Note that a[0] = a & 0xf if (a&0x10) != 0
	// and - (16 - (a & 0xf)) otherwise.   We can compute this as
	//   ((a ^ (((a >> 4) & 1) - 1)) & 0xf) >> 1
	// since a is odd.
	lowbits = a.val[0] & ((1 << 5) - 1);
	lowbits ^= (lowbits >> 4) - 1;
	lowbits &= 15;
	curve_to_jacobian(&secp256k1_cp[0][lowbits >> 1], &jres);
	for (i = 1; i < 64; i ++) {
		// invariant res = sign(a[i-1]) sum_{j=0..i-1} (a[j] * 16^j * G)

		// shift a by 4 places.
		for (j = 0; j < 8; j++) {
			a.val[j] = (a.val[j] >> 4) | ((a.val[j + 1] & 0xf) << 26);
		}
		a.val[j] >>= 4;
		// a = old(a)>>(4*i)
		// a is even iff sign(a[i-1]) = -1

		lowbits = a.val[0] & ((1 << 5) - 1);
		lowbits ^= (lowbits >> 4) - 1;
		lowbits &= 15;
		// negate last result to make signs of this round and the
		// last round equal.
		conditional_negate((lowbits & 1) - 1, &jres.y, &prime256k1);
		
		// add odd factor
		point_jacobian_add(&secp256k1_cp[i][lowbits >> 1], &jres);
	}
	conditional_negate(((a.val[0] >> 4) & 1) - 1, &jres.y, &prime256k1);
	jacobian_to_curve(&jres, res);
}

#else

void scalar_multiply(const bignum256 *k, curve_point *res)
{
	point_multiply(k, &G256k1, res);
}

#endif

// generate random K for signing
int generate_k_random(bignum256 *k) {
	int i, j;
	for (j = 0; j < 10000; j++) {
		for (i = 0; i < 8; i++) {
			k->val[i] = random32() & 0x3FFFFFFF;
		}
		k->val[8] = random32() & 0xFFFF;
		// if k is too big or too small, we don't like it
		if ( !bn_is_zero(k) && bn_is_less(k, &order256k1) ) {
			return 0; // good number - no error
		}
	}
	// we generated 10000 numbers, none of them is good -> fail
	return 1;
}

// generate K in a deterministic way, according to RFC6979
// http://tools.ietf.org/html/rfc6979
int generate_k_rfc6979(bignum256 *secret, const uint8_t *priv_key, const uint8_t *hash)
{
	int i;
	uint8_t v[32], k[32], bx[2*32], buf[32 + 1 + sizeof(bx)];
	bignum256 z1;

	memcpy(bx, priv_key, 32);
	bn_read_be(hash, &z1);
	bn_mod(&z1, &order256k1);
	bn_write_be(&z1, bx + 32);

	memset(v, 1, sizeof(v));
	memset(k, 0, sizeof(k));

	memcpy(buf, v, sizeof(v));
	buf[sizeof(v)] = 0x00;
	memcpy(buf + sizeof(v) + 1, bx, 64);
	hmac_sha256(k, sizeof(k), buf, sizeof(buf), k);
	hmac_sha256(k, sizeof(k), v, sizeof(v), v);

	memcpy(buf, v, sizeof(v));
	buf[sizeof(v)] = 0x01;
	memcpy(buf + sizeof(v) + 1, bx, 64);
	hmac_sha256(k, sizeof(k), buf, sizeof(buf), k);
	hmac_sha256(k, sizeof(k), v, sizeof(v), v);

	for (i = 0; i < 10000; i++) {
		hmac_sha256(k, sizeof(k), v, sizeof(v), v);
		bn_read_be(v, secret);
		if ( !bn_is_zero(secret) && bn_is_less(secret, &order256k1) ) {
			return 0; // good number -> no error
		}
		memcpy(buf, v, sizeof(v));
		buf[sizeof(v)] = 0x00;
		hmac_sha256(k, sizeof(k), buf, sizeof(v) + 1, k);
		hmac_sha256(k, sizeof(k), v, sizeof(v), v);
	}
	// we generated 10000 numbers, none of them is good -> fail
	return 1;
}

// msg is a data to be signed
// msg_len is the message length
int ecdsa_sign(const uint8_t *priv_key, const uint8_t *msg, uint32_t msg_len, uint8_t *sig, uint8_t *pby)
{
	uint8_t hash[32];
	sha256_Raw(msg, msg_len, hash);
	return ecdsa_sign_digest(priv_key, hash, sig, pby);
}

// msg is a data to be signed
// msg_len is the message length
int ecdsa_sign_double(const uint8_t *priv_key, const uint8_t *msg, uint32_t msg_len, uint8_t *sig, uint8_t *pby)
{
	uint8_t hash[32];
	sha256_Raw(msg, msg_len, hash);
	sha256_Raw(hash, 32, hash);
	return ecdsa_sign_digest(priv_key, hash, sig, pby);
}

// uses secp256k1 curve
// priv_key is a 32 byte big endian stored number
// sig is 64 bytes long array for the signature
// digest is 32 bytes of digest
int ecdsa_sign_digest(const uint8_t *priv_key, const uint8_t *digest, uint8_t *sig, uint8_t *pby)
{
	uint32_t i;
	curve_point R;
	bignum256 k, z;
	bignum256 *da = &R.y;

	bn_read_be(digest, &z);

#if USE_RFC6979
	// generate K deterministically
	if (generate_k_rfc6979(&k, priv_key, digest) != 0) {
		return 1;
	}
#else
	// generate random number k
	if (generate_k_random(&k) != 0) {
		return 1;
	}
#endif

	// compute k*G
	scalar_multiply(&k, &R);
	if (pby) {
		*pby = R.y.val[0] & 1;
	}
	// r = (rx mod n)
	bn_mod(&R.x, &order256k1);
	// if r is zero, we fail
	if (bn_is_zero(&R.x)) return 2;
	bn_inverse(&k, &order256k1);
	bn_read_be(priv_key, da);
	bn_multiply(&R.x, da, &order256k1);
	for (i = 0; i < 8; i++) {
		da->val[i] += z.val[i];
		da->val[i + 1] += (da->val[i] >> 30);
		da->val[i] &= 0x3FFFFFFF;
	}
	da->val[8] += z.val[8];
	bn_multiply(da, &k, &order256k1);
	bn_mod(&k, &order256k1);
	// if k is zero, we fail
	if (bn_is_zero(&k)) return 3;

	// if S > order/2 => S = -S
	if (bn_is_less(&order256k1_half, &k)) {
		bn_subtract(&order256k1, &k, &k);
		if (pby) {
			*pby = !*pby;
		}
	}

	// we are done, R.x and k is the result signature
	bn_write_be(&R.x, sig);
	bn_write_be(&k, sig + 32);

	return 0;
}

void ecdsa_get_public_key33(const uint8_t *priv_key, uint8_t *pub_key)
{
	curve_point R;
	bignum256 k;

	bn_read_be(priv_key, &k);
	// compute k*G
	scalar_multiply(&k, &R);
	pub_key[0] = 0x02 | (R.y.val[0] & 0x01);
	bn_write_be(&R.x, pub_key + 1);
}

void ecdsa_get_public_key65(const uint8_t *priv_key, uint8_t *pub_key)
{
	curve_point R;
	bignum256 k;

	bn_read_be(priv_key, &k);
	// compute k*G
	scalar_multiply(&k, &R);
	pub_key[0] = 0x04;
	bn_write_be(&R.x, pub_key + 1);
	bn_write_be(&R.y, pub_key + 33);
}

void ecdsa_get_pubkeyhash(const uint8_t *pub_key, uint8_t *pubkeyhash)
{
	uint8_t h[32];
	if (pub_key[0] == 0x04) {  // uncompressed format
		sha256_Raw(pub_key, 65, h);
	} else if (pub_key[0] == 0x00) { // point at infinity
		sha256_Raw(pub_key, 1, h);
	} else {
		sha256_Raw(pub_key, 33, h); // expecting compressed format
	}
	ripemd160(h, 32, pubkeyhash);
}

void ecdsa_get_address_raw(const uint8_t *pub_key, uint8_t version, uint8_t *addr_raw)
{
	addr_raw[0] = version;
	ecdsa_get_pubkeyhash(pub_key, addr_raw + 1);
}

void ecdsa_get_address(const uint8_t *pub_key, uint8_t version, char *addr, int addrsize)
{
	uint8_t raw[21];
	ecdsa_get_address_raw(pub_key, version, raw);
	base58_encode_check(raw, 21, addr, addrsize);
}

void ecdsa_get_wif(const uint8_t *priv_key, uint8_t version, char *wif, int wifsize)
{
	uint8_t data[34];
	data[0] = version;
	memcpy(data + 1, priv_key, 32);
	data[33] = 0x01;
	base58_encode_check(data, 34, wif, wifsize);
}

int ecdsa_address_decode(const char *addr, uint8_t *out)
{
	if (!addr) return 0;
	return base58_decode_check(addr, out, 21) == 21;
}

void uncompress_coords(uint8_t odd, const bignum256 *x, bignum256 *y)
{
	// y^2 = x^3 + 0*x + 7
	memcpy(y, x, sizeof(bignum256));       // y is x
	bn_multiply(x, y, &prime256k1);        // y is x^2
	bn_multiply(x, y, &prime256k1);        // y is x^3
	bn_addmodi(y, 7, &prime256k1);         // y is x^3 + 7
	bn_sqrt(y, &prime256k1);               // y = sqrt(y)
	if ((odd & 0x01) != (y->val[0] & 1)) {
		bn_subtract(&prime256k1, y, y);   // y = -y
	}
}

int ecdsa_read_pubkey(const uint8_t *pub_key, curve_point *pub)
{
	if (pub_key[0] == 0x04) {
		bn_read_be(pub_key + 1, &(pub->x));
		bn_read_be(pub_key + 33, &(pub->y));
		return ecdsa_validate_pubkey(pub);
	}
	if (pub_key[0] == 0x02 || pub_key[0] == 0x03) { // compute missing y coords
		bn_read_be(pub_key + 1, &(pub->x));
		uncompress_coords(pub_key[0], &(pub->x), &(pub->y));
		return ecdsa_validate_pubkey(pub);
	}
	// error
	return 0;
}

// Verifies that:
//   - pub is not the point at infinity.
//   - pub->x and pub->y are in range [0,p-1].
//   - pub is on the curve.

int ecdsa_validate_pubkey(const curve_point *pub)
{
	bignum256 y_2, x_3_b;

	if (point_is_infinity(pub)) {
		return 0;
	}

	if (!bn_is_less(&(pub->x), &prime256k1) || !bn_is_less(&(pub->y), &prime256k1)) {
		return 0;
	}

	memcpy(&y_2, &(pub->y), sizeof(bignum256));
	memcpy(&x_3_b, &(pub->x), sizeof(bignum256));

	// y^2
	bn_multiply(&(pub->y), &y_2, &prime256k1);
	bn_mod(&y_2, &prime256k1);

	// x^3 + b
	bn_multiply(&(pub->x), &x_3_b, &prime256k1);
	bn_multiply(&(pub->x), &x_3_b, &prime256k1);
	bn_addmodi(&x_3_b, 7, &prime256k1);

	if (!bn_is_equal(&x_3_b, &y_2)) {
		return 0;
	}

	return 1;
}

// uses secp256k1 curve
// pub_key - 65 bytes uncompressed key
// signature - 64 bytes signature
// msg is a data that was signed
// msg_len is the message length

int ecdsa_verify(const uint8_t *pub_key, const uint8_t *sig, const uint8_t *msg, uint32_t msg_len)
{
	uint8_t hash[32];
	sha256_Raw(msg, msg_len, hash);
	return ecdsa_verify_digest(pub_key, sig, hash);
}

int ecdsa_verify_double(const uint8_t *pub_key, const uint8_t *sig, const uint8_t *msg, uint32_t msg_len)
{
	uint8_t hash[32];
	sha256_Raw(msg, msg_len, hash);
	sha256_Raw(hash, 32, hash);
	return ecdsa_verify_digest(pub_key, sig, hash);
}

// returns 0 if verification succeeded
int ecdsa_verify_digest(const uint8_t *pub_key, const uint8_t *sig, const uint8_t *digest)
{
	curve_point pub, res;
	bignum256 r, s, z;

	if (!ecdsa_read_pubkey(pub_key, &pub)) {
		return 1;
	}

	bn_read_be(sig, &r);
	bn_read_be(sig + 32, &s);

	bn_read_be(digest, &z);

	if (bn_is_zero(&r) || bn_is_zero(&s) ||
	    (!bn_is_less(&r, &order256k1)) ||
	    (!bn_is_less(&s, &order256k1))) return 2;

	bn_inverse(&s, &order256k1); // s^-1
	bn_multiply(&s, &z, &order256k1); // z*s^-1
	bn_mod(&z, &order256k1);
	bn_multiply(&r, &s, &order256k1); // r*s^-1
	bn_mod(&s, &order256k1);
	if (bn_is_zero(&z)) {
		// our message hashes to zero
		// I don't expect this to happen any time soon
		return 3;
	} else {
		scalar_multiply(&z, &res);
	}

	// both pub and res can be infinity, can have y = 0 OR can be equal -> false negative
	point_multiply(&s, &pub, &pub);
	point_add(&pub, &res);
	bn_mod(&(res.x), &order256k1);

	// signature does not match
	if (!bn_is_equal(&res.x, &r)) return 5;

	// all OK
	return 0;
}

int ecdsa_sig_to_der(const uint8_t *sig, uint8_t *der)
{
	int i;
	uint8_t *p = der, *len, *len1, *len2;
	*p = 0x30; p++;                        // sequence
	*p = 0x00; len = p; p++;               // len(sequence)

	*p = 0x02; p++;                        // integer
	*p = 0x00; len1 = p; p++;              // len(integer)

	// process R
	i = 0;
	while (sig[i] == 0 && i < 32) { i++; } // skip leading zeroes
	if (sig[i] >= 0x80) { // put zero in output if MSB set
		*p = 0x00; p++; *len1 = *len1 + 1;
	}
	while (i < 32) { // copy bytes to output
		*p = sig[i]; p++; *len1 = *len1 + 1; i++;
	}

	*p = 0x02; p++;                        // integer
	*p = 0x00; len2 = p; p++;              // len(integer)

	// process S
	i = 32;
	while (sig[i] == 0 && i < 64) { i++; } // skip leading zeroes
	if (sig[i] >= 0x80) { // put zero in output if MSB set
		*p = 0x00; p++; *len2 = *len2 + 1;
	}
	while (i < 64) { // copy bytes to output
		*p = sig[i]; p++; *len2 = *len2 + 1; i++;
	}

	*len = *len1 + *len2 + 4;
	return *len + 2;
}
