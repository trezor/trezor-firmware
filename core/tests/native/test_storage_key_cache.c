/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include "memzero.h"
static void observed_memzero(void *out, size_t length);
#define memzero observed_memzero
#define main vault_boundary_main
#include "test_vault_sealing.c"
#undef main
#define STORAGE_KEY_CACHE_TEST 1
#include "../../embed/sec/storage/key_cache.c"
#undef memzero

static unsigned context_erases, key_erases;
static void observed_memzero(void *out, size_t length) {
  memzero(out, length);
  assert(is_zero(out, length));
  if (length == sizeof(aes_encrypt_ctx) || length == sizeof(aes_decrypt_ctx))
    context_erases++;
  if (length == 40) key_erases++;
}
bool storage_key_cache_wrap(bool encrypt, uint8_t value[40]) {
  return vault_keywrap(encrypt, value, vault_wrap_block);
}
void storage_key_cache_random(void *out, size_t length) {
  vault_random(out, length);
}
/* The cache key is wrapped under the KEK in 24 AES blocks. */
static void set_cache(const uint8_t keys[48]) {
  storage_key_cache_wipe();
  fail_after = 24;
  assert(storage_key_cache_set(keys));
  assert(fail_after == 0);
  fail_after = -1;
}
int main(void) {
  uint8_t keys[48], out[48];
  for (size_t i = 0; i < sizeof(keys); i++) keys[i] = 0x80 + i;
  set_cache(keys);
  /* AES key wrap reference from Python cryptography (OpenSSL), which also
   * reproduces RFC 3394 section 4.6: cache key 01*32, keys 80..af. */
  static const uint8_t expected[56] = {
      0x0a, 0x95, 0x2c, 0x5d, 0x4e, 0xc1, 0x13, 0x9a, 0x81, 0x04, 0x19, 0x2d,
      0xdb, 0xc4, 0x52, 0x07, 0xbe, 0xcf, 0xcb, 0x94, 0xfd, 0x59, 0xbd, 0xe2,
      0xda, 0xc1, 0x73, 0xb2, 0x30, 0xfa, 0x9a, 0x28, 0x65, 0xc4, 0x38, 0xc4,
      0xe2, 0x24, 0xb6, 0xdf, 0xe6, 0x78, 0xce, 0xec, 0x2c, 0xe9, 0x2c, 0x4e,
      0x0f, 0x34, 0xe5, 0xec, 0xa2, 0xff, 0x9e, 0x1a};
  assert(!memcmp(sealed_storage_keys.wrapped_keys, expected, sizeof(expected)));
  /* Reads unwrap the cache key (24 blocks) and the keys under it. */
  fail_after = 24;
  assert(storage_key_cache_get(out, 0, sizeof(out)));
  assert(fail_after == 0);
  fail_after = -1;
  assert(!memcmp(out, keys, sizeof(keys)));
  assert(storage_key_cache_get(out, 32, 16));
  assert(!memcmp(out, keys + 32, 16));
  assert(!storage_key_cache_get(out, 49, 0));
  assert(!storage_key_cache_get(out, 32, 17));
  /* Cached plaintext is not retained. The cache key is wrapped, and the
   * caller owns a snapshot independent of future cache updates. */
  assert(memcmp(sealed_storage_keys.wrapped_keys + 8, keys, sizeof(keys)));
  vault_seal_wipe();
  assert(
      storage_key_cache_get(out, 0, 48)); /* independent VM/vault lifecycle */
  assert(!memcmp(out, keys, 48));
  /* An update keeps the cache key and rewraps the new keys. */
  uint8_t wrapped_key[40];
  memcpy(wrapped_key, sealed_storage_keys.wrapped_key, sizeof(wrapped_key));
  keys[0] ^= 1;
  assert(storage_key_cache_set(keys));
  assert(!memcmp(wrapped_key, sealed_storage_keys.wrapped_key, 40));
  assert(storage_key_cache_get(out, 0, 48));
  assert(!memcmp(out, keys, 48));
  /* A wipe replaces the cache key. */
  set_cache(keys);
  assert(memcmp(wrapped_key, sealed_storage_keys.wrapped_key, 40));
  /* Every stored byte is authenticated: the wrapped cache key, the wrapped
   * keys and the ready flag. */
  for (size_t i = 0; i < offsetof(__typeof__(sealed_storage_keys), ready) + 1;
       i++) {
    set_cache(keys);
    ((uint8_t *)&sealed_storage_keys)[i] ^= 1;
    memset(out, 0xaa, sizeof(out));
    assert(!storage_key_cache_get(out, 0, sizeof(out)));
    assert(is_zero(out, sizeof(out)));
    assert(is_zero(&sealed_storage_keys, sizeof(sealed_storage_keys)));
  }
  /* Fail each AES step of wrapping the cache key. */
  for (int step = 0; step < 24; step++) {
    storage_key_cache_wipe();
    fail_after = step;
    assert(!storage_key_cache_set(keys));
    assert(is_zero(&sealed_storage_keys, sizeof(sealed_storage_keys)));
  }
  /* Fail each unwrap step on reads and updates. No old/plain key survives. */
  for (int step = 0; step < 24; step++) {
    set_cache(keys);
    fail_after = step;
    memset(out, 0xaa, sizeof(out));
    assert(!storage_key_cache_get(out, 0, sizeof(out)));
    assert(is_zero(out, sizeof(out)));
    assert(is_zero(&sealed_storage_keys, sizeof(sealed_storage_keys)));
    set_cache(keys);
    fail_after = step;
    assert(!storage_key_cache_set(keys));
    assert(is_zero(&sealed_storage_keys, sizeof(sealed_storage_keys)));
  }
  fail_after = -1;
  storage_key_cache_wipe();
  memset(out, 0xaa, sizeof(out));
  assert(!storage_key_cache_get(out, 0, sizeof(out)));
  assert(is_zero(out, sizeof(out)));

  /* The general key wrap still matches RFC 3394 section 4.6 (n = 4) and
   * refuses semiblock counts outside 2..6. */
  uint8_t value[56] = {0};
  static const uint8_t rfc_key[32] = {
      0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88, 0x99, 0xaa,
      0xbb, 0xcc, 0xdd, 0xee, 0xff, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05,
      0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f};
  static const uint8_t rfc_wrapped[40] = {
      0x28, 0xc9, 0xf4, 0x04, 0xc4, 0xb8, 0x10, 0xf4, 0xcb, 0xcc,
      0xb3, 0x5c, 0xfb, 0x87, 0xf8, 0x26, 0x3f, 0x57, 0x86, 0xe2,
      0xd8, 0x0e, 0xd3, 0x26, 0xcb, 0xc7, 0xf0, 0xe7, 0x1a, 0x99,
      0xf4, 0x3b, 0xfb, 0x98, 0x8b, 0x9b, 0x7a, 0x02, 0xdd, 0x21};
  uint8_t rfc_kek[32];
  for (int i = 0; i < 32; i++) rfc_kek[i] = i;
  aes_encrypt_ctx rfc_ctx = {0};
  assert(aes_encrypt_key256(rfc_kek, &rfc_ctx) == 0);
  memcpy(value + 8, rfc_key, 32);
  assert(vault_keywrap_n(true, value, 4, cache_block, &rfc_ctx));
  assert(!memcmp(value, rfc_wrapped, 40));
  for (size_t n = 0; n < 9; n++)
    if (n < 2 || n > VAULT_KEYWRAP_MAX_N)
      assert(!vault_keywrap_n(true, value, n, cache_block, &rfc_ctx));
  memset(&rfc_ctx, 0, sizeof(rfc_ctx));

  assert(context_erases > 0 && key_erases > 0);
  puts("protected storage key cache tests passed");
}
