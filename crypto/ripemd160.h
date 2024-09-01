#ifndef _RIPEMD160_H_
#define _RIPEMD160_H_

#include <stdint.h>

typedef struct {
  uint64_t length;
  union {
    uint32_t w[16];
    uint8_t  b[64];
  } buf;
  uint32_t h[5];
  uint8_t bufpos;
} ripemd160_state;

#ifndef _RIPEMD160_C_
void ripemd160_init(ripemd160_state * md);
void ripemd160_process(ripemd160_state * md, const void *in, unsigned long inlen);
void ripemd160_done(ripemd160_state * md, void *out);
void ripemd160(const void *in, unsigned long inlen, void *out);
#endif

#endif
