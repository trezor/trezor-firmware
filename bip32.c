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

#include <string.h>
#include <stdbool.h>

#include "bignum.h"
#include "hmac.h"
#include "ecdsa.h"
#include "bip32.h"
#include "sha2.h"
#include "ripemd160.h"
#include "base58.h"
#include "macros.h"
#include "secp256k1.h"

static const ecdsa_curve *default_curve = &secp256k1;

int hdnode_from_xpub(uint32_t depth, uint32_t fingerprint, uint32_t child_num, const uint8_t *chain_code, const uint8_t *public_key, HDNode *out)
{
	if (public_key[0] != 0x02 && public_key[0] != 0x03) { // invalid pubkey
		return 0;
	}
	out->depth = depth;
	out->fingerprint = fingerprint;
	out->child_num = child_num;
	memcpy(out->chain_code, chain_code, 32);
	MEMSET_BZERO(out->private_key, 32);
	memcpy(out->public_key, public_key, 33);
	return 1;
}

int hdnode_from_xprv(uint32_t depth, uint32_t fingerprint, uint32_t child_num, const uint8_t *chain_code, const uint8_t *private_key, HDNode *out)
{
	bignum256 a;
	bn_read_be(private_key, &a);

	bool failed = false;
	if (bn_is_zero(&a)) { // == 0
		failed = true;
	} else {
		if (!bn_is_less(&a, &default_curve->order)) { // >= order
			failed = true;
		}
		MEMSET_BZERO(&a, sizeof(a));
	}

	if (failed) {
		return 0;
	}

	out->depth = depth;
	out->fingerprint = fingerprint;
	out->child_num = child_num;
	memcpy(out->chain_code, chain_code, 32);
	memcpy(out->private_key, private_key, 32);
	hdnode_fill_public_key(out);
	return 1;
}

int hdnode_from_seed(const uint8_t *seed, int seed_len, HDNode *out)
{
	uint8_t I[32 + 32];
	memset(out, 0, sizeof(HDNode));
	out->depth = 0;
	out->fingerprint = 0x00000000;
	out->child_num = 0;
	hmac_sha512((uint8_t *)"Bitcoin seed", 12, seed, seed_len, I);
	memcpy(out->private_key, I, 32);
	bignum256 a;
	bn_read_be(out->private_key, &a);

	bool failed = false;
	if (bn_is_zero(&a)) { // == 0
		failed = true;
	} else {
		if (!bn_is_less(&a, &default_curve->order)) { // >= order
			failed = true;
		}
		MEMSET_BZERO(&a, sizeof(a));
	}

	if (!failed) {
		memcpy(out->chain_code, I + 32, 32);
		hdnode_fill_public_key(out);
	}

	MEMSET_BZERO(I, sizeof(I));
	return failed ? 0 : 1;
}

int hdnode_private_ckd(HDNode *inout, uint32_t i)
{
	uint8_t data[1 + 32 + 4];
	uint8_t I[32 + 32];
	uint8_t fingerprint[32];
	bignum256 a, b;

	if (i & 0x80000000) { // private derivation
		data[0] = 0;
		memcpy(data + 1, inout->private_key, 32);
	} else { // public derivation
		memcpy(data, inout->public_key, 33);
	}
	write_be(data + 33, i);

	sha256_Raw(inout->public_key, 33, fingerprint);
	ripemd160(fingerprint, 32, fingerprint);
	inout->fingerprint = (fingerprint[0] << 24) + (fingerprint[1] << 16) + (fingerprint[2] << 8) + fingerprint[3];

	bn_read_be(inout->private_key, &a);

	hmac_sha512(inout->chain_code, 32, data, sizeof(data), I);
	memcpy(inout->chain_code, I + 32, 32);
	memcpy(inout->private_key, I, 32);

	bn_read_be(inout->private_key, &b);

	bool failed = false;

	if (!bn_is_less(&b, &default_curve->order)) { // >= order
		failed = true;
	}
	if (!failed) {
		bn_addmod(&a, &b, &default_curve->order);
		if (bn_is_zero(&a)) {
			failed = true;
		}
	}
	if (!failed) {
		inout->depth++;
		inout->child_num = i;
		bn_write_be(&a, inout->private_key);
		hdnode_fill_public_key(inout);
	}

	// making sure to wipe our memory
	MEMSET_BZERO(&a, sizeof(a));
	MEMSET_BZERO(&b, sizeof(b));
	MEMSET_BZERO(I, sizeof(I));
	MEMSET_BZERO(fingerprint, sizeof(fingerprint));
	MEMSET_BZERO(data, sizeof(data));
	return failed ? 0 : 1;
}

int hdnode_public_ckd(HDNode *inout, uint32_t i)
{
	uint8_t data[1 + 32 + 4];
	uint8_t I[32 + 32];
	uint8_t fingerprint[32];
	curve_point a, b;
	bignum256 c;

	if (i & 0x80000000) { // private derivation
		return 0;
	} else { // public derivation
		memcpy(data, inout->public_key, 33);
	}
	write_be(data + 33, i);

	sha256_Raw(inout->public_key, 33, fingerprint);
	ripemd160(fingerprint, 32, fingerprint);
	inout->fingerprint = (fingerprint[0] << 24) + (fingerprint[1] << 16) + (fingerprint[2] << 8) + fingerprint[3];

	memset(inout->private_key, 0, 32);

	bool failed = false;
	if (!ecdsa_read_pubkey(default_curve, inout->public_key, &a)) {
		failed = true;
	}

	if (!failed) {
		hmac_sha512(inout->chain_code, 32, data, sizeof(data), I);
		memcpy(inout->chain_code, I + 32, 32);
		bn_read_be(I, &c);
		if (!bn_is_less(&c, &default_curve->order)) { // >= order
			failed = true;
		}
	}

	if (!failed) {
		scalar_multiply(default_curve, &c, &b); // b = c * G
		point_add(default_curve, &a, &b);       // b = a + b
		if (!ecdsa_validate_pubkey(default_curve, &b)) {
			failed = true;
		}
	}

	if (!failed) {
		inout->public_key[0] = 0x02 | (b.y.val[0] & 0x01);
		bn_write_be(&b.x, inout->public_key + 1);
		inout->depth++;
		inout->child_num = i;
	}

	// Wipe all stack data.
	MEMSET_BZERO(data, sizeof(data));
	MEMSET_BZERO(I, sizeof(I));
	MEMSET_BZERO(fingerprint, sizeof(fingerprint));
	MEMSET_BZERO(&a, sizeof(a));
	MEMSET_BZERO(&b, sizeof(b));
	MEMSET_BZERO(&c, sizeof(c));

	return failed ? 0 : 1;
}

