/**
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

#include <stdio.h>
#include "ecdsa.h"
#include "sha2.h"

bignum256 k;
uint8_t kb[32];
uint8_t priv[32] = {0xcc, 0xa9, 0xfb, 0xcc, 0x1b, 0x41, 0xe5, 0xa9, 0x5d, 0x36, 0x9e, 0xaa, 0x6d, 0xdc, 0xff, 0x73, 0xb6, 0x1a, 0x4e, 0xfa, 0xa2, 0x79, 0xcf, 0xc6, 0x56, 0x7e, 0x8d, 0xaa, 0x39, 0xcb, 0xaf, 0x50};
uint8_t hash[32];

void write_32byte_big_endian(const bignum256 *in_number, uint8_t *out_number);
void generate_k_rfc6979(bignum256 *k, const uint8_t *priv_key, const uint8_t *hash);

int main()
{
	int i;

	SHA256_Raw((uint8_t *)"sample", 6, hash);
	printf("hash     : ");
	for (i = 0; i < 32; i++) printf("%02x", hash[i]); printf("\n");
	generate_k_rfc6979(&k, priv, hash);
	write_32byte_big_endian(&k, kb);

	printf("expected : 2df40ca70e639d89528a6b670d9d48d9165fdc0febc0974056bdce192b8e16a3\n");
	printf("got      : ");
	for (i = 0; i < 32; i++) printf("%02x", kb[i]);
	printf("\n");

	return 0;
}
