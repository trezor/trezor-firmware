/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include "aes/aes.h"
#include "siv_core.h"

typedef struct {
  aes_encrypt_ctx mac;
  aes_encrypt_ctx ctr;
} vault_siv_ctx;

static bool siv_software_block(const void *context, bool mac,
                               const uint8_t in[16], uint8_t out[16]) {
  const vault_siv_ctx *ctx = context;
  return aes_encrypt(in, out, mac ? &ctx->mac : &ctx->ctr) == 0;
}

static bool vault_siv_record(const vault_siv_ctx *ctx, bool encrypt,
                             const uint8_t *aad, size_t aad_length,
                             uint8_t *data, size_t length, uint8_t tag[16]) {
  const vault_siv_cipher cipher = {ctx, siv_software_block};
  return vault_siv_cipher_record(&cipher, encrypt, aad, aad_length, data,
                                 length, tag);
}
