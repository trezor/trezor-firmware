/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "key_cache.h"

/* Wherever SAES exists, in its secure world, the cache is sealed with AES-GCM
 * in SAES under its own DHUK-wrapped key, which no smcall reaches. That holds
 * for every vault record mode, hardware or software. Without SAES (F4 and the
 * emulator) the cached keys are wrapped in software below. Tests substitute
 * vault_saes_storage(). */
#if (defined(USE_VAULT_KEK) && defined(SECURE_MODE)) || \
    defined(STORAGE_KEY_CACHE_SAES_TEST)
#include <sec/vault_kek.h>
#include <string.h>
#include "memzero.h"

_Static_assert(STORAGE_CACHED_KEYS_SIZE <= VAULT_SAES_RECORD_SIZE, "size");

static struct {
  uint8_t ciphertext[STORAGE_CACHED_KEYS_SIZE];
  uint8_t tag[16];
  uint64_t nonce;
  bool ready;
} sealed_storage_keys;
/* Monotonic for the whole boot; a wipe also replaces the key. */
static uint64_t cache_nonce;
static const uint8_t cache_aad[VAULT_SAES_AAD_SIZE] =
    "Trezor storage key cache v2";

static void cache_request(vault_saes_request_t *r, uint32_t op,
                          uint64_t nonce) {
  memset(r, 0, sizeof(*r));
  r->op = op;
  r->length = STORAGE_CACHED_KEYS_SIZE;
  memcpy(r->iv, "SK01", 4);
  for (size_t i = 0; i < 8; i++) r->iv[4 + i] = nonce >> (56 - 8 * i);
  memcpy(r->aad, cache_aad, sizeof(r->aad));
}

void storage_key_cache_wipe(void) {
  memzero(&sealed_storage_keys, sizeof(sealed_storage_keys));
  vault_saes_request_t r = {.op = VAULT_SAES_RESET};
  vault_saes_storage(&r);
}

bool storage_key_cache_set(const uint8_t keys[STORAGE_CACHED_KEYS_SIZE]) {
  vault_saes_request_t r;
  bool ok = cache_nonce != UINT64_MAX;
  uint64_t nonce = ok ? ++cache_nonce : 0;
  cache_request(&r, VAULT_SAES_SEAL, nonce);
  memcpy(r.data, keys, STORAGE_CACHED_KEYS_SIZE);
  ok = ok && vault_saes_storage(&r) == VAULT_SAES_OK;
  if (ok) {
    memcpy(sealed_storage_keys.ciphertext, r.data, STORAGE_CACHED_KEYS_SIZE);
    memcpy(sealed_storage_keys.tag, r.tag, sizeof(sealed_storage_keys.tag));
    sealed_storage_keys.nonce = nonce;
    sealed_storage_keys.ready = true;
  }
  memzero(&r, sizeof(r));
  if (!ok) storage_key_cache_wipe();
  return ok;
}

bool storage_key_cache_get(uint8_t *out, size_t offset, size_t length) {
  if (offset > STORAGE_CACHED_KEYS_SIZE ||
      length > STORAGE_CACHED_KEYS_SIZE - offset)
    return false;
  vault_saes_request_t r;
  cache_request(&r, VAULT_SAES_OPEN, sealed_storage_keys.nonce);
  memcpy(r.data, sealed_storage_keys.ciphertext, STORAGE_CACHED_KEYS_SIZE);
  memcpy(r.tag, sealed_storage_keys.tag, sizeof(sealed_storage_keys.tag));
  bool ok =
      sealed_storage_keys.ready && vault_saes_storage(&r) == VAULT_SAES_OK;
  if (ok) {
    memcpy(out, r.data + offset, length);
  } else {
    memzero(out, length);
    storage_key_cache_wipe();
  }
  memzero(&r, sizeof(r));
  return ok;
}

#else  // software AES key wrap

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

#endif  // software AES key wrap
