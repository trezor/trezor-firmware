/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include "aes/aes.h"
#include "consteq.h"
#include "keywrap.h"

#define VAULT_KWP_METADATA_SIZE 12
#define VAULT_KWP_MAX_PLAINTEXT (VAULT_KWP_METADATA_SIZE + 160)
#define VAULT_KWP_ENVELOPE 24

/* NIST SP 800-38F KWP (RFC 5649). work is call-private scratch with room
 * for the 8-byte AIV and padded plaintext. Never unwrap in client memory. */
static bool vault_kwp_crypt(bool encrypt, uint8_t *work, size_t length,
                            vault_wrap_block_ctx_t block, const void *ctx) {
  if (!length || length > VAULT_KWP_MAX_PLAINTEXT) return false;
  size_t padded = (length + 7) & ~(size_t)7;
  uint8_t aiv[8] = {0xa6, 0x59, 0x59, 0xa6};
  for (size_t i = 0; i < 4; i++) aiv[4 + i] = length >> (24 - 8 * i);
  if (encrypt) {
    memcpy(work, aiv, sizeof(aiv));
    memset(work + 8 + length, 0, padded - length);
  }
  bool ok = padded == 8
                ? block(ctx, encrypt, work, work)
                : vault_kw_transform(encrypt, work, padded / 8, block, ctx);
  volatile uint8_t diff = 0;
  if (!encrypt) {
    ok = ok && consteq(work, aiv, sizeof(aiv));
    for (size_t i = 0; i < sizeof(aiv); i++) diff |= work[i] ^ aiv[i];
    for (size_t i = length; i < padded; i++) diff |= work[8 + i];
  }
  ok = ok && diff == 0;
  if (!ok) memzero(work, 8 + padded);
  memzero(aiv, sizeof(aiv));
  return ok;
}

/* The canonical AAD has a 4-byte domain/ABI and an 8-byte header; reserved
 * bytes must be zero. Wrap those 12 bytes alongside the payload. The split
 * ciphertext keeps the existing bounded record transport. */
static bool vault_kwp_cipher_record(const void *ctx,
                                    vault_wrap_block_ctx_t block, bool encrypt,
                                    const uint8_t aad[32], uint8_t data[160],
                                    size_t length,
                                    uint8_t envelope[VAULT_KWP_ENVELOPE]) {
  if (!length || length > 160 || length % 8) return false;
  /* Four additional padding bytes cover the maximum 172-byte plaintext. */
  uint8_t work[8 + ((VAULT_KWP_MAX_PLAINTEXT + 7) & ~7)] = {0};
  uint8_t reserved = 0;
  for (size_t i = VAULT_KWP_METADATA_SIZE; i < 32; i++) reserved |= aad[i];
  if (reserved) {
    memzero(data, 160);
    return false;
  }
  if (encrypt) {
    memcpy(work + 8, aad, VAULT_KWP_METADATA_SIZE);
    memcpy(work + 8 + VAULT_KWP_METADATA_SIZE, data, length);
  } else {
    memcpy(work, envelope, VAULT_KWP_ENVELOPE);
    memcpy(work + VAULT_KWP_ENVELOPE, data, length);
  }
  bool ok = vault_kwp_crypt(encrypt, work, VAULT_KWP_METADATA_SIZE + length,
                            block, ctx);
  volatile uint8_t diff = 0;
  if (!encrypt) {
    ok = ok && consteq(work + 8, aad, VAULT_KWP_METADATA_SIZE);
    for (size_t i = 0; i < VAULT_KWP_METADATA_SIZE; i++)
      diff |= work[8 + i] ^ aad[i];
    ok = ok && diff == 0;
  }
  if (ok) {
    memcpy(data,
           work + (encrypt ? VAULT_KWP_ENVELOPE : 8 + VAULT_KWP_METADATA_SIZE),
           length);
    if (encrypt) memcpy(envelope, work, VAULT_KWP_ENVELOPE);
  } else {
    memzero(data, 160);
    if (encrypt) memzero(envelope, VAULT_KWP_ENVELOPE);
  }
  memzero(work, sizeof(work));
  return ok;
}

static inline bool vault_kwp_software_block(const void *ctx, bool encrypt,
                                            const uint8_t in[16],
                                            uint8_t out[16]) {
  return (encrypt ? aes_encrypt(in, out, (const aes_encrypt_ctx *)ctx)
                  : aes_decrypt(in, out, (const aes_decrypt_ctx *)ctx)) == 0;
}
