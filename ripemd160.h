#ifndef __RIPEMD160_H__
#define __RIPEMD160_H__

#include <stdint.h>

void ripemd160(const uint8_t *msg, uint32_t msg_len, uint8_t *hash);

#endif
