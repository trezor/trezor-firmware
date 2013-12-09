#include <string.h>
#include "pbkdf2.h"
#include "hmac.h"

void pbkdf2(const uint8_t *pass, int passlen, uint8_t *salt, int saltlen, uint32_t iterations, uint8_t *key, int keylen)
{
	uint32_t i, j, k;
	uint8_t f[64], g[64];
	uint32_t blocks = keylen / 64;	// SHA-512
	if (keylen & 63) {
		blocks++;
	}
	for (i = 1; i <= blocks; i++) {
		salt[saltlen    ] = (i >> 24) & 0xFF;
		salt[saltlen + 1] = (i >> 16) & 0xFF;
		salt[saltlen + 2] = (i >> 8) & 0xFF;
		salt[saltlen + 3] = i & 0xFF;
		hmac_sha512(pass, passlen, salt, saltlen + 4, g);
		memcpy(f, g, 64);
		for (j = 1; j < iterations; j++) {
			hmac_sha512(pass, passlen, g, 64, g);
			for (k = 0; k < 64; k++) {
				f[k] ^= g[k];
			}
		}
		if (i == blocks - 1 && (keylen & 63)) {
			for (j = 0; j < (keylen & 63); j++) {
				key[64 * (i - 1) + j] = f[j];
			}
		} else {
			for (j = 0; j < 64; j++) {
				key[64 * (i - 1) + j] = f[j];
			}
		}
	}
}
