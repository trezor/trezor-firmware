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

#include "bignum.h"
#include "rand.h"
#include "sha2.h"
#include "ripemd160.h"
#include "hmac.h"
#include "ecdsa.h"

// cp2 = cp1 + cp2
void point_add(const curve_point *cp1, curve_point *cp2)
{
	int i;
	uint32_t temp;
	bignum256 lambda, inv, xr, yr;
	bn_substract(&(cp2->x), &(cp1->x), &inv);
	bn_inverse(&inv, &prime256k1);
	bn_substract(&(cp2->y), &(cp1->y), &lambda);
	bn_multiply(&inv, &lambda, &prime256k1);
	memcpy(&xr, &lambda, sizeof(bignum256));
	bn_multiply(&xr, &xr, &prime256k1);
	temp = 0;
	for (i = 0; i < 9; i++) {
		temp += xr.val[i] + 3u * prime256k1.val[i] - cp1->x.val[i] - cp2->x.val[i];
		xr.val[i] = temp & 0x3FFFFFFF;
		temp >>= 30;
	}
	bn_fast_mod(&xr, &prime256k1);
	bn_substract(&(cp1->x), &xr, &yr);
	// no need to fast_mod here
	// bn_fast_mod(&yr);
	bn_multiply(&lambda, &yr, &prime256k1);
	bn_substract(&yr, &(cp1->y), &yr);
	bn_fast_mod(&yr, &prime256k1);
	memcpy(&(cp2->x), &xr, sizeof(bignum256));
	memcpy(&(cp2->y), &yr, sizeof(bignum256));
}

// cp = cp + cp
void point_double(curve_point *cp)
{
	int i;
	uint32_t temp;
	bignum256 lambda, inverse_y, xr, yr;
	memcpy(&inverse_y, &(cp->y), sizeof(bignum256));
	bn_inverse(&inverse_y, &prime256k1);
	memcpy(&lambda, &three_over_two256k1, sizeof(bignum256));
	bn_multiply(&inverse_y, &lambda, &prime256k1);
	bn_multiply(&(cp->x), &lambda, &prime256k1);
	bn_multiply(&(cp->x), &lambda, &prime256k1);
	memcpy(&xr, &lambda, sizeof(bignum256));
	bn_multiply(&xr, &xr, &prime256k1);
	temp = 0;
	for (i = 0; i < 9; i++) {
		temp += xr.val[i] + 3u * prime256k1.val[i] - 2u * cp->x.val[i];
		xr.val[i] = temp & 0x3FFFFFFF;
		temp >>= 30;
	}
	bn_fast_mod(&xr, &prime256k1);
	bn_substract(&(cp->x), &xr, &yr);
	// no need to fast_mod here
	// bn_fast_mod(&yr);
	bn_multiply(&lambda, &yr, &prime256k1);
	bn_substract(&yr, &(cp->y), &yr);
	bn_fast_mod(&yr, &prime256k1);
	memcpy(&(cp->x), &xr, sizeof(bignum256));
	memcpy(&(cp->y), &yr, sizeof(bignum256));
}

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
			if (k->val[i] & (1u << j)) {
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
	bn_mod(&(res->x), &prime256k1);
	bn_mod(&(res->y), &prime256k1);
}

// does not validate that this is valid der encoding
// assumes it is der encoding containing 1 number
void der_read_single(const uint8_t *der, bignum256 *elem)
{
	int i, j;
	uint8_t val[32];
	i = 1 + der[1];
	j = 31;
	// we ignore all bytes after 32nd. if there are any, those are either zero or invalid for secp256k1
	while (i > 1 && j >= 0) {
		val[j] = der[i];
		i--; j--;
	}
	for (i = 0; i <= j; i++) {
		val[i] = 0;
	}
	bn_read_be(val, elem);
}

// does not validate that this is valid der encoding
// assumes it is der encoding containing 2 numbers (either public key or ecdsa signature)
void der_read_pair(const uint8_t *der, bignum256 *elem1, bignum256 *elem2)
{
	der_read_single(der + 2, elem1);
	der_read_single(der + 4 + der[3], elem2);
}

