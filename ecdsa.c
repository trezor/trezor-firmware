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
	memcpy(&(cp2->x),  &(cp1->x), sizeof(bignum256));
	memcpy(&(cp2->y),  &(cp1->y), sizeof(bignum256));
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
	bn_mod(&(cp2->x), &prime256k1);
	bn_mod(&(cp2->y), &prime256k1);
}

// cp = cp + cp
void point_double(curve_point *cp)
{
	int i;
	uint32_t temp;
	bignum256 lambda, inverse_y, xr, yr;

	if (point_is_infinity(cp)) {
		return;
	}
	if (bn_is_zero(&(cp->y))) {
		point_set_infinity(cp);
		return;
	}

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
	bn_mod(&(cp->x), &prime256k1);
	bn_mod(&(cp->y), &prime256k1);
}

// res = k * p
void point_multiply(const bignum256 *k, const curve_point *p, curve_point *res)
{
	int i, j;
	// result is zero
	int is_zero = 1;
	curve_point curr;
	// initial res
	memcpy(&curr, p, sizeof(curve_point));
	for (i = 0; i < 9; i++) {
		for (j = 0; j < 30; j++) {
			if (i == 8 && (k->val[i] >> j) == 0) break;
			if (k->val[i] & (1u << j)) {
				if (is_zero) {
					memcpy(res, &curr, sizeof(curve_point));
					is_zero = 0;
				} else {
					point_add(&curr, res);
				}
			}
			point_double(&curr);
		}
	}
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

// res = k * G
void scalar_multiply(const bignum256 *k, curve_point *res)
{
	int i;
	// result is zero
	int is_zero = 1;
	curve_point curr;
	// initial res
	memcpy(&curr, &G256k1, sizeof(curve_point));
	for (i = 0; i < 256; i++) {
		if (k->val[i / 30] & (1u << (i % 30))) {
			if (is_zero) {
#if USE_PRECOMPUTED_CP
				if (i < 255 && (k->val[(i + 1) / 30] & (1u << ((i + 1) % 30)))) {
					memcpy(res, secp256k1_cp2 + i, sizeof(curve_point));
					i++;
				} else {
					memcpy(res, secp256k1_cp + i, sizeof(curve_point));
				}
#else
				memcpy(res, &curr, sizeof(curve_point));
#endif
				is_zero = 0;
			} else {
#if USE_PRECOMPUTED_CP
				if (i < 255 && (k->val[(i + 1) / 30] & (1u << ((i + 1) % 30)))) {
					point_add(secp256k1_cp2 + i, res);
					i++;
				} else {
					point_add(secp256k1_cp + i, res);
				}
#else
				point_add(&curr, res);
#endif
			}
		}
#if ! USE_PRECOMPUTED_CP
		point_double(&curr);
#endif
	}
}

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

	for (i = 0; i < 10000; i++) {
		hmac_sha256(k, sizeof(k), v, sizeof(v), t);
		bn_read_be(t, secret);
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
int ecdsa_sign(const uint8_t *priv_key, const uint8_t *msg, uint32_t msg_len, uint8_t *sig)
{
	uint8_t hash[32];
	sha256_Raw(msg, msg_len, hash);
	return ecdsa_sign_digest(priv_key, hash, sig);
}

// msg is a data to be signed
// msg_len is the message length
int ecdsa_sign_double(const uint8_t *priv_key, const uint8_t *msg, uint32_t msg_len, uint8_t *sig)
{
	uint8_t hash[32];
	sha256_Raw(msg, msg_len, hash);
	sha256_Raw(hash, 32, hash);
	return ecdsa_sign_digest(priv_key, hash, sig);
}

// uses secp256k1 curve
// priv_key is a 32 byte big endian stored number
// sig is 64 bytes long array for the signature
// digest is 32 bytes of digest
int ecdsa_sign_digest(const uint8_t *priv_key, const uint8_t *digest, uint8_t *sig)
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
		bn_substract_noprime(&order256k1, &k, &k);
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

void ecdsa_get_address(const uint8_t *pub_key, uint8_t version, char *addr)
{
	uint8_t raw[21];
	ecdsa_get_address_raw(pub_key, version, raw);
	base58_encode_check(raw, 21, addr);
}

void ecdsa_get_wif(const uint8_t *priv_key, uint8_t version, char *wif)
{
	uint8_t data[34];
	data[0] = version;
	memcpy(data + 1, priv_key, 32);
	data[33 ] = 0x01;
	base58_encode_check(data, 34, wif);
}

int ecdsa_address_decode(const char *addr, uint8_t *out)
{
	if (!addr) return 0;
	return base58_decode_check(addr, out) == 21;
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
		bn_substract_noprime(&prime256k1, y, y);   // y = -y
	}
}

int ecdsa_read_pubkey(const uint8_t *pub_key, curve_point *pub)
{
	if (pub_key[0] == 0x04) {
		bn_read_be(pub_key + 1, &(pub->x));
		bn_read_be(pub_key + 33, &(pub->y));
#if USE_PUBKEY_VALIDATE
		return ecdsa_validate_pubkey(pub);
#else
		return 1;
#endif
	}
	if (pub_key[0] == 0x02 || pub_key[0] == 0x03) { // compute missing y coords
		bn_read_be(pub_key + 1, &(pub->x));
		uncompress_coords(pub_key[0], &(pub->x), &(pub->y));
#if USE_PUBKEY_VALIDATE
		return ecdsa_validate_pubkey(pub);
#else
		return 1;
#endif
	}
	// error
	return 0;
}

// Verifies that:
//   - pub is not the point at infinity.
//   - pub->x and pub->y are in range [0,p-1].
//   - pub is on the curve.
//   - n*pub is the point at infinity.

int ecdsa_validate_pubkey(const curve_point *pub)
{
	bignum256 y_2, x_3_b;
	curve_point temp;

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

	point_multiply(&order256k1, pub, &temp);

	if (!point_is_infinity(&temp)) {
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
	int i, j;
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
	for (i = 0; i < 9; i++) {
		for (j = 0; j < 30; j++) {
			if (i == 8 && (s.val[i] >> j) == 0) break;
			if (s.val[i] & (1u << j)) {
				point_add(&pub, &res);
			}
			point_double(&pub);
		}
	}

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
