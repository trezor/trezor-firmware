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
} xprv;

void xprv_from_seed(uint8_t *seed, int seed_len, xprv *out);

#define xprv_descent_prime(X, I) xprv_descent((X), ((I) | 0x80000000))

void xprv_descent(xprv *inout, uint32_t i);

#endif
