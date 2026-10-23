/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Stage C3: kernel-side SAES record sealing and the SAES storage key cache. A
 * software GCM stand-in plays the secure world; the SAES driver itself only
 * runs on hardware. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#define VAULT_TEST 1
#include "../../embed/sec/vault/seal.c"
#include "../../embed/sec/vault/vault.c"
#define STORAGE_KEY_CACHE_SAES_TEST 1
#include "../../embed/sec/storage/key_cache.c"

/* Unused by SAES sealing; declared by seal.c for the software backends. */
bool vault_wrap_block(bool encrypt, const uint8_t in[16], uint8_t out[16]) {
  (void)encrypt, (void)in, (void)out;
  abort();
}
void vault_random(void *out, size_t length) { memset(out, 0x42, length); }
void rng_fill_buffer(void *out, size_t n) { memset(out, 0x42, n); }
void random_buffer(uint8_t *out, size_t n) { rng_fill_buffer(out, n); }
void __attribute__((noreturn)) __assert_impl(const char *file, int line) {
  fprintf(stderr, "firmware assertion: %s:%d\n", file, line);
  abort();
}
void __attribute__((noreturn)) system_exit_error(const char *title,
                                                 const char *message,
                                                 const char *footer) {
  (void)footer;
  fprintf(stderr, "firmware fatal: %s: %s\n", title, message);
  abort();
}

/* --- Secure-world stand-in ----------------------------------------------- */

typedef struct {
  uint8_t key[32];
  bool ready;
  vault_saes_request_t last;
} sw_key_t;
static sw_key_t sw_record, sw_storage;
static uint8_t sw_generation;
static uint32_t sw_calls;
static vault_saes_request_t sw_last;
static enum { SW_NORMAL, SW_HW_FAIL, SW_CORRUPT_RESULT } sw_mode = SW_NORMAL;

static uint32_t sw_request(sw_key_t *k, vault_saes_request_t *r) {
  sw_calls++;
  sw_last = k->last = *r;
  if (r->op == VAULT_SAES_RESET) {
    memset(k->key, 0, sizeof(k->key));
    k->ready = false;
    return VAULT_SAES_OK;
  }
  if (sw_mode == SW_HW_FAIL) {
    memset(r->data, 0, sizeof(r->data));
    return VAULT_SAES_FAILED;
  }
  if (!k->ready) {
    memset(k->key, ++sw_generation, sizeof(k->key));
    k->ready = true;
  }
  gcm_ctx ctx;
  assert(gcm_init_and_key(k->key, sizeof(k->key), &ctx) == RETURN_GOOD);
  int ret =
      r->op == VAULT_SAES_SEAL
          ? gcm_encrypt_message(r->iv, sizeof(r->iv), r->aad, sizeof(r->aad),
                                r->data, r->length, r->tag, 16, &ctx)
          : gcm_decrypt_message(r->iv, sizeof(r->iv), r->aad, sizeof(r->aad),
                                r->data, r->length, r->tag, 16, &ctx);
  memzero(&ctx, sizeof(ctx));
  if (ret != RETURN_GOOD) {
    memset(r->data, 0, sizeof(r->data));
    return VAULT_SAES_AUTH_FAILED;
  }
  return sw_mode == SW_CORRUPT_RESULT ? VAULT_SAES_OK ^ 1 : VAULT_SAES_OK;
}
uint32_t vault_saes_record(vault_saes_request_t *r) {
  return sw_request(&sw_record, r);
}
uint32_t vault_saes_storage(vault_saes_request_t *r) {
  return sw_request(&sw_storage, r);
}

/* --- Tests ------------------------------------------------------------------
 */

static bool is_zero(const void *p, size_t n) {
  for (size_t i = 0; i < n; i++)
    if (((const uint8_t *)p)[i]) return false;
  return true;
}

static bool seal(uint64_t nonce, const uint8_t aad[VAULT_AAD_SIZE],
                 uint8_t data[VAULT_RECORD_SIZE], size_t length,
                 uint8_t tag[16]) {
  return vault_seal_record(true, nonce, aad, data, length, tag);
}
static bool open(uint64_t nonce, const uint8_t aad[VAULT_AAD_SIZE],
                 uint8_t data[VAULT_RECORD_SIZE], size_t length,
                 uint8_t tag[16]) {
  return vault_seal_record(false, nonce, aad, data, length, tag);
}

