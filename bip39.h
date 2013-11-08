#ifndef __BIP39_H__
#define __BIP39_H__

#include <stdbool.h>
#include <stdint.h>

const char *mnemonic_encode(uint8_t *data, int len, char *passphrase);

int mnemonic_decode(const char *mnemonic, uint8_t *data, char *passphrase);

#endif
