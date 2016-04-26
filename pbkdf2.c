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
#include "pbkdf2.h"
#include "hmac.h"
#include "macros.h"

void pbkdf2_hmac_sha256(const uint8_t *pass, int passlen, uint8_t *salt, int saltlen, uint32_t iterations, uint8_t *key, int keylen, void (*progress_callback)(uint32_t current, uint32_t total))
{
	const uint32_t HMACLEN = 256/8;
	uint8_t f[HMACLEN], g[HMACLEN];
	uint32_t blocks = keylen / HMACLEN;
	if (keylen & (HMACLEN - 1)) {
		blocks++;
	}
	for (uint32_t i = 1; i <= blocks; i++) {
		HMAC_SHA256_CTX hctx;
		hmac_sha256_Init(&hctx, pass, passlen);
		hmac_sha256_Update(&hctx, salt, saltlen);
		uint32_t ii = ((i & 0xFF000000) >> 24) | ((i & 0x00FF0000) >> 8) | ((i & 0x0000FF00) << 8) | ((i & 0x000000FF) << 24);
		hmac_sha256_Update(&hctx, (const uint8_t *)&ii, sizeof(uint32_t));
		hmac_sha256_Final(&hctx, g);
		memcpy(f, g, HMACLEN);
		if (progress_callback) {
			progress_callback(0, iterations);
		}
		for (uint32_t j = 1; j < iterations; j++) {
			hmac_sha256(pass, passlen, g, HMACLEN, g);
			for (uint32_t k = 0; k < HMACLEN; k++) {
				f[k] ^= g[k];
			}
			if (progress_callback && (j % 256 == 255)) {
				progress_callback(j + 1, iterations);
			}
		}
		if (i == blocks && (keylen & (HMACLEN - 1))) {
			memcpy(key + HMACLEN * (i - 1), f, keylen & (HMACLEN - 1));
		} else {
			memcpy(key + HMACLEN * (i - 1), f, HMACLEN);
		}
	}
	MEMSET_BZERO(f, sizeof(f));
	MEMSET_BZERO(g, sizeof(g));
}

void pbkdf2_hmac_sha512(const uint8_t *pass, int passlen, uint8_t *salt, int saltlen, uint32_t iterations, uint8_t *key, int keylen, void (*progress_callback)(uint32_t current, uint32_t total))
{
	const uint32_t HMACLEN = 512/8;
	uint8_t f[HMACLEN], g[HMACLEN];
	uint32_t blocks = keylen / HMACLEN;
	if (keylen & (HMACLEN - 1)) {
		blocks++;
	}
	for (uint32_t i = 1; i <= blocks; i++) {
		HMAC_SHA512_CTX hctx;
		hmac_sha512_Init(&hctx, pass, passlen);
		hmac_sha512_Update(&hctx, salt, saltlen);
		uint32_t ii = ((i & 0xFF000000) >> 24) | ((i & 0x00FF0000) >> 8) | ((i & 0x0000FF00) << 8) | ((i & 0x000000FF) << 24);
		hmac_sha512_Update(&hctx, (const uint8_t *)&ii, sizeof(uint32_t));
		hmac_sha512_Final(&hctx, g);
		memcpy(f, g, HMACLEN);
		if (progress_callback) {
			progress_callback(0, iterations);
		}
		for (uint32_t j = 1; j < iterations; j++) {
			hmac_sha512(pass, passlen, g, HMACLEN, g);
			for (uint32_t k = 0; k < HMACLEN; k++) {
				f[k] ^= g[k];
			}
			if (progress_callback && (j % 256 == 255)) {
				progress_callback(j + 1, iterations);
			}
		}
		if (i == blocks && (keylen & (HMACLEN - 1))) {
			memcpy(key + HMACLEN * (i - 1), f, keylen & (HMACLEN - 1));
		} else {
			memcpy(key + HMACLEN * (i - 1), f, HMACLEN);
		}
	}
	MEMSET_BZERO(f, sizeof(f));
	MEMSET_BZERO(g, sizeof(g));
}
