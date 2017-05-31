/**
 * Copyright (c) 2017 Saleem Rashid
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
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, E1PRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include "nem.h"

#include <stddef.h>
#include <string.h>

#include "base32.h"
#include "macros.h"
#include "ripemd160.h"
#include "sha3.h"

const char *nem_network_name(uint8_t network) {
	switch (network) {
	case NEM_NETWORK_MAINNET:
		return "NEM Mainnet";
	case NEM_NETWORK_TESTNET:
		return "NEM Testnet";
	case NEM_NETWORK_MIJIN:
		return "Mijin";
	default:
		return NULL;
	}
}

void nem_get_address_raw(const ed25519_public_key public_key, uint8_t version, uint8_t *address) {
	uint8_t hash[SHA3_256_DIGEST_LENGTH];

	/* 1.  Perform 256-bit Sha3 on the public key */
	keccak_256(public_key, sizeof(ed25519_public_key), hash);

	/* 2.  Perform 160-bit Ripemd of hash resulting from step 1. */
	ripemd160(hash, SHA3_256_DIGEST_LENGTH, &address[1]);

	/* 3.  Prepend version byte to Ripemd hash (either 0x68 or 0x98) */
	address[0] = version;

	/* 4.  Perform 256-bit Sha3 on the result, take the first four bytes as a checksum */
	keccak_256(address, 1 + RIPEMD160_DIGEST_LENGTH, hash);

	/* 5.  Concatenate output of step 3 and the checksum from step 4 */
	memcpy(&address[1 + RIPEMD160_DIGEST_LENGTH], hash, 4);

	MEMSET_BZERO(hash, sizeof(hash));
}

bool nem_get_address(const ed25519_public_key public_key, uint8_t version, char *address) {
	uint8_t pubkeyhash[NEM_ADDRESS_SIZE_RAW];

	nem_get_address_raw(public_key, version, pubkeyhash);

	char *ret = base32_encode(pubkeyhash, sizeof(pubkeyhash), address, NEM_ADDRESS_SIZE + 1, BASE32_ALPHABET_RFC4648);

	MEMSET_BZERO(pubkeyhash, sizeof(pubkeyhash));

	return (ret != NULL);
}
