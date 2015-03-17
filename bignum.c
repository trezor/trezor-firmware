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

#include <stdio.h>
#include <string.h>
#include "bignum.h"
#include "secp256k1.h"

inline uint32_t read_be(const uint8_t *data)
{
	return (((uint32_t)data[0]) << 24) |
	       (((uint32_t)data[1]) << 16) |
	       (((uint32_t)data[2]) << 8)  |
	       (((uint32_t)data[3]));
}

inline void write_be(uint8_t *data, uint32_t x)
{
	data[0] = x >> 24;
	data[1] = x >> 16;
	data[2] = x >> 8;
	data[3] = x;
}

void bn_read_be(const uint8_t *in_number, bignum256 *out_number)
{
	int i;
	uint64_t temp = 0;
	for (i = 0; i < 8; i++) {
		temp += (((uint64_t)read_be(in_number + (7 - i) * 4)) << (2 * i));
		out_number->val[i]= temp & 0x3FFFFFFF;
		temp >>= 30;
	}
	out_number->val[8] = temp;
}

void bn_write_be(const bignum256 *in_number, uint8_t *out_number)
{
	int i, shift = 30 + 16 - 32;
	uint64_t temp = in_number->val[8];
	for (i = 0; i < 8; i++) {
		temp <<= 30;
		temp |= in_number->val[7 - i];
		write_be(out_number + i * 4, temp >> shift);
		shift -= 2;
	}
}

void bn_zero(bignum256 *a)
{
	int i;
	for (i = 0; i < 9; i++) {
		a->val[i] = 0;
	}
}

int bn_is_zero(const bignum256 *a)
{
	int i;
	for (i = 0; i < 9; i++) {
		if (a->val[i] != 0) return 0;
	}
	return 1;
}

int bn_is_less(const bignum256 *a, const bignum256 *b)
{
	int i;
	for (i = 8; i >= 0; i--) {
		if (a->val[i] < b->val[i]) return 1;
		if (a->val[i] > b->val[i]) return 0;
	}
	return 0;
}

int bn_is_equal(const bignum256 *a, const bignum256 *b) {
	int i;
	for (i = 0; i < 9; i++) {
		if (a->val[i] != b->val[i]) return 0;
	}
	return 1;
}

int bn_bitlen(const bignum256 *a) {
	int i = 8, j;
	while (i >= 0 && a->val[i] == 0) i--;
	if (i == -1) return 0;
	j = 29;
	while ((a->val[i] & (1 << j)) == 0) j--;
	return i * 30 + j + 1;
}

void bn_lshift(bignum256 *a)
{
	int i;
	for (i = 8; i > 0; i--) {
		a->val[i] = ((a->val[i] << 1) & 0x3FFFFFFF) | ((a->val[i - 1] & 0x20000000) >> 29);
	}
	a->val[0] = (a->val[0] << 1) & 0x3FFFFFFF;
}

void bn_rshift(bignum256 *a)
{
	int i;
	for (i = 0; i < 8; i++) {
		a->val[i] = (a->val[i] >> 1) | ((a->val[i + 1] & 1) << 29);
	}
	a->val[8] >>= 1;
}

// assumes x < 2*prime, result < prime
void bn_mod(bignum256 *x, const bignum256 *prime)
{
	int i = 8;
	uint32_t temp;
	// compare numbers
	while (i >= 0 && prime->val[i] == x->val[i]) i--;
	// if equal
	if (i == -1) {
		// set x to zero
		bn_zero(x);
	} else {
		// if x is greater
		if (x->val[i] > prime->val[i]) {
			// substract p from x
			temp = 0x40000000u;
			for (i = 0; i < 9; i++) {
				temp += x->val[i] - prime->val[i];
				x->val[i] = temp & 0x3FFFFFFF;
				temp >>= 30;
				temp += 0x3FFFFFFFu;
			}
		}
	}
}

