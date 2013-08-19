/**
 * Copyright (c) 2013 Tomas Dzetkulic
 * Copyright (c) 2013 Pavol Rusnak
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

#include "rand.h"
#include "sha256.h"
#include "ecdsa.h"
#include "secp256k1.h"
#include "aux.h"

// assumes x < 2*prime
void mod(bignum256 *x, bignum256 const *prime)
{
	int i = 8;
	uint32_t temp;
	// compare numbers
	while (i >= 0 && prime->val[i] == x->val[i]) --i;
	// if equal
	if (i == -1) {
		// set x to zero
		for (i = 0; i < 9; i++) {
			x->val[i] = 0;
		}
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

// x = k * x
// both inputs and result may be bigger than prime but not bigger than 2 * prime
void multiply(const bignum256 *k, bignum256 *x, bignum256 const *prime)
{
	int i, j;
	uint64_t temp = 0;
	uint32_t res[18], coef;

	// compute lower half of long multiplication
	for (i = 0; i < 9; i++)
	{
		for (j = 0; j <= i; j++) {
			temp += k->val[j] * (uint64_t)x->val[i-j];
		}
		res[i] = temp & 0x3FFFFFFFu;
		temp >>= 30;
	}
	// compute upper half
	for (; i < 17; i++)
	{
		for (j = i - 8; j < 9 ; j++) {
			temp += k->val[j] * (uint64_t)x->val[i-j];
		}
		res[i] = temp & 0x3FFFFFFFu;
		temp >>= 30;
	}
	res[17] = temp;
	// compute modulo p division is only estimated so this may give result greater than prime but not bigger than 2 * prime
	for (i = 16; i >= 8; i--) {
		// estimate (res / prime)
		coef = (res[i] >> 16) + (res[i+1] << 14);
		// substract (coef * prime) from res
		temp = 0x1000000000000000llu + res[i-8] - prime->val[0] * (uint64_t)coef;
		res[i-8] = temp & 0x3FFFFFFF;
		for (j = 1; j < 9; j++) {
			temp >>= 30;
			temp += 0xFFFFFFFC0000000llu + res[i-8+j] - prime->val[j] * (uint64_t)coef;
			res[i - 8 + j] = temp & 0x3FFFFFFF;
		}
	}
	// store the result
	for (i = 0; i < 9; i++) {
		x->val[i] = res[i];
	}
}

void fast_mod(bignum256 *x, bignum256 const *prime)
{
	int j;
	uint32_t coef;
	uint64_t temp;

	coef = x->val[8] >> 16;
	if (!coef) return;
	// substract (coef * prime) from x
	temp = 0x1000000000000000llu + x->val[0] - prime->val[0] * (uint64_t)coef;
	x->val[0] = temp & 0x3FFFFFFF;
	for (j = 1; j < 9; j++) {
		temp >>= 30;
		temp += 0xFFFFFFFC0000000llu + x->val[j] - prime->val[j] * (uint64_t)coef;
		x->val[j] = temp & 0x3FFFFFFF;
	}
}

// in field G_prime
void inverse(bignum256 *x, bignum256 const *prime)
{
	int i, j, k, len1, len2, mask;
	uint32_t u[9], v[9], s[10], r[10], temp, temp2;
	fast_mod(x, prime);
	mod(x, prime);
	for (i = 0; i < 9; i++) {
		u[i] = prime->val[i];
		v[i] = x->val[i];
	}
	len1 = 9;
	s[0] = 1;
	r[0] = 0;
	len2 = 1;
	k = 0;
	for (;;) {
		for (i = 0; i < len1; i++) {
			if (v[i]) break;
		}
		if (i == len1) break;
		for (;;) {
			for (i = 0; i < 30; i++) {
				if (u[0] & (1 << i)) break;
			}
			if (i == 0) break;
			mask = (1 << i) - 1;
			for (j = 0; j + 1 < len1; j++) {
				u[j] = (u[j] >> i) | ((u[j + 1] & mask) << (30 - i));
			}
			u[j] = (u[j] >> i);
			mask = (1 << (30 - i)) - 1;
			s[len2] = s[len2 - 1] >> (30 - i);
			for (j = len2 - 1; j > 0; j--) {
				s[j] = (s[j - 1] >> (30 - i)) | ((s[j] & mask) << i);
			}
			s[0] = (s[0] & mask) << i;
			if (s[len2]) {
				r[len2] = 0;
				len2++;
			}
			k += i;
		}
		for (;;) {
			for (i = 0; i < 30; i++) {
				if (v[0] & (1 << i)) break;
			}
			if (i == 0) break;
			mask = (1 << i) - 1;
			for (j = 0; j + 1 < len1; j++) {
				v[j] = (v[j] >> i) | ((v[j + 1] & mask) << (30 - i));
			}
			v[j] = (v[j] >> i);
			mask = (1 << (30 - i)) - 1;
			r[len2] = r[len2 - 1] >> (30 - i);
			for (j = len2 - 1; j > 0; j--) {
				r[j] = (r[j - 1] >> (30 - i)) | ((r[j] & mask) << i);
			}
			r[0] = (r[0] & mask) << i;
			if (r[len2]) {
				s[len2] = 0;
				len2++;
			}
			k += i;
		}
		
		i = len1 - 1;
		while (i>0 && u[i] == v[i]) i--;
		if (u[i] > v[i]) {
			temp = 0x40000000u + u[0] - v[0];
			u[0] = (temp >> 1) & 0x1FFFFFFF;
			temp >>= 30;
			for (i = 1; i < len1; i++) {
				temp += 0x3FFFFFFFu + u[i] - v[i];
				u[i-1] += (temp & 1) << 29;
				u[i] = (temp >> 1) & 0x1FFFFFFF;
				temp >>= 30;
			}
			temp = temp2 = 0;
			for (i = 0; i < len2; i++) {
				temp += s[i] + r[i];
				temp2 += s[i] << 1;
				r[i] = temp & 0x3FFFFFFF;
				s[i] = temp2 & 0x3FFFFFFF;
				temp >>= 30;
				temp2 >>= 30;
			}
			if (temp != 0 || temp2 != 0) {
				r[len2] = temp;
				s[len2] = temp2;
				len2++;
			}
		} else {
			temp = 0x40000000u + v[0] - u[0];
			v[0] = (temp >> 1) & 0x1FFFFFFF;
			temp >>= 30;
			for (i = 1; i < len1; i++) {
				temp += 0x3FFFFFFFu + v[i] - u[i];
				v[i-1] += (temp & 1) << 29;
				v[i] = (temp >> 1) & 0x1FFFFFFF;
				temp >>= 30;
			}
			temp = temp2 = 0;
			for (i = 0; i < len2; i++) {
				temp += s[i] + r[i];
				temp2 += r[i] << 1;
				s[i] = temp & 0x3FFFFFFF;
				r[i] = temp2 & 0x3FFFFFFF;
				temp >>= 30;
				temp2 >>= 30;
			}
			if (temp != 0 || temp2 != 0) {
				s[len2] = temp;
				r[len2] = temp2;
				len2++;
			}
		}
		if (u[len1 - 1] == 0 && v[len1 - 1] == 0) len1--;
		k++;
	}
	i = 8;
	while (i>0 && r[i] == prime->val[i]) i--;
	if (r[i] >= prime->val[i]) {
		temp = 1;
		for (i = 0; i < 9; i++) {
			temp += 0x3FFFFFFF + r[i] - prime->val[i];
			r[i] = temp & 0x3FFFFFFF;
			temp >>= 30;
		}
	}
	temp = 1;
	for (i = 0; i < 9; i++) {
		temp += 0x3FFFFFFF + prime->val[i] - r[i];
		r[i] = temp & 0x3FFFFFFF;
		temp >>= 30;
	}
	int done = 0;
#ifdef USE_PRECOMPUTED_IV
	if (prime == &prime256k1) {
		for (j = 0; j < 9; j++) {
			x->val[j] = r[j];
		}
		multiply(secp256k1_iv + k - 256, x, prime);
		fast_mod(x, prime);
		done = 1;
	}
#endif
	if (!done) {
		for (j = 0; j < k; j++) {
			if (r[0] & 1) {
				temp = r[0] + prime->val[0];
				r[0] = (temp >> 1) & 0x1FFFFFFF;
				temp >>= 30;
				for (i = 1; i < 9; i++) {
					temp += r[i] + prime->val[i];
					r[i-1] += (temp & 1) << 29;
					r[i] = (temp >> 1) & 0x1FFFFFFF;
					temp >>= 30;
				}
			} else {
				for (i = 0; i < 8; i++) {
					r[i] = (r[i] >> 1) | ((r[i+1] & 1) << 29);
				}
				r[8] = r[8] >> 1;
			}
		}
		for (j = 0; j < 9; j++) {
			x->val[j] = r[j];
		}
	}
}

// res = a - b
// b < 2*prime; result not normalized
void fast_substract(const bignum256 *a, const bignum256 *b, bignum256 *res)
{
	int i;
	uint32_t temp = 0;
	for (i = 0; i < 9; i++) {
		temp += a->val[i] + 2u *prime256k1.val[i] - b->val[i];
		res->val[i] = temp & 0x3FFFFFFF;
		temp >>= 30;
	}
}

// cp2 = cp1 + cp2
void point_add(const curve_point *cp1, curve_point *cp2)
{
	int i;
	uint32_t temp;
	bignum256 lambda, inv, xr, yr;
	fast_substract(&(cp2->x), &(cp1->x), &inv);
	inverse(&inv, &prime256k1);
	fast_substract(&(cp2->y), &(cp1->y), &lambda);
	multiply(&inv, &lambda, &prime256k1);
	memcpy(&xr, &lambda, sizeof(bignum256));
	multiply(&xr, &xr, &prime256k1);
	temp = 0;
	for (i = 0; i < 9; i++) {
		temp += xr.val[i] + 3u * prime256k1.val[i] - cp1->x.val[i] - cp2->x.val[i];
		xr.val[i] = temp & 0x3FFFFFFF;
		temp >>= 30;
	}
	fast_mod(&xr, &prime256k1);
	fast_substract(&(cp1->x), &xr, &yr);
	// no need to fast_mod here
	// fast_mod(&yr);
	multiply(&lambda, &yr, &prime256k1);
	fast_substract(&yr, &(cp1->y), &yr);
	fast_mod(&yr, &prime256k1);
	memcpy(&(cp2->x), &xr, sizeof(bignum256));
	memcpy(&(cp2->y), &yr, sizeof(bignum256));
}

#ifndef USE_PRECOMPUTED_CP
// cp = cp + cp
void point_double(curve_point *cp)
{
	int i;
	uint32_t temp;
	bignum256 lambda, inverse_y, xr, yr;
	memcpy(&inverse_y, &(cp->y), sizeof(bignum256));
	inverse(&inverse_y, &prime256k1);
	memcpy(&lambda, &three_over_two256k1, sizeof(bignum256));
	multiply(&inverse_y, &lambda, &prime256k1);
	multiply(&(cp->x), &lambda, &prime256k1);
	multiply(&(cp->x), &lambda, &prime256k1);
	memcpy(&xr, &lambda, sizeof(bignum256));
	multiply(&xr, &xr, &prime256k1);
	temp = 0;
	for (i = 0; i < 9; i++) {
		temp += xr.val[i] + 3u * prime256k1.val[i] - 2u * cp->x.val[i];
		xr.val[i] = temp & 0x3FFFFFFF;
		temp >>= 30;
	}
	fast_mod(&xr, &prime256k1);
	fast_substract(&(cp->x), &xr, &yr);
	// no need to fast_mod here
	// fast_mod(&yr);
	multiply(&lambda, &yr, &prime256k1);
	fast_substract(&yr, &(cp->y), &yr);
	fast_mod(&yr, &prime256k1);
	memcpy(&(cp->x), &xr, sizeof(bignum256));
	memcpy(&(cp->y), &yr, sizeof(bignum256));
}
#endif

// res = k * G
void scalar_multiply(bignum256 *k, curve_point *res)
{
	int i, j;
	// result is zero
	int is_zero = 1;
#ifdef USE_PRECOMPUTED_CP
	int exp = 0;
#else
	curve_point curr;
	// initial res
	memcpy(&curr, &G256k1, sizeof(curve_point));
#endif
	for (i = 0; i < 9; i++) {
		for (j = 0; j < 30; j++) {
			if (i == 8 && (k->val[i] >> j) == 0) break;
			if (k->val[i] & (1u<<j)) {
				if (is_zero) {
#ifdef USE_PRECOMPUTED_CP
					memcpy(res, secp256k1_cp + exp, sizeof(curve_point));
#else
					memcpy(res, &curr, sizeof(curve_point));
#endif
					is_zero = 0;
				} else {
#ifdef USE_PRECOMPUTED_CP
					point_add(secp256k1_cp + exp, res);
#else
					point_add(&curr, res);
#endif
				}
			}
#ifdef USE_PRECOMPUTED_CP
			exp++;
#else
			point_double(&curr);
#endif
		}
	}
	mod(&(res->x), &prime256k1);
	mod(&(res->y), &prime256k1);
}

// write DER encoding of number to buffer
void write_der(const bignum256 *x, uint8_t *buf)
{
	int i, j = 8, k = 8, len = 0;
	uint8_t r = 0, temp;
	buf[0] = 2;
	for (i = 0; i < 32; i++) {
		temp = (x->val[j] >> k) + r;
		k -= 8;
		if (k < 0) {
			r = (x->val[j]) << (-k);
			k += 30;
			j--;
		} else {
			r = 0;
		}
		if (len || temp) {
			buf[2 + len] = temp;
			len++;
		}
	}
	buf[1] = len;
}

// uses secp256k1 curve
// priv_key is a 32 byte big endian stored number
// msg is a data to be signed
// msg_len is the message length
// sig is at least 70 bytes long array for the signature
// sig_len is the pointer to a uint that will contain resulting signature length. note that ((*sig_len) == sig[1]+2)
void ecdsa_sign(uint8_t *priv_key, uint8_t *msg, uint32_t msg_len, uint8_t *sig, uint32_t *sig_len)
{
	uint32_t i;
	uint64_t temp;
	uint8_t hash[32];
	curve_point R;
	bignum256 k, z;
	bignum256 *da = &R.y;
	// compute hash function of message
	sha256(msg, msg_len, hash);
	// if double hash is required uncomment the following line:
	// sha256(hash, 32, hash);

	temp = 0;
	for (i = 0; i < 8; i++) {
		temp += (((uint64_t)read_be(hash + (7 - i) * 4)) << (2 * i));
		z.val[i]= temp & 0x3FFFFFFF;
		temp >>= 30;
	}
	z.val[8] = temp;
	for (;;) {
		// generate random number k
		for (i = 0; i < 8; i++) {
			k.val[i] = random32() & 0x3FFFFFFF;
		}
		k.val[8] = random32() & 0xFFFF;
		// if k is too big or too small, we don't like it
		if (k.val[5] == 0x3FFFFFFF && k.val[6] == 0x3FFFFFFF && k.val[7] == 0x3FFFFFFF && k.val[8] == 0xFFFF) continue;
		if (k.val[5] == 0x0 && k.val[6] == 0x0 && k.val[7] == 0x0 && k.val[8] == 0x0) continue;
		// compute k*G
		scalar_multiply(&k, &R);
		// r = (rx mod n)
		mod(&R.x, &order256k1);
		// if r is zero, we try different k
		for (i = 0; i < 9; i++) {
			if (R.x.val[i] != 0) break;
		}
		if (i == 9) continue;
		inverse(&k, &order256k1);
		temp = 0;
		for (i = 0; i < 8; i++) {
			temp += (((uint64_t)read_be(priv_key + (7 - i) * 4)) << (2 * i));
			da->val[i] = temp & 0x3FFFFFFF;
			temp >>= 30;
		}
		da->val[8] = temp;
		multiply(&R.x, da, &order256k1);
		for (i = 0; i < 8; i++) {
			da->val[i] += z.val[i];
			da->val[i+1] += (da->val[i] >> 30);
			da->val[i] &= 0x3FFFFFFF;
		}
		da->val[8] += z.val[8];
		multiply(da, &k, &order256k1);
		mod(&k, &order256k1);
		for (i = 0; i < 9; i++) {
			if (k.val[i] != 0) break;
		}
		if (i == 9) continue;
		// we are done, R.x and k is the result signature
		break;
	}
	write_der(&R.x, sig + 2);
	i = sig[3] + 2;
	write_der(&k, sig + 2 + i);
	i += sig[3+i] + 2;
	sig[0] = 0x30;
	sig[1] = i;
	*sig_len = i + 2;
}
