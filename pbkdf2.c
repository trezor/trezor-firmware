#include <string.h>
#include "pbkdf2.h"
#include "hmac.h"

#define HMACFUNC hmac_sha512
#define HMACLEN  (512/8)

void pbkdf2(const uint8_t *pass, int passlen, uint8_t *salt, int saltlen, uint32_t iterations, uint8_t *key, int keylen)
{
	uint32_t i, j, k;
	uint8_t f[HMACLEN], g[HMACLEN];
	uint32_t blocks = keylen / HMACLEN;
	if (keylen & (HMACLEN - 1)) {
		blocks++;
	}
	for (i = 1; i <= blocks; i++) {
		salt[saltlen    ] = (i >> 24) & 0xFF;
		salt[saltlen + 1] = (i >> 16) & 0xFF;
		salt[saltlen + 2] = (i >> 8) & 0xFF;
		salt[saltlen + 3] = i & 0xFF;
		HMACFUNC(pass, passlen, salt, saltlen + 4, g);
		memcpy(f, g, HMACLEN);
		for (j = 1; j < iterations; j++) {
			HMACFUNC(pass, passlen, g, HMACLEN, g);
			for (k = 0; k < HMACLEN; k++) {
				f[k] ^= g[k];
			}
		}
		if (i == blocks - 1 && (keylen & (HMACLEN - 1))) {
			memcpy(key + HMACLEN * (i - 1), f, keylen & (HMACLEN - 1));
		} else {
			memcpy(key + HMACLEN * (i - 1), f, HMACLEN);
		}
	}
}
