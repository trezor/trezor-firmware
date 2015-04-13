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

#include "hmac.h"
#include "sha2.h"
#include "macros.h"

void hmac_sha256(const uint8_t *key, const uint32_t keylen, const uint8_t *msg, const uint32_t msglen, uint8_t *hmac)
{
	int i;
	uint8_t buf[SHA256_BLOCK_LENGTH], o_key_pad[SHA256_BLOCK_LENGTH], i_key_pad[SHA256_BLOCK_LENGTH];
	SHA256_CTX ctx;

	memset(buf, 0, SHA256_BLOCK_LENGTH);
	if (keylen > SHA256_BLOCK_LENGTH) {
		sha256_Raw(key, keylen, buf);
	} else {
		memcpy(buf, key, keylen);
	}

	for (i = 0; i < SHA256_BLOCK_LENGTH; i++) {
		o_key_pad[i] = buf[i] ^ 0x5c;
		i_key_pad[i] = buf[i] ^ 0x36;
	}

	sha256_Init(&ctx);
	sha256_Update(&ctx, i_key_pad, SHA256_BLOCK_LENGTH);
	sha256_Update(&ctx, msg, msglen);
	sha256_Final(buf, &ctx);

	sha256_Init(&ctx);
	sha256_Update(&ctx, o_key_pad, SHA256_BLOCK_LENGTH);
	sha256_Update(&ctx, buf, SHA256_DIGEST_LENGTH);
	sha256_Final(hmac, &ctx);
	MEMSET_BZERO(buf, sizeof(buf));
	MEMSET_BZERO(o_key_pad, sizeof(o_key_pad));
	MEMSET_BZERO(i_key_pad, sizeof(i_key_pad));
}

void hmac_sha512(const uint8_t *key, const uint32_t keylen, const uint8_t *msg, const uint32_t msglen, uint8_t *hmac)
{
	int i;
	uint8_t buf[SHA512_BLOCK_LENGTH], o_key_pad[SHA512_BLOCK_LENGTH], i_key_pad[SHA512_BLOCK_LENGTH];
	SHA512_CTX ctx;

	memset(buf, 0, SHA512_BLOCK_LENGTH);
	if (keylen > SHA512_BLOCK_LENGTH) {
		sha512_Raw(key, keylen, buf);
	} else {
		memcpy(buf, key, keylen);
	}

	for (i = 0; i < SHA512_BLOCK_LENGTH; i++) {
		o_key_pad[i] = buf[i] ^ 0x5c;
		i_key_pad[i] = buf[i] ^ 0x36;
	}

	sha512_Init(&ctx);
	sha512_Update(&ctx, i_key_pad, SHA512_BLOCK_LENGTH);
	sha512_Update(&ctx, msg, msglen);
	sha512_Final(buf, &ctx);

	sha512_Init(&ctx);
	sha512_Update(&ctx, o_key_pad, SHA512_BLOCK_LENGTH);
	sha512_Update(&ctx, buf, SHA512_DIGEST_LENGTH);
	sha512_Final(hmac, &ctx);

	MEMSET_BZERO(buf, sizeof(buf));
	MEMSET_BZERO(o_key_pad, sizeof(o_key_pad));
	MEMSET_BZERO(i_key_pad, sizeof(i_key_pad));
}
