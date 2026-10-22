/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "../../embed/sec/vault/siv.h"
#include "vault_siv_vectors.h"

static size_t decode(const char *hex, uint8_t *out) {
  size_t length = strlen(hex) / 2;
  for (size_t i = 0; i < length; i++) {
    unsigned value;
    assert(sscanf(hex + 2 * i, "%2x", &value) == 1);
    out[i] = value;
  }
  return length;
}
int main(void) {
  for (size_t i = 0; i < sizeof(vectors) / sizeof(vectors[0]); i++) {
    const vector_t *v = &vectors[i];
    uint8_t key[64], aad[64], data[128], original[128], expected[144], tag[16];
    assert(decode(v->key, key) == 64);
    size_t aad_length = decode(v->aad, aad);
    size_t length = decode(v->message, original);
    assert(decode(v->ciphertext, expected) == length + 16);
    vault_siv_ctx ctx = {0};
    assert(aes_encrypt_key256(key, &ctx.mac) == 0);
    assert(aes_encrypt_key256(key + 32, &ctx.ctr) == 0);
    if (v->valid) {
      memcpy(data, original, length);
      assert(vault_siv_record(&ctx, true, aad, aad_length, data, length, tag));
      assert(!memcmp(tag, expected, 16));
      assert(!memcmp(data, expected + 16, length));
    }
    memcpy(tag, expected, 16);
    memcpy(data, expected + 16, length);
    assert(vault_siv_record(&ctx, false, aad, aad_length, data, length, tag) ==
           v->valid);
    if (v->valid) {
      assert(!memcmp(data, original, length));
    } else {
      for (size_t j = 0; j < length; j++) assert(data[j] == 0);
    }
    memzero(&ctx, sizeof(ctx));
    memzero(key, sizeof(key));
  }
  printf("AES-SIV Wycheproof: %zu vectors passed\n",
         sizeof(vectors) / sizeof(vectors[0]));
  return 0;
}

void __attribute__((noreturn)) system_exit_error(const char *title,
                                                 const char *message,
                                                 const char *footer) {
  (void)title;
  (void)footer;
  fprintf(stderr, "firmware fatal: %s\n", message);
  abort();
}
