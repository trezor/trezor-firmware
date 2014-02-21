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
	bn_mod(&(res->x), &prime256k1);
	bn_mod(&(res->y), &prime256k1);
}

// res = k * G
void scalar_multiply(const bignum256 *k, curve_point *res)
{
	int i, j;
	// result is zero
	int is_zero = 1;
#if USE_PRECOMPUTED_CP
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
#if USE_PRECOMPUTED_CP
					memcpy(res, secp256k1_cp + exp, sizeof(curve_point));
#else
					memcpy(res, &curr, sizeof(curve_point));
#endif
					is_zero = 0;
				} else {
#if USE_PRECOMPUTED_CP
					point_add(secp256k1_cp + exp, res);
#else
					point_add(&curr, res);
#endif
				}
			}
#if USE_PRECOMPUTED_CP
			exp++;
#else
			point_double(&curr);
#endif
		}
	}
	bn_mod(&(res->x), &prime256k1);
	bn_mod(&(res->y), &prime256k1);
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
	for (i = 0; i < 9; i++) {
		if (R.x.val[i] != 0) break;
	}
	if (i == 9) {
		return 2;
	}
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
	// if k is zero, we fail
	if (i == 9) {
		return 3;
	}

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
	if (pub_key[0] == 0x04) {
		sha256_Raw(pub_key, 65, h);
	} else {
		sha256_Raw(pub_key, 33, h);
	}
	ripemd160(h, 32, pubkeyhash);
}

void ecdsa_get_address(const uint8_t *pub_key, uint8_t version, char *addr)
{
	const char code[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
	char *p = addr, s;
	uint8_t a[32], b[21];
	uint32_t r;
	bignum256 c;
	int i, l;

	b[0] = version;
	ecdsa_get_pubkeyhash(pub_key, b + 1);

	sha256_Raw(b, 21, a);
	sha256_Raw(a, 32, a);

	memcpy(a + 28, a, 4); // checksum
	memset(a, 0, 7);      // zeroes
	memcpy(a + 7, b, 21); // ripemd160(sha256(version + pubkey)

	bn_read_be(a, &c);

	while (!bn_is_zero(&c)) {
		bn_divmod58(&c, &r);
		*p = code[r];
		p++;
	}

	i = 7;
	while (a[i] == 0) {
		*p = code[0];
		p++; i++;
	}

	*p = 0;

	l = strlen(addr);

	for (i = 0; i < l / 2; i++) {
		s = addr[i];
		addr[i] = addr[l - 1 - i];
		addr[l - 1 - i] = s;
	}
}

int ecdsa_address_decode(const char *addr, uint8_t *out)
{
	if (!addr) return 0;
	const char code[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
	bignum256 num;
	uint8_t buf[32], check[32];
	bn_zero(&num);
	uint32_t k;
	size_t i;
	for (i = 0; i < strlen(addr); i++) {
		bn_muli(&num, 58);
		for (k = 0; k <= strlen(code); k++) {
			if (code[k] == 0) { // char not found -> invalid address
				return 0;
			}
			if (addr[i] == code[k]) {
				bn_addi(&num, k);
				break;
			}
		}
	}
	bn_write_be(&num, buf);
	// compute address hash
	sha256_Raw(buf + 7, 21, check);
	sha256_Raw(check, 32, check);
	// check if valid
	if (memcmp(buf + 7 + 21, check, 4) != 0) {
		return 0;
	}
	memcpy(out, buf + 7, 21);
	return 1;
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
		return 1;
	}
	if (pub_key[0] == 0x02 || pub_key[0] == 0x03) { // compute missing y coords
		bn_read_be(pub_key + 1, &(pub->x));
		uncompress_coords(pub_key[0], &(pub->x), &(pub->y));
		return 1;
	}
	// error
	return 0;
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
// it is assumed that public key is valid otherwise calling this does not make much sense
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
				bn_mod(&(pub.y), &prime256k1);
				bn_mod(&(res.y), &prime256k1);
				if (bn_is_equal(&(pub.y), &(res.y))) {
					// this is not a failure, but a very inprobable case
					// that we don't handle because of its inprobability
					return 4;
				}
				point_add(&pub, &res);
			}
			point_double(&pub);
		}
	}

	bn_mod(&(res.x), &prime256k1);
	bn_mod(&(res.x), &order256k1);

	// signature does not match
	for (i = 0; i < 9; i++) {
		if (res.x.val[i] != r.val[i]) {
			return 5;
		}
	}

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
