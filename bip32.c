#include <string.h>

#include "bignum.h"
#include "hmac.h"
#include "ecdsa.h"
#include "bip32.h"

void hdnode_from_pub(uint32_t version, uint32_t depth, uint32_t fingerprint, uint32_t child_num, uint8_t *chain_code, uint8_t *public_key, HDNode *out)
{
	out->version = version;
	out->depth = depth;
	out->fingerprint = fingerprint;
	out->child_num = child_num;
	memcpy(out->chain_code, chain_code, 32);
	memcpy(out->public_key, public_key, 33);
	memset(out->private_key, 0, 32);
	hdnode_fill_address(out, 0x00);
}

void hdnode_from_seed(uint8_t *seed, int seed_len, HDNode *out)
{
	out->version = 0x0488ADE4; // main-net
	out->depth = 0;
	out->fingerprint = 0x00000000;
	out->child_num = 0;
	// this can be done because private_key[32] and chain_code[32]
	// form a continuous 64 byte block in the memory
	hmac_sha512((uint8_t *)"Bitcoin seed", 12, seed, seed_len, out->private_key);
	hdnode_fill_public_key(out);
	hdnode_fill_address(out, 0x00);
}

void hdnode_descent(HDNode *inout, uint32_t i)
{
	uint8_t data[1 + 32 + 4];
	bignum256 a, b;

	if (i & 0x80000000) { // private derivation
		data[0] = 0;
		memcpy(data + 1, inout->private_key, 32);
	} else { // public derivation
		memcpy(data, inout->public_key, 33);
	}
	write_be(data + 33, i);

	bn_read_be(inout->private_key, &a);

	// this can be done because private_key[32] and chain_code[32]
	// form a continuous 64 byte block in the memory
	hmac_sha512(inout->chain_code, 32, data, sizeof(data), inout->private_key);

	bn_read_be(inout->private_key, &b);
	bn_addmod(&a, &b, &order256k1);

	inout->depth++;
	inout->child_num = i;
	bn_write_be(&a, inout->private_key);

	hdnode_fill_public_key(inout);
	hdnode_fill_address(inout, 0x00);
}

void hdnode_fill_public_key(HDNode *xprv)
{
	ecdsa_get_public_key33(xprv->private_key, xprv->public_key);
}

void hdnode_fill_address(HDNode *xprv, uint8_t version)
{
	ecdsa_get_address(xprv->public_key, version, xprv->address);
}
