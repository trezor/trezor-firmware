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
#include <assert.h>
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

// convert a raw bigendian 256 bit number to a normalized bignum
void bn_read_be(const uint8_t *in_number, bignum256 *out_number)
{
	int i;
	uint32_t temp = 0;
	for (i = 0; i < 8; i++) {
		// invariant: temp = (in_number % 2^(32i)) >> 30i
		// get next limb = (in_number % 2^(32(i+1))) >> 32i
		uint32_t limb = read_be(in_number + (7 - i) * 4);
		// temp = (in_number % 2^(32(i+1))) << 30i
		temp |= limb << (2*i);
		// store 30 bits into val[i]
		out_number->val[i]= temp & 0x3FFFFFFF;
		// prepare temp for next round
		temp = limb >> (30 - 2*i);
	}
	out_number->val[8] = temp;
}

// convert a normalized bignum to a raw bigendian 256 bit number.
// in_number must be normalized and < 2^256.
void bn_write_be(const bignum256 *in_number, uint8_t *out_number)
{
	int i;
	uint32_t temp = in_number->val[8] << 16;
	for (i = 0; i < 8; i++) {
		// invariant: temp = (in_number >> 30*(8-i)) << (16 + 2i)
		uint32_t limb = in_number->val[7 - i];
		temp |= limb >> (14 - 2*i);
		write_be(out_number + i * 4, temp);
		temp = limb << (18 + 2*i);
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

// multiply x by 3/2 modulo prime.
// assumes x < 2*prime,
// guarantees x < 4*prime on exit.
void bn_mult_3_2(bignum256 * x, const bignum256 *prime)
{
	int j;
	uint32_t xodd = -(x->val[0] & 1);
	// compute x = 3*x/2 mod prime
	// if x is odd compute (3*x+prime)/2
	uint32_t tmp1 = (3*x->val[0] + (prime->val[0] & xodd)) >> 1;
	for (j = 0; j < 8; j++) {
		uint32_t tmp2 = (3*x->val[j+1] + (prime->val[j+1] & xodd));
		tmp1 += (tmp2 & 1) << 29;
		x->val[j] = tmp1 & 0x3fffffff;
		tmp1 >>= 30;
		tmp1 += tmp2 >> 1;
	}
	x->val[8] = tmp1;
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

// in field G_prime, big and complicated but fast
// the input must not be 0 mod prime.
// the result is smaller than prime
void bn_inverse(bignum256 *x, const bignum256 *prime)
{
	int i, j, k, cmp;
	struct combo {
		uint32_t a[9];
		int len1;
	} us, vr, *odd, *even;
	uint32_t pp[8];
	uint32_t temp32;
	uint64_t temp;

	// The algorithm is based on Schroeppel et. al. "Almost Modular Inverse"
	// algorithm.  We keep four values u,v,r,s in the combo registers
	// us and vr.  us stores u in the first len1 limbs (little endian)
	// and s in the last 9-len1 limbs (big endian).  vr stores v and r.
	// This is because both u*s and v*r are guaranteed to fit in 8 limbs, so
	// their components are guaranteed to fit in 9.  During the algorithm,
	// the length of u and v shrinks while r and s grow.
	// u,v,r,s correspond to F,G,B,C in Schroeppel's algorithm.

	// reduce x modulo prime.  This is necessary as it has to fit in 8 limbs.
	bn_fast_mod(x, prime);
	bn_mod(x, prime);
	// convert x and prime to 8x32 bit limb form
	temp32 = prime->val[0];
	for (i = 0; i < 8; i++) {
		temp32 |= prime->val[i + 1] << (30-2*i);
		us.a[i] = pp[i] = temp32;
		temp32 = prime->val[i + 1] >> (2+2*i);
	}
	temp32 = x->val[0];
	for (i = 0; i < 8; i++) {
		temp32 |= x->val[i + 1] << (30-2*i);
		vr.a[i] = temp32;
		temp32 = x->val[i + 1] >> (2+2*i);
	}
	us.len1 = 8;
	vr.len1 = 8;
	// set s = 1 and r = 0
	us.a[8] = 1;
	vr.a[8] = 0;
	// set k = 0.
	k = 0;

	// only one of the numbers u,v can be even at any time.  We
	// let even point to that number and odd to the other.
	// Initially the prime u is guaranteed to be odd.
	odd = &us;
	even = &vr;

	// u = prime, v = x  
	// r = 0    , s = 1
	// k = 0
	for (;;) {
		// invariants:
		//   let u = limbs us.a[0..u.len1-1] in little endian, 
		//   let s = limbs us.a[u.len..8] in big endian,
		//   let v = limbs vr.a[0..u.len1-1] in little endian, 
		//   let r = limbs vr.a[u.len..8] in big endian,
		//   r,s >= 0 ; u,v >= 1
		//   x*-r = u*2^k mod prime
		//   x*s  = v*2^k mod prime
		//   u*s + v*r = prime
		//   floor(log2(u)) + floor(log2(v)) + k <= 510
		//   max(u,v) <= 2^k   (*) see comment at end of loop
		//   gcd(u,v) = 1
		//   {odd,even} = {&us, &vr}
 		//   odd->a[0] and odd->a[8] are odd
		//   even->a[0] or even->a[8] is even
		//
		// first u/v are large and r/s small
		// later u/v are small and r/s large
		assert(odd->a[0] & 1);
		assert(odd->a[8] & 1);

		// adjust length of even.
		while (even->a[even->len1 - 1] == 0) {
			even->len1--;
			// if input was 0, return.
			// This simple check prevents crashing with stack underflow
			// or worse undesired behaviour for illegal input.
			if (even->len1 < 0)
				return;
		}

		// reduce even->a while it is even
		while (even->a[0] == 0) {
			// shift right first part of even by a limb
			// and shift left second part of even by a limb.
			for (i = 0; i < 8; i++) {
				even->a[i] = even->a[i+1];
			}
			even->a[i] = 0;
			even->len1--;
			k += 32;
		}
		// count up to 32 zero bits of even->a.
		j = 0;
		while ((even->a[0] & (1 << j)) == 0) {
			j++;
		}
		if (j > 0) {
			// shift first part of even right by j bits.
			for (i = 0; i + 1 < even->len1; i++) {
				even->a[i] = (even->a[i] >> j) | (even->a[i + 1] << (32 - j));
			}
			even->a[i] = (even->a[i] >> j);
			if (even->a[i] == 0) {
				even->len1--;
			} else {
				i++;
			}

			// shift second part of even left by j bits.
			for (; i < 8; i++) {
				even->a[i] = (even->a[i] << j) | (even->a[i + 1] >> (32 - j));
			}
			even->a[i] = (even->a[i] << j);
			// add j bits to k.
			k += j;
		}
		// invariant is reestablished.
		// now both a[0] are odd.
		assert(odd->a[0] & 1);
		assert(odd->a[8] & 1);
		assert(even->a[0] & 1);
		assert((even->a[8] & 1) == 0);

		// cmp > 0 if us.a[0..len1-1] > vr.a[0..len1-1], 
		// cmp = 0 if equal, < 0 if less.
		cmp = us.len1 - vr.len1;
		if (cmp == 0) {
			i = us.len1 - 1;
			while (i >= 0 && us.a[i] == vr.a[i]) i--;
			// both are equal to 1 and we are done.
			if (i == -1)
				break;
			cmp = us.a[i] > vr.a[i] ? 1 : -1;
		}
		if (cmp > 0) {
			even = &us;
			odd = &vr;
		} else {
			even = &vr;
			odd = &us;
		}

		// now even > odd.

		//  even->a[0..len1-1] = (even->a[0..len1-1] - odd->a[0..len1-1]);
		temp = 1;
		for (i = 0; i < odd->len1; i++) {
			temp += 0xFFFFFFFFull + even->a[i] - odd->a[i];
			even->a[i] = temp & 0xFFFFFFFF;
			temp >>= 32;
		}
		for (; i < even->len1; i++) {
			temp += 0xFFFFFFFFull + even->a[i];
			even->a[i] = temp & 0xFFFFFFFF;
			temp >>= 32;
		}
		//  odd->a[len1..8] = (odd->b[len1..8] + even->b[len1..8]);
		temp = 0;
		for (i = 8; i >= even->len1; i--) {
			temp += (uint64_t) odd->a[i] + even->a[i];
			odd->a[i] = temp & 0xFFFFFFFF;
			temp >>= 32;
		}
		for (; i >= odd->len1; i--) {
			temp += (uint64_t) odd->a[i];
			odd->a[i] = temp & 0xFFFFFFFF;
			temp >>= 32;
		}
		// note that
		//  if u > v:
		//   u'2^k = (u - v) 2^k = x(-r) - xs = x(-(r+s)) = x(-r') mod prime
		//   u's' + v'r' = (u-v)s + v(r+s) = us + vr
		//  if u < v:
		//   v'2^k = (v - u) 2^k = xs - x(-r) = x(s+r) = xs' mod prime
		//   u's' + v'r' = u(s+r) + (v-u)r = us + vr

		// even->a[0] is difference between two odd numbers, hence even.
		// odd->a[8] is sum of even and odd number, hence odd.
		assert(odd->a[0] & 1);
		assert(odd->a[8] & 1);
		assert((even->a[0] & 1) == 0);

		// The invariants are (almost) reestablished.
		// The invariant max(u,v) <= 2^k can be invalidated at this point,
		// because odd->a[len1..8] was changed.  We only have
		//
		//     odd->a[len1..8] <= 2^{k+1}
		//
		// Since even->a[0] is even, k will be incremented at the beginning
		// of the next loop while odd->a[len1..8] remains unchanged.
		// So after that, odd->a[len1..8] <= 2^k will hold again.
	}
	// In the last iteration we had u = v and gcd(u,v) = 1.
	// Hence, u=1, v=1, s+r = prime, k <= 510, 2^k > max(s,r) >= prime/2
	// This implies 0 <= s < prime and 255 <= k <= 510.
	//
	// The invariants also give us x*s = 2^k mod prime,
	// hence s = 2^k * x^-1 mod prime.
	// We need to compute s/2^k mod prime.

	// First we compute inverse = -prime^-1 mod 2^32, which we need later.
	// We use the Explicit Quadratic Modular inverse algorithm.
	//   http://arxiv.org/pdf/1209.6626.pdf
	// a^-1  = (2-a) * PROD_i (1 + (a - 1)^(2^i)) mod 2^32
	// the product will converge quickly, because (a-1)^(2^i) will be 
	// zero mod 2^32 after at most five iterations.
	// We want to compute -prime^-1 so we start with (pp[0]-2).
	assert(pp[0] & 1);
	uint32_t amone = pp[0]-1;
	uint32_t inverse = pp[0] - 2;
	while (amone) {
		amone *= amone;
		inverse *= (amone + 1);
	}

	while (k >= 32) {
		// compute s / 2^32 modulo prime.
		// Idea: compute factor, such that
		//   s + factor*prime mod 2^32 == 0
		// i.e. factor = s * -1/prime mod 2^32.
		// Then compute s + factor*prime and shift right by 32 bits.
		uint32_t factor = (inverse * us.a[8]) & 0xffffffff;
		temp = us.a[8] + (uint64_t) pp[0] * factor;
		assert((temp & 0xffffffff) == 0);
		temp >>= 32;
		for (i = 0; i < 7; i++) {
			temp += us.a[8-(i+1)] + (uint64_t) pp[i+1] * factor;
			us.a[8-i] = temp & 0xffffffff;
			temp >>= 32;
		}
		us.a[8-i] = temp & 0xffffffff;
		k -= 32;
	}
	if (k > 0) {
		// compute s / 2^k  modulo prime.
		// Same idea: compute factor, such that
		//   s + factor*prime mod 2^k == 0
		// i.e. factor = s * -1/prime mod 2^k.
		// Then compute s + factor*prime and shift right by k bits.
		uint32_t mask = (1 << k) - 1;
		uint32_t factor = (inverse * us.a[8]) & mask;
		temp = (us.a[8] + (uint64_t) pp[0] * factor) >> k;
		assert(((us.a[8] + pp[0] * factor) & mask) == 0);
		for (i = 0; i < 7; i++) {
			temp += (us.a[8-(i+1)] + (uint64_t) pp[i+1] * factor) << (32 - k);
			us.a[8-i] = temp & 0xffffffff;
			temp >>= 32;
		}
		us.a[8-i] = temp & 0xffffffff;
	}

	// convert s to bignum style
	temp32 = 0;
	for (i = 0; i < 8; i++) {
		x->val[i] = ((us.a[8-i] << (2 * i)) & 0x3FFFFFFFu) | temp32;
		temp32 = us.a[8-i] >> (30 - 2 * i);
	}
	x->val[i] = temp32;
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

// res = a - b mod prime.  More exactly res = a + (2*prime - b).
// precondition: 0 <= b < 2*prime, 0 <= a < prime
// res < 3*prime
void bn_subtractmod(const bignum256 *a, const bignum256 *b, bignum256 *res, const bignum256 *prime)
{
	int i;
	uint32_t temp = 0;
	for (i = 0; i < 9; i++) {
		temp += a->val[i] + 2u * prime->val[i] - b->val[i];
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
		// invariants:
		//   rem = old(a) >> 30(i+1) % 58
		//   a[i+1..8] = old(a[i+1..8])/58
		//   a[0..i]   = old(a[0..i])
		// 2^30 == 18512790*58 + 4
		tmp = rem * 4 + a->val[i];
		// set a[i] = (rem * 2^30 + a[i])/58
		//          = rem * 18512790 + (rem * 4 + a[i])/58
		a->val[i] = rem * 18512790 + (tmp / 58);
		// set rem = (rem * 2^30 + a[i]) mod 58
		//         = (rem * 4 + a[i]) mod 58
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