/* The first record of a kernel run replaces the record key first. */
static void test_fresh_key(void) {
  sw_record.ready = true; /* a key left over from an earlier kernel run */
  uint8_t aad[VAULT_AAD_SIZE] = {0}, data[VAULT_RECORD_SIZE] = {1}, tag[16];
  uint32_t calls = sw_calls;
  assert(vault_seal_record(true, 1, aad, data, 32, tag));
  assert(sw_calls == calls + 2 && sw_record.last.op == VAULT_SAES_SEAL);
  assert(sw_record.ready);
  /* Only once per run. */
  calls = sw_calls;
  assert(vault_seal_record(true, 2, aad, data, 32, tag));
  assert(sw_calls == calls + 1);
}

static void test_records(void) {
  uint8_t aad[VAULT_AAD_SIZE] = {7}, original[VAULT_RECORD_SIZE];
  for (size_t n = 1; n <= VAULT_RECORD_SIZE; n++) {
    for (size_t i = 0; i < n; i++) original[i] = i + n;
    uint8_t data[VAULT_RECORD_SIZE] = {0}, tag[16] = {0}, ct[VAULT_RECORD_SIZE];
    memcpy(data, original, n);
    assert(seal(n, aad, data, n, tag));
    assert(memcmp(data, original, n));
    /* The request carried the nonce as a big-endian IV after "SV01". */
    assert(sw_last.op == VAULT_SAES_SEAL && sw_last.length == n);
    assert(!memcmp(sw_last.iv, "SV01", 4) && sw_last.iv[11] == (uint8_t)n);
    memcpy(ct, data, n);
    assert(open(n, aad, data, n, tag));
    assert(!memcmp(data, original, n));
    assert(vault_seal_idle());

    /* Every byte of ciphertext, tag and AAD is authenticated, and a tag
     * mismatch is not a key failure. */
    for (size_t i = 0; i < n; i++) {
      memcpy(data, ct, n);
      data[i] ^= 1;
      assert(!open(n, aad, data, n, tag) && is_zero(data, VAULT_RECORD_SIZE));
    }
    for (size_t i = 0; i < 16; i++) {
      memcpy(data, ct, n);
      tag[i] ^= 1;
      assert(!open(n, aad, data, n, tag));
      tag[i] ^= 1;
    }
    memcpy(data, ct, n);
    aad[n % VAULT_AAD_SIZE] ^= 1;
    assert(!open(n, aad, data, n, tag));
    aad[n % VAULT_AAD_SIZE] ^= 1;
    memcpy(data, ct, n);
    assert(!open(n + 1, aad, data, n, tag));
    assert(vault_seal_ready());
  }
  uint8_t data[VAULT_RECORD_SIZE] = {0}, tag[16] = {0};
  assert(!seal(0, aad, data, 0, tag));
  assert(!seal(0, aad, data, VAULT_RECORD_SIZE + 1, tag));
}

static void test_failures(void) {
  uint8_t aad[VAULT_AAD_SIZE] = {0}, data[VAULT_RECORD_SIZE] = {9}, tag[16];
  assert(seal(1, aad, data, 32, tag));
  uint8_t ct[32];
  memcpy(ct, data, sizeof(ct));

  /* A result that is not exactly VAULT_SAES_OK is a key failure. */
  sw_mode = SW_CORRUPT_RESULT;
  assert(!open(1, aad, data, 32, tag) && is_zero(data, sizeof(data)));
  assert(!vault_seal_ready());
  sw_mode = SW_NORMAL;
  /* Until a wipe, the vault refuses to seal without asking SAES. */
  uint32_t calls = sw_calls;
  assert(!seal(2, aad, data, 32, tag) && sw_calls == calls);
  vault_seal_wipe();
  assert(vault_seal_ready() && sw_last.op == VAULT_SAES_RESET);
  /* The new key no longer opens the old record. */
  memcpy(data, ct, sizeof(ct));
  assert(!open(1, aad, data, 32, tag) && vault_seal_ready());

  sw_mode = SW_HW_FAIL;
  assert(!seal(3, aad, data, 32, tag) && !vault_seal_ready());
  sw_mode = SW_NORMAL;
  vault_seal_wipe();
  assert(vault_seal_ready());
}

static bool call(uintptr_t caller, vault_request_t *r, vault_response_t *out) {
  r->abi = VAULT_ABI;
  return vault_dispatch(caller, r, out, true);
}

