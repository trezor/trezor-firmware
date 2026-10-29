/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "key_cache.h"

#include <string.h>
#include "../vault/keywrap.h"
#include "aes/aes.h"
#include "memzero.h"

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

/* The cached keys are wrapped with AES key wrap (RFC 3394) under a per-boot
 * cache key, which is itself wrapped under the KEK. Key wrap is made for key
 * material: it needs no nonce or nonce state, no GHASH table, and its 64-bit
 * integrity check is the standard for wrapped keys. The cache key is
 * expanded once per call. */
#define CACHE_SEMIBLOCKS (STORAGE_CACHED_KEYS_SIZE / 8)
_Static_assert(STORAGE_CACHED_KEYS_SIZE % 8 == 0 &&
                   CACHE_SEMIBLOCKS <= VAULT_KEYWRAP_MAX_N,
               "cached keys must fit one key wrap");

/* Independent of the wallet vault's key, owners and VM-reset lifecycle. */
static struct {
  uint8_t wrapped_key[40];
  uint8_t wrapped_keys[8 + STORAGE_CACHED_KEYS_SIZE];
  bool ready;
} sealed_storage_keys;

void storage_key_cache_wipe(void) {
  memzero(&sealed_storage_keys, sizeof(sealed_storage_keys));
#if !defined(USE_VAULT_KEK) && !defined(STORAGE_KEY_CACHE_TEST)
  memzero(cache_soft_kek, sizeof(cache_soft_kek));
  cache_soft_kek_ready = false;
#endif
}

static bool cache_block(const void *ctx, bool encrypt, const uint8_t in[16],
                        uint8_t out[16]) {
  return (encrypt ? aes_encrypt(in, out, (const aes_encrypt_ctx *)ctx)
                  : aes_decrypt(in, out, (const aes_decrypt_ctx *)ctx)) == 0;
}

/* The cache key in key[8..40]: unwrapped, or created and wrapped when nothing
 * is cached. */
static bool cache_key(uint8_t key[40], bool create) {
  if (!create) {
    memcpy(key, sealed_storage_keys.wrapped_key, 40);
    return storage_key_cache_wrap(false, key);
  }
  uint8_t wrapped[40] = {0};
  storage_key_cache_random(key + 8, 32);
  memcpy(wrapped, key, sizeof(wrapped));
  bool ok = storage_key_cache_wrap(true, wrapped);
  if (ok) memcpy(sealed_storage_keys.wrapped_key, wrapped, sizeof(wrapped));
  memzero(wrapped, sizeof(wrapped));
  return ok;
}

bool storage_key_cache_set(const uint8_t keys[STORAGE_CACHED_KEYS_SIZE]) {
  uint8_t key[40] = {0}, wrapped[8 + STORAGE_CACHED_KEYS_SIZE] = {0};
  aes_encrypt_ctx ctx = {0};
  bool ok = cache_key(key, !sealed_storage_keys.ready) &&
            aes_encrypt_key256(key + 8, &ctx) == 0;
  memzero(key, sizeof(key));
  if (ok) {
    memcpy(wrapped + 8, keys, STORAGE_CACHED_KEYS_SIZE);
    ok = vault_keywrap_n(true, wrapped, CACHE_SEMIBLOCKS, cache_block, &ctx);
  }
  memzero(&ctx, sizeof(ctx));
  if (ok) {
    memcpy(sealed_storage_keys.wrapped_keys, wrapped, sizeof(wrapped));
    sealed_storage_keys.ready = true;
  } else {
    storage_key_cache_wipe();
  }
  memzero(wrapped, sizeof(wrapped));
  return ok;
}

bool storage_key_cache_get(uint8_t *out, size_t offset, size_t length) {
  if (offset > STORAGE_CACHED_KEYS_SIZE ||
      length > STORAGE_CACHED_KEYS_SIZE - offset)
    return false;
  uint8_t key[40] = {0}, keys[8 + STORAGE_CACHED_KEYS_SIZE] = {0};
  aes_decrypt_ctx ctx = {0};
  bool ok = sealed_storage_keys.ready && cache_key(key, false) &&
            aes_decrypt_key256(key + 8, &ctx) == 0;
  memzero(key, sizeof(key));
  if (ok) {
    memcpy(keys, sealed_storage_keys.wrapped_keys, sizeof(keys));
    /* Releases nothing unless the integrity block checks, twice. */
    ok = vault_keywrap_n(false, keys, CACHE_SEMIBLOCKS, cache_block, &ctx);
  }
  memzero(&ctx, sizeof(ctx));
  if (ok) {
    memcpy(out, keys + 8 + offset, length);
  } else {
    memzero(out, length);
    storage_key_cache_wipe();
  }
  memzero(keys, sizeof(keys));
  return ok;
}