// Compute x := k * x  (mod prime)
// both inputs must be smaller than 2 * prime.
// result is reduced to 0 <= x < 2 * prime
// This only works for primes between 2^256-2^196 and 2^256.
// this particular implementation accepts inputs up to 2^263 or 128*prime.
void bn_multiply(const bignum256 *k, bignum256 *x, const bignum256 *prime)
{
	int i, j;
	uint64_t temp = 0;
	uint32_t res[18], coef;

	// compute lower half of long multiplication
	for (i = 0; i < 9; i++)
	{
		for (j = 0; j <= i; j++) {
			temp += k->val[j] * (uint64_t)x->val[i - j];
		}
		res[i] = temp & 0x3FFFFFFFu;
		temp >>= 30;
	}
	// compute upper half
	for (; i < 17; i++)
	{
		for (j = i - 8; j < 9 ; j++) {
			temp += k->val[j] * (uint64_t)x->val[i - j];
		}
		res[i] = temp & 0x3FFFFFFFu;
		temp >>= 30;
	}
	res[17] = temp;
	// res = k * x is a normalized number (every limb < 2^30)
	// 0 <= res < 2^526.
	// compute modulo p division is only estimated so this may give result greater than prime but not bigger than 2 * prime
	for (i = 16; i >= 8; i--) {
		// let k = i-8.
		// invariants:
		//   res[0..(i+1)] = k * x   (mod prime)
		//   0 <= res < 2^(30k + 256) * (2^30 + 1)
		// estimate (res / prime)
		coef = (res[i] >> 16) + (res[i + 1] << 14);
		
		// coef = res / 2^(30k + 256)  rounded down
		// 0 <= coef <= 2^30
		// subtract (coef * 2^(30k) * prime) from res
		// note that we unrolled the first iteration
		temp = 0x1000000000000000ull + res[i - 8] - prime->val[0] * (uint64_t)coef;
		res[i - 8] = temp & 0x3FFFFFFF;
		for (j = 1; j < 9; j++) {
			temp >>= 30;
			temp += 0xFFFFFFFC0000000ull + res[i - 8 + j] - prime->val[j] * (uint64_t)coef;
			res[i - 8 + j] = temp & 0x3FFFFFFF;
		}
		// we don't clear res[i+1] but we never read it again.
		
		// we rely on the fact that prime > 2^256 - 2^196
		//   res = oldres - coef*2^(30k) * prime;
		// and
		//   coef * 2^(30k + 256) <= oldres < (coef+1) * 2^(30k + 256)
		// Hence, 0 <= res < 2^30k (2^256 + coef * (2^256 - prime))
		// Since coef * (2^256 - prime) < 2^226, we get
		//   0 <= res < 2^(30k + 226) (2^30 + 1)
		// Thus the invariant holds again.
	}
	// store the result
	for (i = 0; i < 9; i++) {
		x->val[i] = res[i];
	}
}

// input x can be any normalized number that fits (0 <= x < 2^270).
// prime must be between (2^256 - 2^196) and 2^256
// result is smaller than 2*prime
void bn_fast_mod(bignum256 *x, const bignum256 *prime)
{
	int j;
	uint32_t coef;
	uint64_t temp;

	coef = x->val[8] >> 16;
	if (!coef) return;
	// substract (coef * prime) from x
	// note that we unrolled the first iteration
	temp = 0x1000000000000000ull + x->val[0] - prime->val[0] * (uint64_t)coef;
	x->val[0] = temp & 0x3FFFFFFF;
	for (j = 1; j < 9; j++) {
		temp >>= 30;
		temp += 0xFFFFFFFC0000000ull + x->val[j] - prime->val[j] * (uint64_t)coef;
		x->val[j] = temp & 0x3FFFFFFF;
	}
}

