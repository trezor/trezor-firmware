/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Native-GCM provider stand-in: verifies the port contract, not H5 silicon. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "../../embed/sec/vault/record_backend.h"
#include "aes/aesgcm.h"

typedef struct {
  aes_encrypt_ctx encrypt;
  aes_decrypt_ctx decrypt;
  gcm_ctx gcm;
  unsigned native_calls, block_calls;
  bool fail;
} test_engine;
static bool block(const void *context, bool encrypt, const uint8_t in[16],
                  uint8_t out[16]) {
  test_engine *engine = (test_engine *)context;
  engine->block_calls++;
  if (engine->fail) {
    memset(out, 0xa5, 16);
    return false;
  }
  return (encrypt ? aes_encrypt(in, out, &engine->encrypt)
                  : aes_decrypt(in, out, &engine->decrypt)) == 0;
}
static bool native_gcm(const void *context, bool encrypt, const uint8_t iv[12],
                       const uint8_t aad[32], const uint8_t *in, size_t length,
                       uint8_t *out, uint8_t tag[16]) {
  test_engine *engine = (test_engine *)context;
  engine->native_calls++;
  memcpy(out, in, length);
  if (engine->fail) {
    memset(out, 0xa5, length);
    return false;
  }
  return gcm_init_message(iv, 12, &engine->gcm) == RETURN_GOOD &&
         gcm_auth_header(aad, 32, &engine->gcm) == RETURN_GOOD &&
         (encrypt ? gcm_encrypt(out, length, &engine->gcm)
                  : gcm_decrypt(out, length, &engine->gcm)) == RETURN_GOOD &&
         gcm_compute_tag(tag, 16, &engine->gcm) == RETURN_GOOD;
}
static void zero_data(const vault_cipher_request_t *r) {
  for (size_t i = 0; i < sizeof(r->data); i++) assert(!r->data[i]);
}
int main(void) {
  uint8_t key[32];
  for (size_t i = 0; i < sizeof(key); i++) key[i] = 7 * i;
  test_engine engine = {0};
  assert(!aes_encrypt_key256(key, &engine.encrypt));
  assert(!aes_decrypt_key256(key, &engine.decrypt));
  assert(gcm_init_and_key(key, 32, &engine.gcm) == RETURN_GOOD);
  const vault_cipher_provider_t native = {&engine, block, native_gcm};
  const vault_cipher_provider_t ecb = {&engine, block, NULL};
  for (size_t n = 1; n <= VAULT_CIPHER_RECORD_SIZE; n++) {
    vault_cipher_request_t input = {.op = VAULT_CIPHER_SEAL, .length = n};
    for (size_t i = 0; i < n; i++) input.data[i] = i + n;
    for (size_t i = 0; i < sizeof(input.aad); i++) input.aad[i] = 3 * i + 1;
    for (size_t i = 0; i < sizeof(input.iv); i++) input.iv[i] = 7 * i + n;
    vault_cipher_request_t sw = input, hw = input;
    unsigned calls = engine.block_calls;
    assert(vault_gcm_cipher_record(&native, &hw) == VAULT_CIPHER_OK);
    assert(engine.block_calls ==
           calls); /* native GCM never falls back to ECB */
#ifdef VAULT_NATIVE_GCM
    assert(vault_gcm_cipher_record(&ecb, &sw) == VAULT_CIPHER_FAILED);
    zero_data(&sw);
    sw = input;
    assert(vault_gcm_ecb_record(&ecb, &sw) == VAULT_CIPHER_OK);
#else
    assert(vault_gcm_cipher_record(&ecb, &sw) == VAULT_CIPHER_OK);
#endif
    assert(!memcmp(sw.data, hw.data, n) && !memcmp(sw.tag, hw.tag, 16));
    /* The same format opens across implementations. */
    sw.op = VAULT_CIPHER_OPEN;
    assert(vault_gcm_cipher_record(&native, &sw) == VAULT_CIPHER_OK);
    assert(!memcmp(sw.data, input.data, n));
    sw = hw;
    sw.op = VAULT_CIPHER_OPEN;
#ifdef VAULT_NATIVE_GCM
    assert(vault_gcm_ecb_record(&ecb, &sw) == VAULT_CIPHER_OK);
#else
    assert(vault_gcm_cipher_record(&ecb, &sw) == VAULT_CIPHER_OK);
#endif
    for (size_t i = 0; i < 16; i++) {
      vault_cipher_request_t bad = hw;
      bad.op = VAULT_CIPHER_OPEN;
      bad.tag[i] ^= 1;
      assert(vault_gcm_cipher_record(&native, &bad) ==
             VAULT_CIPHER_AUTH_FAILED);
      zero_data(&bad);
    }
    for (size_t i = 0; i < 32; i++) {
      vault_cipher_request_t bad = hw;
      bad.op = VAULT_CIPHER_OPEN;
      bad.aad[i] ^= 1;
      assert(vault_gcm_cipher_record(&native, &bad) ==
             VAULT_CIPHER_AUTH_FAILED);
      zero_data(&bad);
    }
    vault_cipher_request_t bad = hw;
    bad.op = VAULT_CIPHER_OPEN;
    bad.data[n - 1] ^= 1;
    assert(vault_gcm_cipher_record(&native, &bad) == VAULT_CIPHER_AUTH_FAILED);
    zero_data(&bad);
    bad = hw;
    bad.op = VAULT_CIPHER_OPEN;
    bad.iv[0] ^= 1;
    assert(vault_gcm_cipher_record(&native, &bad) == VAULT_CIPHER_AUTH_FAILED);
    zero_data(&bad);
    engine.fail = true;
    calls = engine.block_calls;
    bad = hw;
    bad.op = VAULT_CIPHER_OPEN;
    assert(vault_gcm_cipher_record(&native, &bad) == VAULT_CIPHER_FAILED);
    assert(engine.block_calls == calls);
    zero_data(&bad);
    engine.fail = false;
  }
  vault_cipher_request_t invalid = {
      .op = VAULT_CIPHER_RESET, .length = 32, .data = {1}};
  unsigned calls = engine.native_calls;
  assert(vault_gcm_cipher_record(&native, &invalid) == VAULT_CIPHER_FAILED);
  assert(engine.native_calls == calls);
  zero_data(&invalid);
  for (size_t length = 0; length <= VAULT_CIPHER_RECORD_SIZE + 1;
       length += VAULT_CIPHER_RECORD_SIZE + 1) {
    invalid.op = VAULT_CIPHER_SEAL;
    invalid.length = length;
    invalid.data[0] = 1;
    assert(vault_gcm_cipher_record(&native, &invalid) == VAULT_CIPHER_FAILED);
    assert(engine.native_calls == calls);
    zero_data(&invalid);
  }
  const vault_cipher_provider_t missing = {.context = &engine};
  invalid.op = VAULT_CIPHER_SEAL;
  invalid.length = 32;
  invalid.data[0] = 1;
  assert(vault_gcm_cipher_record(&missing, &invalid) == VAULT_CIPHER_FAILED);
  zero_data(&invalid);
  vault_cipher_request_t kw = {
      .op = VAULT_CIPHER_SEAL, .length = 32, .data = {7}};
  calls = engine.native_calls;
  assert(vault_kwp_backend_record(&native, &kw) == VAULT_CIPHER_OK);
  assert(engine.native_calls ==
         calls); /* KWP uses ECB even on native-GCM MCUs */
  kw.op = VAULT_CIPHER_OPEN;
  assert(vault_kwp_backend_record(&native, &kw) == VAULT_CIPHER_OK &&
         kw.data[0] == 7);
  kw.op = VAULT_CIPHER_SEAL;
  engine.fail = true;
  assert(vault_kwp_backend_record(&native, &kw) == VAULT_CIPHER_FAILED);
  zero_data(&kw);
  memzero(&engine, sizeof(engine));
  puts(
      "native/ECB GCM interoperability, authenticated release and KWP provider "
      "checks passed");
}
void __attribute__((noreturn)) system_exit_error(const char *title,
                                                 const char *message,
                                                 const char *footer) {
  (void)title;
  (void)message;
  (void)footer;
  abort();
}
