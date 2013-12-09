#ifndef __PBKDF2_H__
#define __PBKDF2_H__

#include <stdint.h>

// salt needs to have 4 extra bytes available beyond saltlen
void pbkdf2(const uint8_t *pass, int passlen, uint8_t *salt, int saltlen, uint32_t iterations, uint8_t *key, int keylen);

#endif
