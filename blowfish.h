#ifndef __BLOWFISH_H__
#define __BLOWFISH_H__

#include <stdint.h>

void blowfish_setkey(uint8_t *key, int keylen);
void blowfish_encrypt(uint8_t *data, int datalen);
void blowfish_decrypt(uint8_t *data, int datalen);

#endif