// write DER encoding of number to buffer
void der_write(const bignum256 *x, uint8_t *buf)
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

// generate random K for signing
void generate_k_random(bignum256 *k) {
	int i;
	for (;;) {
		for (i = 0; i < 8; i++) {
			k->val[i] = random32() & 0x3FFFFFFF;
		}
		k->val[8] = random32() & 0xFFFF;
		// if k is too big or too small, we don't like it
		if (k->val[5] == 0x3FFFFFFF && k->val[6] == 0x3FFFFFFF && k->val[7] == 0x3FFFFFFF && k->val[8] == 0xFFFF) continue;
		if (k->val[5] == 0x0 && k->val[6] == 0x0 && k->val[7] == 0x0 && k->val[8] == 0x0) continue;
		return;
	}
}

// generate K in a deterministic way, according to RFC6979
// http://tools.ietf.org/html/rfc6979
void generate_k_rfc6979(bignum256 *secret, const uint8_t *priv_key, const uint8_t *hash)
{
	uint8_t v[32], k[32], bx[2*32], buf[32 + 1 + sizeof(bx)], t[32];
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
	hmac_sha256(k, sizeof(k), v, sizeof(k), v);

	for (;;) {
		hmac_sha256(k, sizeof(k), v, sizeof(v), t);
		bn_read_be(t, secret);
		if ( !bn_is_zero(secret) && bn_is_less(secret, &order256k1) ) {
			return;
		}
		memcpy(buf, v, sizeof(v));
		buf[sizeof(v)] = 0x00;
		hmac_sha256(k, sizeof(k), buf, sizeof(v) + 1, k);
		hmac_sha256(k, sizeof(k), v, sizeof(v), v);
	}
}

// uses secp256k1 curve
// priv_key is a 32 byte big endian stored number
// msg is a data to be signed
// msg_len is the message length
// sig is at least 70 bytes long array for the signature
// sig_len is the pointer to a uint that will contain resulting signature length. note that ((*sig_len) == sig[1]+2)
void ecdsa_sign(const uint8_t *priv_key, const uint8_t *msg, uint32_t msg_len, uint8_t *sig, uint32_t *sig_len)
{
	int i;
	uint8_t hash[32];
	curve_point R;
	bignum256 k, z;
	bignum256 *da = &R.y;
	// compute hash function of message
	SHA256_Raw(msg, msg_len, hash);
	// if double hash is required uncomment the following line:
	// SHA256_Raw(hash, 32, hash);

	bn_read_be(hash, &z);
	for (;;) {

		// generate random number k
		//generate_k_random(&k);

		// generate K deterministically
		generate_k_rfc6979(&k, priv_key, hash);

		// compute k*G
		scalar_multiply(&k, &R);
		// r = (rx mod n)
		bn_mod(&R.x, &order256k1);
		// if r is zero, we try different k
		for (i = 0; i < 9; i++) {
			if (R.x.val[i] != 0) break;
		}
		if (i == 9) continue;
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
		for (i = 0; i < 9; i++) {
			if (k.val[i] != 0) break;
		}
		if (i == 9) continue;
		// we are done, R.x and k is the result signature
		break;
	}
	der_write(&R.x, sig + 2);
	i = sig[3] + 2;
	der_write(&k, sig + 2 + i);
	i += sig[3 + i] + 2;
	sig[0] = 0x30;
	sig[1] = i;
	*sig_len = i + 2;
}

// uses secp256k1 curve
// priv_key is a 32 byte big endian stored number
// pub_key is at least 70 bytes long array for the public key
void ecdsa_get_public_key_der(const uint8_t *priv_key, uint8_t *pub_key, uint32_t *pub_key_len)
{
	uint32_t i;
	curve_point R;
	bignum256 k;

	bn_read_be(priv_key, &k);
	// compute k*G
	scalar_multiply(&k, &R);
	der_write(&R.x, pub_key + 2);
	i = pub_key[3] + 2;
	der_write(&R.y, pub_key + 2 + i);
	i += pub_key[3 + i] + 2;
	pub_key[0] = 0x30;
	pub_key[1] = i;
	*pub_key_len = i + 2;
}


