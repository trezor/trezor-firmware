#include <string.h>

#include "hmac.h"
#include "sha2.h"

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
}
