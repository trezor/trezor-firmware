#ifndef __BIP32_H__
#define __BIP32_H__

#include <stdint.h>

typedef struct {
	uint32_t version;
	uint32_t depth;
	uint32_t fingerprint;
	uint32_t child_num;
	uint8_t private_key[32]; // private_key + chain_code have to
	uint8_t chain_code[32];  // form a continuous 64 byte block
	uint8_t public_key[33];
	char address[35];
} HDNode;

void hdnode_from_pub(uint32_t version, uint32_t depth, uint32_t fingerprint, uint32_t child_num, uint8_t *chain_code, uint8_t *public_key, HDNode *out);

void hdnode_from_seed(uint8_t *seed, int seed_len, HDNode *out);

#define hdnode_descent_prime(X, I) hdnode_descent((X), ((I) | 0x80000000))

void hdnode_descent(HDNode *inout, uint32_t i);

void hdnode_fill_public_key(HDNode *xprv);

void hdnode_fill_address(HDNode *xprv, uint8_t version);

#endif
