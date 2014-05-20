#include <string.h>

#include "bignum.h"
#include "hmac.h"
#include "ecdsa.h"
#include "bip32.h"
#include "sha2.h"
#include "ripemd160.h"

void hdnode_from_xpub(uint32_t depth, uint32_t fingerprint, uint32_t child_num, uint8_t *chain_code, uint8_t *public_key, HDNode *out)
{
	out->depth = depth;
	out->fingerprint = fingerprint;
	out->child_num = child_num;
	memcpy(out->chain_code, chain_code, 32);
	memset(out->private_key, 0, 32);
	memcpy(out->public_key, public_key, 33);
}

void hdnode_from_xprv(uint32_t depth, uint32_t fingerprint, uint32_t child_num, uint8_t *chain_code, uint8_t *private_key, HDNode *out)
{
	out->depth = depth;
	out->fingerprint = fingerprint;
	out->child_num = child_num;
	memcpy(out->chain_code, chain_code, 32);
	memcpy(out->private_key, private_key, 32);
	hdnode_fill_public_key(out);
}

void hdnode_from_seed(uint8_t *seed, int seed_len, HDNode *out)
{
	uint8_t I[32 + 32];
	memset(out, 0, sizeof(HDNode));
	out->depth = 0;
	out->fingerprint = 0x00000000;
	out->child_num = 0;
	hmac_sha512((uint8_t *)"Bitcoin seed", 12, seed, seed_len, I);
	memcpy(out->chain_code, I + 32, 32);
	memcpy(out->private_key, I, 32);
	hdnode_fill_public_key(out);
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
	bn_addmod(&a, &b, &order256k1);

	inout->depth++;
	inout->child_num = i;
	bn_write_be(&a, inout->private_key);

	hdnode_fill_public_key(inout);

	return 1;
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
	if (!ecdsa_read_pubkey(inout->public_key, &a)) {
		return 0;
	}

	hmac_sha512(inout->chain_code, 32, data, sizeof(data), I);
	memcpy(inout->chain_code, I + 32, 32);
	bn_read_be(I, &c);
	scalar_multiply(&c, &b); // b = c * G
	point_add(&a, &b);       // b = a + b
	inout->public_key[0] = 0x02 | (b.y.val[0] & 0x01);
	bn_write_be(&b.x, inout->public_key + 1);

	inout->depth++;
	inout->child_num = i;

	return 1;
}

void hdnode_fill_public_key(HDNode *node)
{
	ecdsa_get_public_key33(node->private_key, node->public_key);
}

void hdnode_serialize(const HDNode *node, uint32_t version, char use_public, char *str)
{
	uint8_t node_data[82], a[32];
	int i,j;
	uint32_t rem, tmp;
	const char code[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
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
	sha256_Raw(node_data, 78, a);
	sha256_Raw(a, 32, a);
	memcpy(node_data + 78, a, 4); // checksum
	for (j = 110; j >= 0; j--) {
		rem = node_data[0] % 58;
		node_data[0] /= 58;
		for (i = 1; i < 82; i++) {
			tmp = rem * 24 + node_data[i]; // 2^8 == 4*58 + 24
			node_data[i] = rem * 4 + (tmp / 58);
			rem = tmp % 58;
		}
		str[j] = code[rem];
	}
	str[111] = 0;
}

void hdnode_serialize_public(const HDNode *node, char *str)
{
	hdnode_serialize(node, 0x0488B21E, 1, str);
}

void hdnode_serialize_private(const HDNode *node, char *str)
{
	hdnode_serialize(node, 0x0488ADE4, 0, str);
}

// check for validity of curve point in case of public data not performed
int hdnode_deserialize(const char *str, HDNode *node)
{
	uint8_t node_data[82], a[32];
	const char decode[] = {
		-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
		-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
		-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
		-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, 1, 2, 3,
		4, 5, 6, 7, 8, -1, -1, -1, -1, -1, -1, -1, 9, 10, 11,
		12, 13, 14, 15, 16, -1, 17, 18, 19, 20, 21, -1, 22,
		23, 24, 25, 26, 27, 28, 29, 30, 31, 32, -1, -1, -1,
		-1, -1, -1, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
		43, -1, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54,
		55, 56, 57
	};
	memset(node, 0, sizeof(HDNode));
	memset(node_data, 0, sizeof(node_data));
	if (strlen(str) != 111) { // invalid data length
		return -1;
	}
	int i, j, k;
	for (i = 0; i < 111; i++) {
		if (str[i] < 0 || str[i] >= (int)sizeof(decode)) { // invalid character
			return -2;
		}
		k = decode[(int)str[i]];
		if (k == -1) { // invalid character
			return -2;
		}
		for (j = 81; j >= 0; j--) {
			k += node_data[j] * 58;
			node_data[j] = k & 0xFF;
			k >>= 8;
		}
	}
	sha256_Raw(node_data, 78, a);
	sha256_Raw(a, 32, a);
	if (memcmp(node_data + 78, a, 4)) { // wrong checksum
		 return -3;
	}
	uint32_t version = read_be(node_data);
	if (version == 0x0488B21E) { // public node
		memcpy(node->public_key, node_data + 45, 33);
	} else if (version == 0x0488ADE4) { // private node
		if (node_data[45]) { // invalid data
			return -4;
		}
		memcpy(node->private_key, node_data + 46, 32);
		hdnode_fill_public_key(node);
	} else {
		return -5; // invalid version
	}
	node->depth = node_data[4];
	node->fingerprint = read_be(node_data + 5);
	node->child_num = read_be(node_data + 9);
	memcpy(node->chain_code, node_data + 13, 32);
	return 0;
}
