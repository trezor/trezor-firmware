#ifndef __RIPEMD160_H__
#define __RIPEMD160_H__

#include <stdint.h>
#include <stddef.h>

#define RIPEMD160_BLOCK_LENGTH 64
#define RIPEMD160_DIGEST_LENGTH 20

typedef struct {
  uint64_t length;
  union {
    uint32_t w[16];
    uint8_t  b[64];
  } buf;
  uint32_t h[5];
  uint8_t bufpos;
} ripemd160_state;

void ripemd160_init(ripemd160_state * self);
void ripemd160_process(ripemd160_state * self, const uint8_t *in, size_t length);
void ripemd160_done(ripemd160_state * self, uint8_t out[RIPEMD160_DIGEST_LENGTH]);
void ripemd160(const uint8_t *in, size_t length, uint8_t out[RIPEMD160_DIGEST_LENGTH]);
#endif