// pub_key is always 33 bytes long
void ecdsa_get_public_key_compressed(const uint8_t *priv_key, uint8_t *pub_key)
{
	curve_point R;
	bignum256 k;

	bn_read_be(priv_key, &k);
	// compute k*G
	scalar_multiply(&k, &R);
	pub_key[0] = 0x02 | (R.y.val[0] & 0x01);
	bn_write_be(&R.x, pub_key + 1);
}

void ecdsa_get_address(const uint8_t *pub_key, char version, char *addr)
{
	const char code[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
	char *p = addr, s;
	uint8_t a[32], b[21];
	uint32_t r;
	bignum256 c, q;
	int i, l;

	SHA256_Raw(pub_key, 33, a);
	b[0] = version;
	ripemd160(a, 32, b + 1);

	SHA256_Raw(b, 21, a);
	SHA256_Raw(a, 32, a);

	memcpy(a + 28, a, 4); // checksum
	memset(a, 0, 7);      // zeroes
	memcpy(a + 7, b, 21); // ripemd160(sha256(version + pubkey)

	bn_read_be(a, &c);

	while (!bn_is_zero(&c)) {
		bn_divmod58(&c, &q, &r);
		*p = code[r];
		p++;
		for (i = 0; i < 9; i++) {
			c.val[i] = q.val[i];
		}
	}

	if (a[0] == 0) {
		*p = '1';
		p++;
	}

	*p = 0;

	l = strlen(addr);

	for (i = 0; i < l / 2; i++) {
		s = addr[i];
		addr[i] = addr[l - 1 - i];
		addr[l - 1 - i] = s;;
	}
}

// uses secp256k1 curve
// pub_key and signature are DER encoded
// msg is a data that was signed
// msg_len is the message length
// returns 0 if verification succeeded
// it is assumed that public key is valid otherwise calling this does not make much sense
int ecdsa_verify(const uint8_t *pub_key, const uint8_t *signature, const uint8_t *msg, uint32_t msg_len)
{
	int i, j;
	uint8_t hash[32];
	curve_point pub, res;
	bignum256 r, s, z;
	int res_is_zero = 0;
	// compute hash function of message
	SHA256_Raw(msg, msg_len, hash);
	// if double hash is required uncomment the following line:
	// SHA256_Raw(hash, 32, hash);

	bn_read_be(hash, &z);
	der_read_pair(pub_key, &pub.x, &pub.y);
	der_read_pair(signature, &r, &s);

	if (bn_is_zero(&r) ||
	    bn_is_zero(&s) ||
	    (!bn_is_less(&r, &order256k1)) ||
	    (!bn_is_less(&s, &order256k1))) return 1;

	bn_inverse(&s, &order256k1); // s^-1
	bn_multiply(&s, &z, &order256k1); // z*s^-1
	bn_mod(&z, &order256k1);
	bn_multiply(&r, &s, &order256k1); // r*s^-1
	bn_mod(&s, &order256k1);
	if (bn_is_zero(&z)) {
		// our message hashes to zero
		// I don't expect this to happen any time soon
		res_is_zero = 1;
	} else {
		scalar_multiply(&z, &res);
	}

	// TODO both pub and res can be infinity, can have y = 0 OR can be equal
	for (i = 0; i < 9; i++) {
		for (j = 0; j < 30; j++) {
			if (i == 8 && (s.val[i] >> j) == 0) break;
			if (s.val[i] & (1u << j)) {
				point_add(&pub, &res);
			}
			point_double(&pub);
		}
	}

	bn_mod(&(res.x), &prime256k1);
	bn_mod(&(res.x), &order256k1);
	for (i = 0; i < 9; i++) {
		if (res.x.val[i] != r.val[i]) {
			return 1;
		}
	}
	return 0;
}
