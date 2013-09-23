#include <string.h>

#include "bignum.h"
#include "hmac.h"
#include "ecdsa.h"
#include "bip32.h"

void xprv_from_seed(uint8_t *seed, int seed_len, xprv *out)
{
	out->version = 0x0488ADE4; // main-net
	out->depth = 0;
	out->fingerprint = 0x00000000;
	out->child_num = 0;
	// this can be done because private_key[32] and chain_code[32]
	// form a continuous 64 byte block in the memory
	hmac_sha512((uint8_t *)"Bitcoin seed", 12, seed, seed_len, out->private_key);
	ecdsa_get_public_key33(out->private_key, out->public_key);
	ecdsa_get_address(out->public_key, 0, out->address);
}

void xprv_descent(xprv *inout, uint32_t i)
{
	uint8_t data[1 + 32 + 4];
	bignum256 a, b;

	if (i & 0x80000000) {
		data[0] = 0;
		memcpy(data + 1, inout->private_key, 32);
	} else {
		ecdsa_get_public_key33(inout->private_key, data);
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

	ecdsa_get_public_key33(inout->private_key, inout->public_key);
	ecdsa_get_address(inout->public_key, 0, inout->address);
}