#if USE_BIP32_CACHE

static bool private_ckd_cache_root_set = false;
static HDNode private_ckd_cache_root;
static int private_ckd_cache_index = 0;

static struct {
	bool set;
	size_t depth;
	uint32_t i[BIP32_CACHE_MAXDEPTH];
	HDNode node;
} private_ckd_cache[BIP32_CACHE_SIZE];

int hdnode_private_ckd_cached(HDNode *inout, const uint32_t *i, size_t i_count)
{
	if (i_count == 0) {
		return 1;
	}
	if (i_count == 1) {
		if (hdnode_private_ckd(inout, i[0]) == 0) return 0;
		return 1;
	}

	bool found = false;
	// if root is not set or not the same
	if (!private_ckd_cache_root_set || memcmp(&private_ckd_cache_root, inout, sizeof(HDNode)) != 0) {
		// clear the cache
		private_ckd_cache_index = 0;
		memset(private_ckd_cache, 0, sizeof(private_ckd_cache));
		// setup new root
		memcpy(&private_ckd_cache_root, inout, sizeof(HDNode));
		private_ckd_cache_root_set = true;
	} else {
		// try to find parent
		int j;
		for (j = 0; j < BIP32_CACHE_SIZE; j++) {
			if (private_ckd_cache[j].set &&
			    private_ckd_cache[j].depth == i_count - 1 &&
			    memcmp(private_ckd_cache[j].i, i, (i_count - 1) * sizeof(uint32_t)) == 0) {
				memcpy(inout, &(private_ckd_cache[j].node), sizeof(HDNode));
				found = true;
				break;
			}
		}
	}

	// else derive parent
	if (!found) {
		size_t k;
		for (k = 0; k < i_count - 1; k++) {
			if (hdnode_private_ckd(inout, i[k]) == 0) return 0;
		}
		// and save it
		memset(&(private_ckd_cache[private_ckd_cache_index]), 0, sizeof(private_ckd_cache[private_ckd_cache_index]));
		private_ckd_cache[private_ckd_cache_index].set = true;
		private_ckd_cache[private_ckd_cache_index].depth = i_count - 1;
		memcpy(private_ckd_cache[private_ckd_cache_index].i, i, (i_count - 1) * sizeof(uint32_t));
		memcpy(&(private_ckd_cache[private_ckd_cache_index].node), inout, sizeof(HDNode));
		private_ckd_cache_index = (private_ckd_cache_index + 1) % BIP32_CACHE_SIZE;
	}

	if (hdnode_private_ckd(inout, i[i_count - 1]) == 0) return 0;

	return 1;
}

#endif

void hdnode_fill_public_key(HDNode *node)
{
	ecdsa_get_public_key33(default_curve, node->private_key, node->public_key);
}

void hdnode_serialize(const HDNode *node, uint32_t version, char use_public, char *str, int strsize)
{
	uint8_t node_data[78];
	write_be(node_data, version);
	node_data[4] = node->depth;
	write_be(node_data + 5, node->fingerprint);
	write_be(node_data + 9, node->child_num);
	memcpy(node_data + 13, node->chain_code, 32);
	if (use_public) {
		memcpy(node_data + 45, node->public_key, 33);
	} else {
		node_data[45] = 0;
		memcpy(node_data + 46, node->private_key, 32);
	}
	base58_encode_check(node_data, sizeof(node_data), str, strsize);

	MEMSET_BZERO(node_data, sizeof(node_data));
}

void hdnode_serialize_public(const HDNode *node, char *str, int strsize)
{
	hdnode_serialize(node, 0x0488B21E, 1, str, strsize);
}

void hdnode_serialize_private(const HDNode *node, char *str, int strsize)
{
	hdnode_serialize(node, 0x0488ADE4, 0, str, strsize);
}

// check for validity of curve point in case of public data not performed
int hdnode_deserialize(const char *str, HDNode *node)
{
	uint8_t node_data[78];
	memset(node, 0, sizeof(HDNode));
	if (!base58_decode_check(str, node_data, sizeof(node_data))) {
		return -1;
	}
	uint32_t version = read_be(node_data);
	if (version == 0x0488B21E) { // public node
		memcpy(node->public_key, node_data + 45, 33);
	} else if (version == 0x0488ADE4) { // private node
		if (node_data[45]) { // invalid data
			return -2;
		}
		memcpy(node->private_key, node_data + 46, 32);
		hdnode_fill_public_key(node);
	} else {
		return -3; // invalid version
	}
	node->depth = node_data[4];
	node->fingerprint = read_be(node_data + 5);
	node->child_num = read_be(node_data + 9);
	memcpy(node->chain_code, node_data + 13, 32);
	return 0;
}
