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
  if (length == sizeof(vault_siv_ctx)) context_erases++;
  if (length == 80) key_erases++;
}
bool storage_key_cache_wrap(bool encrypt, uint8_t value[40]) {
  return vault_keywrap(encrypt, value, vault_wrap_block);
}
void storage_key_cache_random(void *out, size_t length) {
  vault_random(out, length);
}
static void set_cache(const uint8_t keys[48]) {
  storage_key_cache_wipe();
  fail_after = -1;
  assert(storage_key_cache_set(keys));
}
int main(void) {
  uint8_t keys[48], out[48];
  for (size_t i = 0; i < sizeof(keys); i++) keys[i] = 0x80 + i;
  set_cache(keys);
  assert(storage_key_cache_get(out, 0, sizeof(out)));
  assert(!memcmp(out, keys, sizeof(keys)));
  assert(storage_key_cache_get(out, 32, 16));
  assert(!memcmp(out, keys + 32, 16));
  assert(!storage_key_cache_get(out, 49, 0));
  assert(!storage_key_cache_get(out, 32, 17));
  /* Cached plaintext is not retained. Both encryption keys are wrapped, and
   * the caller owns a snapshot independent of future cache updates. */
  assert(memcmp(sealed_storage_keys.ciphertext, keys, sizeof(keys)));
  vault_seal_wipe();
  assert(
      storage_key_cache_get(out, 0, 48)); /* independent VM/vault lifecycle */
  assert(!memcmp(out, keys, 48));
  keys[0] ^= 1;
  assert(storage_key_cache_set(keys));
  assert(storage_key_cache_get(out, 0, 48));
  assert(!memcmp(out, keys, 48));
  /* Authenticate every byte of wrapped keys, ciphertext, tag and ready flag. */
  for (size_t i = 0; i < sizeof(sealed_storage_keys); i++) {
    set_cache(keys);
    ((uint8_t *)&sealed_storage_keys)[i] ^= 1;
    memset(out, 0xaa, sizeof(out));
    assert(!storage_key_cache_get(out, 0, sizeof(out)));
    assert(is_zero(out, sizeof(out)));
    assert(is_zero(&sealed_storage_keys, sizeof(sealed_storage_keys)));
  }
  /* Fail each AES step of wrapping either cache key. */
  for (int step = 0; step < 48; step++) {
    storage_key_cache_wipe();
    fail_after = step;
    assert(!storage_key_cache_set(keys));
    assert(is_zero(&sealed_storage_keys, sizeof(sealed_storage_keys)));
  }
  /* Fail each unwrap step on reads and updates. No old/plain key survives. */
  for (int step = 0; step < 48; step++) {
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
  assert(context_erases > 0 && key_erases > 0);
  puts("protected storage key cache tests passed");
}
