#ifndef __BIP39_H__
#define __BIP39_H__

#include <stdint.h>

const char *mnemonic_generate(int strength);	// strength in bits

const char *mnemonic_from_data(const uint8_t *data, int len);

void mnemonic_to_seed(const char *mnemonic, const char *passphrase, uint8_t seed[512 / 8]);

#endif
