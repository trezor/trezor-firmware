/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "key_cache.h"
#include "../vault/siv.h"

#if defined(STORAGE_KEY_CACHE_TEST)
extern bool storage_key_cache_wrap(bool encrypt, uint8_t value[40]);
extern void storage_key_cache_random(void *out, size_t length);
#elif defined(USE_VAULT_KEK)
#include <sec/rng_strong.h>
#include <sec/vault_kek.h>
static bool storage_key_cache_wrap(bool encrypt, uint8_t value[40]) {
  return vault_kek_wrap(encrypt, value) == sectrue;
}
#define storage_key_cache_random rng_fill_buffer_strong
#else
#include <sec/rng_strong.h>
#include "../vault/keywrap.h"
/* Emulator/F4 fallback: does not protect against a whole-RAM disclosure. */
static uint8_t cache_soft_kek[32];
static bool cache_soft_kek_ready;
static bool cache_wrap_block(bool encrypt, const uint8_t in[16],
                             uint8_t out[16]) {
  if (!cache_soft_kek_ready) {
    rng_fill_buffer_strong(cache_soft_kek, sizeof(cache_soft_kek));
    cache_soft_kek_ready = true;
  }
  bool ok;
  if (encrypt) {
    aes_encrypt_ctx ctx = {0};
    ok = aes_encrypt_key256(cache_soft_kek, &ctx) == 0 &&
         aes_encrypt(in, out, &ctx) == 0;
    memzero(&ctx, sizeof(ctx));
  } else {
    aes_decrypt_ctx ctx = {0};
    ok = aes_decrypt_key256(cache_soft_kek, &ctx) == 0 &&
         aes_decrypt(in, out, &ctx) == 0;
    memzero(&ctx, sizeof(ctx));
  }
  return ok;
}
static bool storage_key_cache_wrap(bool encrypt, uint8_t value[40]) {
  return vault_keywrap(encrypt, value, cache_wrap_block);
}
#define storage_key_cache_random rng_fill_buffer_strong
#endif

/* Independent of the wallet vault's key, owners and VM-reset lifecycle. */
static struct {
  uint8_t wrapped[80];
  uint8_t ciphertext[STORAGE_CACHED_KEYS_SIZE];
  uint8_t tag[16];
  bool ready;
} sealed_storage_keys;
static const uint8_t cache_aad[32] = "Trezor storage key cache v1";

void storage_key_cache_wipe(void) {
  memzero(&sealed_storage_keys, sizeof(sealed_storage_keys));
#if !defined(USE_VAULT_KEK) && !defined(STORAGE_KEY_CACHE_TEST)
  memzero(cache_soft_kek, sizeof(cache_soft_kek));
  cache_soft_kek_ready = false;
#endif
}
static bool cache_context(vault_siv_ctx *ctx, bool create) {
  uint8_t keys[80] = {0};
  bool ok = false;
  if (create) {
    for (size_t i = 0; i < 2; i++) {
      storage_key_cache_random(keys + 40 * i + 8, 32);
      uint8_t wrapped[40];
      memcpy(wrapped, keys + 40 * i, sizeof(wrapped));
      bool wrapped_ok = storage_key_cache_wrap(true, wrapped);
      if (wrapped_ok)
        memcpy(sealed_storage_keys.wrapped + 40 * i, wrapped, sizeof(wrapped));
      memzero(wrapped, sizeof(wrapped));
      if (!wrapped_ok) goto cleanup;
    }
  } else {
    memcpy(keys, sealed_storage_keys.wrapped, sizeof(keys));
    for (size_t i = 0; i < 2; i++)
      if (!storage_key_cache_wrap(false, keys + 40 * i)) goto cleanup;
  }
  ok = aes_encrypt_key256(keys + 8, &ctx->mac) == 0 &&
       aes_encrypt_key256(keys + 48, &ctx->ctr) == 0;
cleanup:
  memzero(keys, sizeof(keys));
  return ok;
}

bool storage_key_cache_set(const uint8_t keys[STORAGE_CACHED_KEYS_SIZE]) {
  vault_siv_ctx ctx = {0};
  bool ok = cache_context(&ctx, !sealed_storage_keys.ready);
  if (ok) {
    memcpy(sealed_storage_keys.ciphertext, keys, STORAGE_CACHED_KEYS_SIZE);
    ok = vault_siv_record(&ctx, true, cache_aad, sizeof(cache_aad),
                          sealed_storage_keys.ciphertext,
                          STORAGE_CACHED_KEYS_SIZE, sealed_storage_keys.tag);
  }
  memzero(&ctx, sizeof(ctx));
  if (ok)
    sealed_storage_keys.ready = true;
  else
    storage_key_cache_wipe();
  return ok;
}

bool storage_key_cache_get(uint8_t *out, size_t offset, size_t length) {
  if (offset > STORAGE_CACHED_KEYS_SIZE ||
      length > STORAGE_CACHED_KEYS_SIZE - offset)
    return false;
  vault_siv_ctx ctx = {0};
  uint8_t plaintext[STORAGE_CACHED_KEYS_SIZE] = {0}, tag[16];
  bool ok = sealed_storage_keys.ready && cache_context(&ctx, false);
  if (ok) {
    memcpy(plaintext, sealed_storage_keys.ciphertext, sizeof(plaintext));
    memcpy(tag, sealed_storage_keys.tag, sizeof(tag));
    ok = vault_siv_record(&ctx, false, cache_aad, sizeof(cache_aad), plaintext,
                          sizeof(plaintext), tag);
  }
  if (ok)
    memcpy(out, plaintext + offset, length);
  else {
    memzero(out, length);
    storage_key_cache_wipe();
  }
  memzero(plaintext, sizeof(plaintext));
  memzero(tag, sizeof(tag));
  memzero(&ctx, sizeof(ctx));
  return ok;
}