// square root of x = x^((p+1)/4)
// http://en.wikipedia.org/wiki/Quadratic_residue#Prime_or_prime_power_modulus
void bn_sqrt(bignum256 *x, const bignum256 *prime)
{
	// this method compute x^1/2 = x^(prime+1)/4
	uint32_t i, j, limb;
	bignum256 res, p;
	bn_zero(&res); res.val[0] = 1;
	// compute p = (prime+1)/4
	memcpy(&p, prime, sizeof(bignum256));
	p.val[0] += 1;
	bn_rshift(&p);
	bn_rshift(&p);
	for (i = 0; i < 9; i++) {
		// invariants:
		//    x   = old(x)^(2^(i*30))
		//    res = old(x)^(p % 2^(i*30))
		// get the i-th limb of prime - 2
		limb = p.val[i];
		for (j = 0; j < 30; j++) {
			// invariants:
			//    x    = old(x)^(2^(i*30+j))
			//    res  = old(x)^(p % 2^(i*30+j))
			//    limb = (p % 2^(i*30+30)) / 2^(i*30+j)
			if (i == 8 && limb == 0) break;
			if (limb & 1) {
				bn_multiply(x, &res, prime);
			}
			limb >>= 1;
			bn_multiply(x, x, prime);
		}
	}
	bn_mod(&res, prime);
	memcpy(x, &res, sizeof(bignum256));
}

#if ! USE_INVERSE_FAST

#if USE_PRECOMPUTED_IV
#warning USE_PRECOMPUTED_IV will not be used
#endif

// in field G_prime, small but slow
void bn_inverse(bignum256 *x, const bignum256 *prime)
{
	// this method compute x^-1 = x^(prime-2)
	uint32_t i, j, limb;
	bignum256 res;
	bn_zero(&res); res.val[0] = 1;
	for (i = 0; i < 9; i++) {
		// invariants:
		//    x   = old(x)^(2^(i*30))
		//    res = old(x)^((prime-2) % 2^(i*30))
		// get the i-th limb of prime - 2
		limb = prime->val[i];
		// this is not enough in general but fine for secp256k1 because prime->val[0] > 1
		if (i == 0) limb -= 2;
		for (j = 0; j < 30; j++) {
			// invariants:
			//    x    = old(x)^(2^(i*30+j))
			//    res  = old(x)^((prime-2) % 2^(i*30+j))
			//    limb = ((prime-2) % 2^(i*30+30)) / 2^(i*30+j)
			// early abort when only zero bits follow
			if (i == 8 && limb == 0) break;
			if (limb & 1) {
				bn_multiply(x, &res, prime);
			}
			limb >>= 1;
			bn_multiply(x, x, prime);
		}
	}
	bn_mod(&res, prime);
	memcpy(x, &res, sizeof(bignum256));
}

#else

