#pragma once

#include <stdbool.h>

#define XSHA256_CONTEXT_SAVING 0

typedef struct {
  uint32_t q[16 + 1];
  size_t q_size;
  size_t q_exp;
#if XSHA256_CONTEXT_SAVING
  uint32_t state[38];
  bool state_valid;
#endif
} xsha256_ctx_t;

void xsha256_init(xsha256_ctx_t* ctx);

void xsha256_update(xsha256_ctx_t* ctx, const uint8_t* in, size_t inlen);

void xsha256_digest(xsha256_ctx_t* ctx, uint8_t* out);

// optimized combination of update and digest
void xsha256_final(xsha256_ctx_t* ctx, uint8_t* out, const uint8_t* in,
                   size_t inlen);
