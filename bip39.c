#include <string.h>

#include "bip39.h"
#include "sha2.h"
#include "aes.h"
#include "bip39_english.h"

#define RIJNDAEL_ITERATIONS 10000

void mnemonic_rijndael(uint8_t *data, int len, char *passphrase, bool encrypt)
{
	if (len != 16 && len != 24 && len != 32) return;

	SHA256_CTX sha_ctx;
	aes_ctx ctx;
	uint8_t key[32];
	int i;

	SHA256_Init(&sha_ctx);
	SHA256_Update(&sha_ctx, (uint8_t *)"mnemonic", 8);
	if (passphrase) {
		SHA256_Update(&sha_ctx, (uint8_t *)passphrase, strlen(passphrase));
	}
	SHA256_Final(key, &sha_ctx);

	aes_blk_len(len, &ctx);

	if (encrypt) {
		aes_enc_key(key, 32, &ctx);
		for (i = 0; i < RIJNDAEL_ITERATIONS; i++) {
			aes_enc_blk(data, data, &ctx);
		}
	} else {
		aes_dec_key(key, 32, &ctx);
		for (i = 0; i < RIJNDAEL_ITERATIONS; i++) {
			aes_dec_blk(data, data, &ctx);
		}
	}
}

#define mnemonic_stretch(D, L, P) mnemonic_rijndael((D), (L), (P), true)
#define mnemonic_unstretch(D, L, P) mnemonic_rijndael((D), (L), (P), false)

static char mnemo[24 * 10];
static char bits[256 + 8];

char mnemonic_checksum(uint8_t *data, int len)
{
	char r = 0;
	int i;
	switch (len) {
		case 16:	// checksum = 4 bits
			for (i = 0; i < 16; i++) {
				r ^= (data[i] & 0xF0) >> 4;
				r ^= (data[i] & 0x0F);
			}
			break;
		case 24:	// checksum = 6 bits
			for (i = 0; i < 8; i++) {
				r ^= (data[3 * i] & 0xFC) >> 2;						// xxxxxx__ ________ ________
				r ^= ((data[3 * i] & 0x03) << 4) | ((data[3 * i + 1] & 0xF0) >> 4);	// ______xx xxxx____ ________
				r ^= ((data[3 * i + 1] & 0x0F) << 2) | ((data[3 * i + 2] & 0xC0) >> 6);	// ________ ____xxxx xx______
				r ^= data[3 * i + 2] & 0x3F;						// ________ ________ __xxxxxx
			}
			break;
		case 32:	// checksum = 8 bits
			for (i = 0; i < 32; i++) {
				r ^= data[i];
			}
			break;
	}
	return r;
}

const char *mnemonic_encode(uint8_t *data, int len, char *passphrase)
{
	if (len != 16 && len != 24 && len != 32) return 0;

	mnemonic_stretch(data, len, passphrase);

	int i, j;
	for (i = 0; i < len; i++) {
		for (j = 0; j < 8; j++) {
			bits[8 * i + j] = (data[i] & (1 << (7 - j))) > 0;
		}
	}

	char checksum = mnemonic_checksum(data, len);
	for (j = 0; j < (len/4); j++) {
		bits[8 * len + j] = (checksum & (1 << ((len / 4 - 1) - j))) > 0;
	}

	len = len * 3 / 4;
	char *p = mnemo;
	for (i = 0; i < len; i++) {
		int idx = 0;
		for (j = 0; j < 11; j++) {
			idx += bits[i * 11 + j] << (10 - j);
		}
		strcpy(p, wordlist[idx]);
		p += strlen(wordlist[idx]);
		*p = (i < len - 1) ? ' ' : 0;
		p++;
	}

	return mnemo;
}

int wordlist_index(const char *word)
{
	int i = 0;
	while (wordlist[i]) {
		if (strcmp(word, wordlist[i]) == 0) return i;
		i++;
	}
	return -1;
}

int mnemonic_decode(const char *mnemonic, uint8_t *data, char *passphrase)
{
	strcpy(mnemo, mnemonic);

	int i, j, b = 0, len;
	char *p = strtok(mnemo, " ");
	while (p) {
		int idx = wordlist_index(p);
		if (idx < 0 || idx > 2047) return 0;
		for (j = 0; j < 11; j++) {
			bits[b] = (idx & (1 << (10 - j))) > 0;
			b++;
		}
		p = strtok(NULL, " ");
	}
	if (b != 128 + 4 && b != 192 + 6 && b != 256 + 8) return 0;

	len = b / 33 * 4;

	for (i = 0; i < len; i++) {
		data[i] = 0;
		for (j = 0; j < 8; j++) {
			data[i] |= bits[8 * i + j] << (7 - j);
		}
	}
	char checksum = 0;
	for (j = 0; j < (len/4); j++) {
		checksum |= bits[8 * len + j] << ((len / 4 - 1) - j);
	}
	if (checksum != mnemonic_checksum(data, len)) {
		return 0;
	}

	mnemonic_unstretch(data, len, passphrase);

	return len;
}