// in field G_prime, big but fast
// this algorithm is based on the Euklidean algorithm
// the result is smaller than 2*prime
void bn_inverse(bignum256 *x, const bignum256 *prime)
{
	int i, j, k, len1, len2, mask;
	uint8_t buf[32];
	uint32_t u[8], v[8], s[9], r[10], temp32;
	uint64_t temp, temp2;
	// reduce x modulo prime
	bn_fast_mod(x, prime);
	bn_mod(x, prime);
	// convert x and prime it to 8x32 bit limb form
	bn_write_be(prime, buf);
	for (i = 0; i < 8; i++) {
		u[i] = read_be(buf + 28 - i * 4);
	}
	bn_write_be(x, buf);
	for (i = 0; i < 8; i++) {
		v[i] = read_be(buf + 28 - i * 4);
	}
	len1 = 8;
	s[0] = 1;
	r[0] = 0;
	len2 = 1;
	k = 0;
	// u = prime, v = x  len1 = numlimbs(u,v)
	// r = 0    , s = 1  len2 = numlimbs(r,s)
	// k = 0
	for (;;) {
		// invariants:
		//   r,s,u,v >= 0
		//   x*-r = u*2^k mod prime
		//   x*s  = v*2^k mod prime
		//   u*s + v*r = prime
		//   floor(log2(u)) + floor(log2(v)) + k <= 510
		//   max(u,v) <= 2^k
		//   gcd(u,v) = 1
		//   len1 = numlimbs(u,v)
		//   len2 = numlimbs(r,s)
		//
		// first u,v are large and s,r small
		// later u,v are small and s,r large

		// if (is_zero(v)) break;
		for (i = 0; i < len1; i++) {
			if (v[i]) break;
		}
		if (i == len1) break;

		// reduce u while it is even
		for (;;) {
			// count up to 30 zero bits of u.
			for (i = 0; i < 30; i++) {
				if (u[0] & (1 << i)) break;
			}
			// if u was odd break
			if (i == 0) break;

			// shift u right by i bits.
			mask = (1 << i) - 1;
			for (j = 0; j + 1 < len1; j++) {
				u[j] = (u[j] >> i) | ((u[j + 1] & mask) << (32 - i));
			}
			u[j] = (u[j] >> i);

			// shift s left by i bits.
			mask = (1 << (32 - i)) - 1;
			s[len2] = s[len2 - 1] >> (32 - i);
			for (j = len2 - 1; j > 0; j--) {
				s[j] = (s[j - 1] >> (32 - i)) | ((s[j] & mask) << i);
			}
			s[0] = (s[0] & mask) << i;
			// update len2 if necessary
			if (s[len2]) {
				r[len2] = 0;
				len2++;
			}
			// add i bits to k.
			k += i;
		}
		// reduce v while it is even
		for (;;) {
			// count up to 30 zero bits of v.
			for (i = 0; i < 30; i++) {
				if (v[0] & (1 << i)) break;
			}
			// if v was odd break
			if (i == 0) break;

			// shift v right by i bits.
			mask = (1 << i) - 1;
			for (j = 0; j + 1 < len1; j++) {
				v[j] = (v[j] >> i) | ((v[j + 1] & mask) << (32 - i));
			}
			v[j] = (v[j] >> i);
			mask = (1 << (32 - i)) - 1;
			// shift r left by i bits.
			r[len2] = r[len2 - 1] >> (32 - i);
			for (j = len2 - 1; j > 0; j--) {
				r[j] = (r[j - 1] >> (32 - i)) | ((r[j] & mask) << i);
			}
			r[0] = (r[0] & mask) << i;
			// update len2 if necessary
			if (r[len2]) {
				s[len2] = 0;
				len2++;
			}
			// add i bits to k.
			k += i;
		}
		
		// invariant is reestablished.
		i = len1 - 1;
		while (i > 0 && u[i] == v[i]) i--;
		if (u[i] > v[i]) {
			// u > v:
			//  u = (u - v)/2;
			temp = 0x100000000ull + u[0] - v[0];
			u[0] = (temp >> 1) & 0x7FFFFFFF;
			temp >>= 32;
			for (i = 1; i < len1; i++) {
				temp += 0xFFFFFFFFull + u[i] - v[i];
				u[i - 1] += (temp & 1) << 31;
				u[i] = (temp >> 1) & 0x7FFFFFFF;
				temp >>= 32;
			}
			temp = temp2 = 0;
			// r += s;
			// s += s;
			for (i = 0; i < len2; i++) {
				temp += s[i];
				temp += r[i];
				temp2 += s[i];
				temp2 += s[i];
				r[i] = temp;
				s[i] = temp2;
				temp >>= 32;
				temp2 >>= 32;
			}
			// expand if necessary.
			if (temp != 0 || temp2 != 0) {
				r[len2] = temp;
				s[len2] = temp2;
				len2++;
			}
			// note that
			//   u'2^(k+1) = (u - v) 2^k = x -(r + s) = x -r' mod prime
			//   v'2^(k+1) = 2*v     2^k = x (s + s) = x s'   mod prime
			//   u's' + v'r' = (u-v)/2(2s) + v(r+s) = us + vr
		} else {
			// v >= u:
			// v = v - u;
			temp = 0x100000000ull + v[0] - u[0];
			v[0] = (temp >> 1) & 0x7FFFFFFF;
			temp >>= 32;
			for (i = 1; i < len1; i++) {
				temp += 0xFFFFFFFFull + v[i] - u[i];
				v[i - 1] += (temp & 1) << 31;
				v[i] = (temp >> 1) & 0x7FFFFFFF;
				temp >>= 32;
			}
			// s = s + r
			// r = r + r
			temp = temp2 = 0;
			for (i = 0; i < len2; i++) {
				temp += s[i];
				temp += r[i];
				temp2 += r[i];
				temp2 += r[i];
				s[i] = temp;
				r[i] = temp2;
				temp >>= 32;
				temp2 >>= 32;
			}
			if (temp != 0 || temp2 != 0) {
				s[len2] = temp;
				r[len2] = temp2;
				len2++;
			}
			// note that
			//   u'2^(k+1) = 2*u     2^k = x -(r + r) = x -r' mod prime
			//   v'2^(k+1) = (v - u) 2^k = x (s + r) = x s'   mod prime
			//   u's' + v'r' = u(r+s) + (v-u)/2(2r) = us + vr
		}
		// adjust len1 if possible.
		if (u[len1 - 1] == 0 && v[len1 - 1] == 0) len1--;
		// increase k
		k++;
	}
	// In the last iteration just before the comparison and subtraction
	// we had u=1, v=1, s+r = prime, k <= 510, 2^k > max(s,r) >= prime/2
	// hence 0 <= r < prime and 255 <= k <= 510.
	//
	// Afterwards r is doubled, k is incremented by 1.
	// Hence 0 <= r < 2*prime and 256 <= k < 512.
	//
	// The invariants give us x*-r = 2^k mod prime,
	// hence r = -2^k * x^-1 mod prime.
	// We need to compute -r/2^k mod prime.

	// convert r to bignum style
	j = r[0] >> 30;
	r[0] = r[0] & 0x3FFFFFFFu;
	for (i = 1; i < len2; i++) {
		uint32_t q = r[i] >> (30 - 2 * i);
		r[i] = ((r[i] << (2 * i)) & 0x3FFFFFFFu) + j;
		j=q;
	}
	r[i] = j;
	i++;
	for (; i < 9; i++) r[i] = 0;

	// r = r mod prime, note that r<2*prime.
	i = 8;
	while (i > 0 && r[i] == prime->val[i]) i--;
	if (r[i] >= prime->val[i]) {
		temp32 = 1;
		for (i = 0; i < 9; i++) {
			temp32 += 0x3FFFFFFF + r[i] - prime->val[i];
			r[i] = temp32 & 0x3FFFFFFF;
			temp32 >>= 30;
		}
	}
	// negate r:  r = prime - r
	temp32 = 1;
	for (i = 0; i < 9; i++) {
		temp32 += 0x3FFFFFFF + prime->val[i] - r[i];
		r[i] = temp32 & 0x3FFFFFFF;
		temp32 >>= 30;
	}
	// now: r = 2^k * x^-1 mod prime
	// compute  r/2^k,  256 <= k < 511
	int done = 0;
#if USE_PRECOMPUTED_IV
	if (prime == &prime256k1) {
		for (j = 0; j < 9; j++) {
			x->val[j] = r[j];
		}
		// secp256k1_iv[k-256] = 2^-k mod prime
		bn_multiply(secp256k1_iv + k - 256, x, prime);
		// bn_fast_mod is unnecessary as bn_multiply already
		//   guarantees x < 2*prime
		bn_fast_mod(x, prime);
		// We don't guarantee x < prime!
		// the slow variant and the slow case below guarantee
		// this.
		done = 1;
	}
#endif
	if (!done) {
		// compute r = r/2^k mod prime
		for (j = 0; j < k; j++) {
			// invariant: r = 2^(k-j) * x^-1 mod prime
			// in each iteration divide r by 2 modulo prime.
			if (r[0] & 1) {
				// r is odd; compute r = (prime + r)/2
				temp32 = r[0] + prime->val[0];
				r[0] = (temp32 >> 1) & 0x1FFFFFFF;
				temp32 >>= 30;
				for (i = 1; i < 9; i++) {
					temp32 += r[i] + prime->val[i];
					r[i - 1] += (temp32 & 1) << 29;
					r[i] = (temp32 >> 1) & 0x1FFFFFFF;
					temp32 >>= 30;
				}
			} else {
				// r = r / 2
				for (i = 0; i < 8; i++) {
					r[i] = (r[i] >> 1) | ((r[i + 1] & 1) << 29);
				}
				r[8] = r[8] >> 1;
			}
		}
		// r = x^-1 mod prime, since j = k
		for (j = 0; j < 9; j++) {
			x->val[j] = r[j];
		}
	}
}
#endif