/* The dispatcher round trip of test_vault_bytes, on SAES records. */
static void test_dispatcher(void) {
  vault_request_t r = {.op = VAULT_OWNER_CREATE};
  vault_response_t out = {0};
  assert(call(1, &r, &out));
  uint32_t session = out.value;
  r = (vault_request_t){.op = VAULT_OWNER_CREATE, .owner = session};
  assert(call(1, &r, &out));
  uint32_t request = out.value;
  for (size_t length = 1; length <= VAULT_SECRET_SIZE; length++) {
    r = (vault_request_t){
        .op = VAULT_IMPORT_BYTES, .owner = request, .length = length};
    for (size_t i = 0; i < length; i++) r.data[i] = i + 1;
    assert(call(1, &r, &out));
    vault_blob_t blob = out.blob;
    secret_transaction_begin();
    size_t actual = 0;
    secret_payload_t *p = secret_open(&blob, request, SECRET_BYTES, &actual);
    assert(p && actual == length && !memcmp(p->bytes, r.data, length));
    assert(secret_transaction_end());
    assert(is_zero(secret_scratch, sizeof(secret_scratch)));
    r = (vault_request_t){.op = VAULT_RETAIN,
                          .owner = request,
                          .arg = SECRET_BYTES,
                          .blob = blob};
    assert(call(1, &r, &out));
  }
  /* Revoking everything resets the SAES record key, not the storage key. */
  sw_storage.ready = true;
  vault_wipe();
  assert(sw_last.op == VAULT_SAES_RESET && !sw_record.ready);
  assert(sw_storage.ready);
  sw_storage.ready = false;
}

static void test_storage_key_cache(void) {
  uint8_t keys[STORAGE_CACHED_KEYS_SIZE], out[STORAGE_CACHED_KEYS_SIZE];
  for (size_t i = 0; i < sizeof(keys); i++) keys[i] = 0x80 + i;
  assert(!storage_key_cache_get(out, 0, sizeof(out))); /* nothing cached */
  assert(storage_key_cache_set(keys));
  /* Sealed under the storage key, with its own IV prefix and AAD. */
  assert(sw_storage.ready && !sw_record.ready);
  assert(!memcmp(sw_storage.last.iv, "SK01", 4));
  assert(sw_storage.last.length == STORAGE_CACHED_KEYS_SIZE);
  assert(memcmp(sealed_storage_keys.ciphertext, keys, sizeof(keys)));
  assert(storage_key_cache_get(out, 0, sizeof(out)));
  assert(!memcmp(out, keys, sizeof(keys)));
  assert(storage_key_cache_get(out, 32, 16) && !memcmp(out, keys + 32, 16));
  assert(!storage_key_cache_get(out, 40, 16));
  assert(!storage_key_cache_get(out, 49, 0));

  /* Each update uses a fresh nonce. */
  uint64_t nonce = sealed_storage_keys.nonce;
  assert(storage_key_cache_set(keys) && sealed_storage_keys.nonce == nonce + 1);

  /* Tampering fails closed and drops both the cache and the storage key. */
  for (size_t i = 0; i < sizeof(keys) + 16; i++) {
    assert(storage_key_cache_set(keys));
    if (i < sizeof(keys))
      sealed_storage_keys.ciphertext[i] ^= 1;
    else
      sealed_storage_keys.tag[i - sizeof(keys)] ^= 1;
    memset(out, 0xff, sizeof(out));
    assert(!storage_key_cache_get(out, 0, sizeof(out)));
    assert(is_zero(out, sizeof(out)));
    assert(!sealed_storage_keys.ready && !sw_storage.ready);
  }

  /* Wipe erases the sealed cache and requests a new storage key. */
  assert(storage_key_cache_set(keys));
  storage_key_cache_wipe();
  assert(is_zero(&sealed_storage_keys, sizeof(sealed_storage_keys)));
  assert(!sw_storage.ready && sw_storage.last.op == VAULT_SAES_RESET);

  /* A hardware failure leaves nothing cached. */
  sw_mode = SW_HW_FAIL;
  assert(!storage_key_cache_set(keys) && !sealed_storage_keys.ready);
  sw_mode = SW_NORMAL;
}

int main(void) {
  test_fresh_key();
  test_records();
  test_failures();
  test_dispatcher();
  test_storage_key_cache();
  puts("SAES record sealing and storage key cache tests passed");
  return 0;
}
