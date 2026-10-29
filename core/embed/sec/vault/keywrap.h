/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "memzero.h"
/* RFC 3394 section 2.2 key wrap. vault_kw_transform() serves KW and KWP with up
 * to 22 semiblocks (t <= 132); vault_keywrap_n() wraps 2 <= n <= 6. The AES
 * primitive may use an opaque hardware key. A failed unwrap never releases
 * partial key bytes. Private to the vault and the storage key cache. */
#define VAULT_KEYWRAP_MAX_N 6
typedef bool (*vault_wrap_block_ctx_t)(const void *ctx, bool encrypt,
                                       const uint8_t in[16], uint8_t out[16]);
/* value holds the 8-byte integrity block followed by n semiblocks; on wrap
 * the first 8 bytes are ignored. */
/* The caller supplies private scratch, never a client-visible buffer. */
static bool vault_kw_transform(bool encrypt, uint8_t *work, size_t n,
                               vault_wrap_block_ctx_t block, const void *ctx) {
  uint8_t b[16] __attribute__((aligned(4))) = {0};
  bool ok = false;
  for (size_t round = 0; round < 6; round++) {
    size_t j = encrypt ? round : 5 - round;
    for (size_t step = 0; step < n; step++) {
      size_t i = encrypt ? step + 1 : n - step;
      /* t <= 132 for the bounded KW/KWP callers; XOR into the least significant
       * byte of big-endian A. */
      memcpy(b, work, 8);
      memcpy(b + 8, work + 8 * i, 8);
      if (!encrypt) b[7] ^= n * j + i;
      if (!block(ctx, encrypt, b, b)) goto cleanup;
      if (encrypt) b[7] ^= n * j + i;
      memcpy(work, b, 8);
      memcpy(work + 8 * i, b + 8, 8);
    }
  }
  ok = true;
cleanup:
  memzero(b, sizeof(b));
  return ok;
}

static bool vault_keywrap_n(bool encrypt, uint8_t *value, size_t n,
                            vault_wrap_block_ctx_t block, const void *ctx) {
  if (n < 2 || n > VAULT_KEYWRAP_MAX_N) return false;
  uint8_t work[8 + 8 * VAULT_KEYWRAP_MAX_N] = {0};
  size_t size = 8 + 8 * n;
  volatile uint8_t diff = 0;
  bool ok = false;
  memcpy(work, value, size);
  if (encrypt) memset(work, 0xa6, 8);
  if (!vault_kw_transform(encrypt, work, n, block, ctx)) goto cleanup;
  /* Integrity is tested twice, so one skipped branch releases no key. */
  if (!encrypt) {
    for (size_t i = 0; i < 8; i++) diff |= work[i] ^ 0xa6;
    if (diff) goto cleanup;
  }
  memcpy(value, work, size);
  if (diff) {
    memzero(value, size);
    goto cleanup;
  }
  ok = true;
cleanup:
  if (!ok) memzero(value, size);
  memzero(work, sizeof(work));
  return ok;
}

typedef bool (*vault_wrap_block_t)(bool encrypt, const uint8_t in[16],
                                   uint8_t out[16]);
static bool vault_keywrap_plain_block(const void *ctx, bool encrypt,
                                      const uint8_t in[16], uint8_t out[16]) {
  return (*(const vault_wrap_block_t *)ctx)(encrypt, in, out);
}
/* A 32-byte key (n = 4) under a context-free block function. */
static inline bool vault_keywrap(bool encrypt, uint8_t value[40],
                                 vault_wrap_block_t block) {
  return vault_keywrap_n(encrypt, value, 4, vault_keywrap_plain_block, &block);
}