void bn_normalize(bignum256 *a) {
	int i;
	uint32_t tmp = 0;
	for (i = 0; i < 9; i++) {
		tmp += a->val[i];
		a->val[i] = tmp & 0x3FFFFFFF;
		tmp >>= 30;
	}
}

void bn_addmod(bignum256 *a, const bignum256 *b, const bignum256 *prime)
{
	int i;
	for (i = 0; i < 9; i++) {
		a->val[i] += b->val[i];
	}
	bn_normalize(a);
	bn_fast_mod(a, prime);
	bn_mod(a, prime);
}

void bn_addmodi(bignum256 *a, uint32_t b, const bignum256 *prime) {
	a->val[0] += b;
	bn_normalize(a);
	bn_fast_mod(a, prime);
	bn_mod(a, prime);
}

// res = a - b
// b < 2*prime; result not normalized
void bn_subtractmod(const bignum256 *a, const bignum256 *b, bignum256 *res)
{
	int i;
	uint32_t temp = 0;
	for (i = 0; i < 9; i++) {
		temp += a->val[i] + 2u * prime256k1.val[i] - b->val[i];
		res->val[i] = temp & 0x3FFFFFFF;
		temp >>= 30;
	}
}

// res = a - b ; a > b
void bn_subtract(const bignum256 *a, const bignum256 *b, bignum256 *res)
{
	int i;
	uint32_t tmp = 1;
	for (i = 0; i < 9; i++) {
		tmp += 0x3FFFFFFF + a->val[i] - b->val[i];
		res->val[i] = tmp & 0x3FFFFFFF;
		tmp >>= 30;
	}
}

