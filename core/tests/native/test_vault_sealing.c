/* SPDX-License-Identifier: GPL-3.0-or-later */
/* AES-only tests: no HDNode, ECDSA, Ed25519 or kernel operation dispatcher. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#define VAULT_TEST 1
#include "../../embed/sec/vault/seal.c"

static int fail_after = -1;
static bool is_zero(const void *p, size_t n) {
  for (size_t i = 0; i < n; i++)
    if (((const uint8_t *)p)[i]) return false;
  return true;
}
bool vault_wrap_block(bool encrypt, const uint8_t in[16], uint8_t out[16]) {
  if (fail_after == 0) return false;
  if (fail_after > 0) fail_after--;
  const uint8_t key[32] = {0};
  bool ok;
  if (encrypt) {
    aes_encrypt_ctx ctx = {0};
    ok = aes_encrypt_key256(key, &ctx) == 0 && aes_encrypt(in, out, &ctx) == 0;
    memzero(&ctx, sizeof(ctx));
  } else {
    aes_decrypt_ctx ctx = {0};
    ok = aes_decrypt_key256(key, &ctx) == 0 && aes_decrypt(in, out, &ctx) == 0;
    memzero(&ctx, sizeof(ctx));
  }
  return ok;
}
void vault_random(void *out, size_t length) {
  static uint8_t sequence;
  memset(out, ++sequence, length);
}
int main(void) {
  uint8_t aad[VAULT_AAD_SIZE] = {1}, original[VAULT_RECORD_SIZE];
  for (size_t n = 1; n <= VAULT_RECORD_SIZE; n++) {
    for (size_t i = 0; i < sizeof(original); i++) original[i] = i + n;
    size_t length = vault_ciphertext_size(n);
    uint8_t data[VAULT_RECORD_SIZE] = {0}, tag[16] = {0};
    memcpy(data, original, n);
    assert(vault_seal_record(true, n, aad, data, length, tag));
    assert(memcmp(data, original, n));
    vault_seal_end();
    assert(is_zero(&record_ctx, sizeof(record_ctx)));
    uint8_t ciphertext[VAULT_RECORD_SIZE];
    memcpy(ciphertext, data, length);
    assert(vault_seal_record(false, n, aad, data, length, tag));
    assert(!memcmp(data, original, n));
    vault_seal_end();
#if VAULT_TAG_SIZE
    for (size_t i = 0; i < length; i++) {
      memcpy(data, ciphertext, length);
      data[i] ^= 1;
      assert(!vault_seal_record(false, n, aad, data, length, tag));
      assert(is_zero(data, length));
      vault_seal_end();
    }
    memcpy(data, ciphertext, length);
    aad[0] ^= 1;
    assert(!vault_seal_record(false, n, aad, data, length, tag));
    assert(is_zero(data, length));
    aad[0] ^= 1;
    vault_seal_end();
#endif
  }
  assert(vault_seal_ready());
  wrapped_dek[8] ^= 1;
  uint8_t data[16] = {0}, tag[16] = {0};
  assert(!vault_seal_record(true, 1, aad, data, sizeof(data), tag));
  assert(!vault_seal_ready());
  assert(is_zero(&record_ctx, sizeof(record_ctx)));
  assert(is_zero(wrapped_dek, sizeof(wrapped_dek)));
  fail_after = 0;
  assert(!vault_seal_record(true, 1, aad, data, sizeof(data), tag));
  assert(!vault_seal_ready());
  puts("AES-only sealing and cleanup tests passed");
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
