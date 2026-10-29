/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "consteq.h"
#include "memzero.h"

/* RFC 5297 AES-SIV-CMAC-512, one AAD string. The provider selects either
 * independent MAC or CTR key and encrypts a block without exposing that key. */
typedef struct {
  const void *context;
  bool (*block)(const void *context, bool mac, const uint8_t in[16],
                uint8_t out[16]);
} vault_siv_cipher;

static void siv_double(uint8_t block[16]) {
  uint8_t carry = block[0] >> 7;
  for (size_t i = 0; i < 15; i++)
    block[i] = (block[i] << 1) | (block[i + 1] >> 7);
  block[15] = (block[15] << 1) ^ (0x87 & (uint8_t)(0 - carry));
}

/* CMAC with optional xorend, avoiding a second plaintext-sized buffer. */
static bool siv_cmac(const vault_siv_cipher *ctx, const uint8_t *data,
                     size_t length, const uint8_t *xorend, uint8_t out[16]) {
  uint8_t subkey[16] = {0}, state[16] = {0}, block[16] = {0};
  bool ok = false;
  if (!ctx->block(ctx->context, true, subkey, subkey)) goto cleanup;
  siv_double(subkey);
  if (!length || length % 16) siv_double(subkey);
  size_t blocks = length ? (length + 15) / 16 : 1;
  for (size_t n = 0; n < blocks; n++) {
    memset(block, 0, sizeof(block));
    size_t start = 16 * n;
    size_t count = length - start;
    if (count > 16) count = 16;
    for (size_t i = 0; i < count; i++) {
      size_t index = start + i;
      block[i] = data[index];
      if (xorend && index >= length - 16)
        block[i] ^= xorend[index - (length - 16)];
    }
    if (n == blocks - 1) {
      if (count < 16) block[count] = 0x80;
      for (size_t i = 0; i < 16; i++) block[i] ^= subkey[i];
    }
    for (size_t i = 0; i < 16; i++) block[i] ^= state[i];
    if (!ctx->block(ctx->context, true, block, state)) goto cleanup;
  }
  memcpy(out, state, 16);
  ok = true;
cleanup:
  if (!ok) memzero(out, 16);
  memzero(subkey, sizeof(subkey));
  memzero(state, sizeof(state));
  memzero(block, sizeof(block));
  return ok;
}

static bool siv_s2v(const vault_siv_cipher *ctx, const uint8_t *aad,
                    size_t aad_length, const uint8_t *data, size_t length,
                    uint8_t tag[16]) {
  uint8_t d[16] = {0}, a[16] = {0}, short_data[16] = {0};
  bool ok = false;
  if (!siv_cmac(ctx, d, 16, NULL, d) ||
      !siv_cmac(ctx, aad, aad_length, NULL, a))
    goto cleanup;
  siv_double(d);
  for (size_t i = 0; i < 16; i++) d[i] ^= a[i];
  if (length >= 16) {
    ok = siv_cmac(ctx, data, length, d, tag);
  } else {
    siv_double(d);
    if (length) memcpy(short_data, data, length);
    short_data[length] = 0x80;
    for (size_t i = 0; i < 16; i++) short_data[i] ^= d[i];
    ok = siv_cmac(ctx, short_data, 16, NULL, tag);
  }
cleanup:
  if (!ok) memzero(tag, 16);
  memzero(d, sizeof(d));
  memzero(a, sizeof(a));
  memzero(short_data, sizeof(short_data));
  return ok;
}

static bool siv_ctr(const vault_siv_cipher *ctx, const uint8_t tag[16],
                    uint8_t *data, size_t length) {
  uint8_t counter[16], stream[16] = {0};
  memcpy(counter, tag, 16);
  counter[8] &= 0x7f;
  counter[12] &= 0x7f;
  bool ok = false;
  for (size_t offset = 0; offset < length; offset += 16) {
    if (!ctx->block(ctx->context, false, counter, stream)) goto cleanup;
    size_t count = length - offset;
    if (count > 16) count = 16;
    for (size_t i = 0; i < count; i++) data[offset + i] ^= stream[i];
    for (size_t i = 16; i-- > 0;)
      if (++counter[i]) break;
  }
  ok = true;
cleanup:
  memzero(counter, sizeof(counter));
  memzero(stream, sizeof(stream));
  return ok;
}

static bool vault_siv_cipher_record(const vault_siv_cipher *ctx, bool encrypt,
                                    const uint8_t *aad, size_t aad_length,
                                    uint8_t *data, size_t length,
                                    uint8_t tag[16]) {
  uint8_t expected[16] = {0};
  /* A decrypted record is released only if two independent tag comparisons
   * agree: with CTR, one skipped check would turn bit flips in the
   * ciphertext into chosen bit flips of the key. */
  volatile uint8_t diff = 0;
  bool ok;
  if (encrypt) {
    ok = siv_s2v(ctx, aad, aad_length, data, length, tag) &&
         siv_ctr(ctx, tag, data, length);
  } else {
    ok = siv_ctr(ctx, tag, data, length) &&
         siv_s2v(ctx, aad, aad_length, data, length, expected) &&
         consteq(tag, expected, 16);
    for (size_t i = 0; i < 16; i++) diff |= tag[i] ^ expected[i];
  }
  if (!ok || diff) {
    memzero(data, length);
    ok = false;
  }
  memzero(expected, sizeof(expected));
  return ok;
}
