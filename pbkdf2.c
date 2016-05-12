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

void pbkdf2_hmac_sha256_Init(PBKDF2_HMAC_SHA256_CTX *pctx, const uint8_t *pass, int passlen, const uint8_t *salt, int saltlen)
{
	HMAC_SHA256_CTX hctx;
	hmac_sha256_Init(&hctx, pass, passlen);
	hmac_sha256_Update(&hctx, salt, saltlen);
	hmac_sha256_Update(&hctx, (const uint8_t *)"\x00\x00\x00\x01", 4);
	hmac_sha256_Final(&hctx, pctx->g);
	memcpy(pctx->f, pctx->g, SHA256_DIGEST_LENGTH);
	pctx->pass = pass;
	pctx->passlen = passlen;
	pctx->first = 1;
}

void pbkdf2_hmac_sha256_Update(PBKDF2_HMAC_SHA256_CTX *pctx, uint32_t iterations)
{
	for (uint32_t i = pctx->first; i < iterations; i++) {
		hmac_sha256(pctx->pass, pctx->passlen, pctx->g, SHA256_DIGEST_LENGTH, pctx->g);
		for (uint32_t j = 0; j < SHA256_DIGEST_LENGTH; j++) {
			pctx->f[j] ^= pctx->g[j];
		}
	}
	pctx->first = 0;
}

void pbkdf2_hmac_sha256_Final(PBKDF2_HMAC_SHA256_CTX *pctx, uint8_t *key)
{
	memcpy(key, pctx->f, SHA256_DIGEST_LENGTH);
	MEMSET_BZERO(pctx, sizeof(PBKDF2_HMAC_SHA256_CTX));
}

void pbkdf2_hmac_sha256(const uint8_t *pass, int passlen, const uint8_t *salt, int saltlen, uint32_t iterations, uint8_t *key)
{
	PBKDF2_HMAC_SHA256_CTX pctx;
	pbkdf2_hmac_sha256_Init(&pctx, pass, passlen, salt, saltlen);
	pbkdf2_hmac_sha256_Update(&pctx, iterations);
	pbkdf2_hmac_sha256_Final(&pctx, key);
}

void pbkdf2_hmac_sha512_Init(PBKDF2_HMAC_SHA512_CTX *pctx, const uint8_t *pass, int passlen, const uint8_t *salt, int saltlen)
{
	HMAC_SHA512_CTX hctx;
	hmac_sha512_Init(&hctx, pass, passlen);
	hmac_sha512_Update(&hctx, salt, saltlen);
	hmac_sha512_Update(&hctx, (const uint8_t *)"\x00\x00\x00\x01", 4);
	hmac_sha512_Final(&hctx, pctx->g);
	memcpy(pctx->f, pctx->g, SHA512_DIGEST_LENGTH);
	pctx->pass = pass;
	pctx->passlen = passlen;
	pctx->first = 1;
}

void pbkdf2_hmac_sha512_Update(PBKDF2_HMAC_SHA512_CTX *pctx, uint32_t iterations)
{
	for (uint32_t i = pctx->first; i < iterations; i++) {
		hmac_sha512(pctx->pass, pctx->passlen, pctx->g, SHA512_DIGEST_LENGTH, pctx->g);
		for (uint32_t j = 0; j < SHA512_DIGEST_LENGTH; j++) {
			pctx->f[j] ^= pctx->g[j];
		}
	}
	pctx->first = 0;
}

void pbkdf2_hmac_sha512_Final(PBKDF2_HMAC_SHA512_CTX *pctx, uint8_t *key)
{
	memcpy(key, pctx->f, SHA512_DIGEST_LENGTH);
	MEMSET_BZERO(pctx, sizeof(PBKDF2_HMAC_SHA512_CTX));
}

void pbkdf2_hmac_sha512(const uint8_t *pass, int passlen, const uint8_t *salt, int saltlen, uint32_t iterations, uint8_t *key)
{
	PBKDF2_HMAC_SHA512_CTX pctx;
	pbkdf2_hmac_sha512_Init(&pctx, pass, passlen, salt, saltlen);
	pbkdf2_hmac_sha512_Update(&pctx, iterations);
	pbkdf2_hmac_sha512_Final(&pctx, key);
}
