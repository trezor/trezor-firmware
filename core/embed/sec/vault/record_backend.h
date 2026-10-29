/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <sec/vault_cipher.h>
#include "gcm.h"
#include "kwp.h"

typedef struct {
  const vault_cipher_provider_t *provider;
  bool failed;
} vault_kwp_backend_context;
static bool vault_kwp_backend_block(const void *context, bool encrypt,
                                    const uint8_t in[16], uint8_t out[16]) {
  vault_kwp_backend_context *ctx = (vault_kwp_backend_context *)context;
  bool ok = !ctx->failed &&
            ctx->provider->block(ctx->provider->context, encrypt, in, out);
  ctx->failed = !ok;
  return ok;
}
static inline uint32_t vault_kwp_backend_record(
    const vault_cipher_provider_t *cipher, vault_cipher_request_t *r) {
  uint32_t result = VAULT_CIPHER_FAILED;
  vault_kwp_backend_context context = {.provider = cipher};
  if (cipher->block &&
      (r->op == VAULT_CIPHER_SEAL || r->op == VAULT_CIPHER_OPEN) && r->length &&
      r->length <= VAULT_CIPHER_RECORD_SIZE && r->length % 8 == 0) {
    bool ok = vault_kwp_cipher_record(&context, vault_kwp_backend_block,
                                      r->op == VAULT_CIPHER_SEAL, r->aad,
                                      r->data, r->length, r->tag);
    result = ok               ? VAULT_CIPHER_OK
             : context.failed ? VAULT_CIPHER_FAILED
                              : VAULT_CIPHER_AUTH_FAILED;
  }
  memzero(&context, sizeof(context));
  if (result != VAULT_CIPHER_OK) memzero(r->data, sizeof(r->data));
  return result;
}