// a / 58 = a (+r)
void bn_divmod58(bignum256 *a, uint32_t *r)
{
	int i;
	uint32_t rem, tmp;
	rem = a->val[8] % 58;
	a->val[8] /= 58;
	for (i = 7; i >= 0; i--) {
		// 2^30 == 18512790*58 + 4
		tmp = rem * 4 + a->val[i];
		a->val[i] = rem * 18512790 + (tmp / 58);
		rem = tmp % 58;
	}
	*r = rem;
}

#if USE_BN_PRINT
void bn_print(const bignum256 *a)
{
	printf("%04x", a->val[8] & 0x0000FFFF);
	printf("%08x", (a->val[7] << 2) | ((a->val[6] & 0x30000000) >> 28));
	printf("%07x", a->val[6] & 0x0FFFFFFF);
	printf("%08x", (a->val[5] << 2) | ((a->val[4] & 0x30000000) >> 28));
	printf("%07x", a->val[4] & 0x0FFFFFFF);
	printf("%08x", (a->val[3] << 2) | ((a->val[2] & 0x30000000) >> 28));
	printf("%07x", a->val[2] & 0x0FFFFFFF);
	printf("%08x", (a->val[1] << 2) | ((a->val[0] & 0x30000000) >> 28));
	printf("%07x", a->val[0] & 0x0FFFFFFF);
}

void bn_print_raw(const bignum256 *a)
{
	int i;
	for (i = 0; i <= 8; i++) {
		printf("0x%08x, ", a->val[i]);
	}
}
#endif
