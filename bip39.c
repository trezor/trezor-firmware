#include <string.h>

#include "bip39.h"
#include "hmac.h"
#include "rand.h"
#include "sha2.h"
#include "bip39_english.h"

#define HMAC_ROUNDS 10000

const char *mnemonic_generate(int strength)
{
	int i;
	static uint32_t data[16];
	if (strength % 32 || strength < 128 || strength > 256) {
		return 0;
	}
	for (i = 0; i < 16; i++) {
		data[i] = random32();
	}
	return mnemonic_from_data((const uint8_t *)data, strength / 8);
}

const char *mnemonic_from_data(const uint8_t *data, int len)
{
	int i, j;
	static uint8_t hash[32];
	static char bits[256 + 8];
	static char mnemo[24 * 10];

	SHA256_Raw((const uint8_t *)data, len, hash);

	for (i = 0; i < len; i++) {
		for (j = 0; j < 8; j++) {
			bits[8 * i + j] = (data[i] & (1 << (7 - j))) > 0;
		}
	}

	char hlen = len / 4;
	for (i = 0; i < hlen; i++) {
		char c = (hash[0] & (1 << (7 - i))) > 0;
		bits[8 * len + i] = c;
	}

	int mlen = len * 3 / 4;

	char *p = mnemo;
	for (i = 0; i < mlen; i++) {
		int idx = 0;
		for (j = 0; j < 11; j++) {
			idx += bits[i * 11 + j] << (10 - j);
		}
		strcpy(p, wordlist[idx]);
		p += strlen(wordlist[idx]);
		*p = (i < mlen - 1) ? ' ' : 0;
		p++;
	}

	return mnemo;
}

void mnemonic_to_seed(const char *mnemonic, const char *passphrase, uint8_t *seed)
{
	static uint8_t k[8 + 256];
	uint8_t *m = seed;
	int i, kl;

	kl = strlen(passphrase);
	memcpy(k, "mnemonic", 8);
	memcpy(k + 8, passphrase, kl);
	kl += 8;

	hmac_sha512(k, kl, (const uint8_t *)mnemonic, strlen(mnemonic), m);
	for (i = 1; i < HMAC_ROUNDS; i++) {
		hmac_sha512(k, kl, m, 512 / 8, m);
	}
}
