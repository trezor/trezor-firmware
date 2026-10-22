/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Stage C3: kernel-side SAES record sealing. A software GCM stand-in plays the
 * secure world; the SAES driver itself only runs on hardware. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#define VAULT_TEST 1
#include "../../embed/sec/vault/seal.c"
#include "../../embed/sec/vault/vault.c"

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

static uint8_t sw_key[32];
static bool sw_key_ready;
static uint8_t sw_generation;
static uint32_t sw_calls;
static vault_saes_request_t sw_last;
static enum { SW_NORMAL, SW_HW_FAIL, SW_CORRUPT_RESULT } sw_mode = SW_NORMAL;

uint32_t vault_saes_record(vault_saes_request_t *r) {
  sw_calls++;
  sw_last = *r;
  if (r->op == VAULT_SAES_RESET) {
    memset(sw_key, 0, sizeof(sw_key));
    sw_key_ready = false;
    return VAULT_SAES_OK;
  }
  if (sw_mode == SW_HW_FAIL) {
    memset(r->data, 0, sizeof(r->data));
    return VAULT_SAES_FAILED;
  }
  if (!sw_key_ready) {
    memset(sw_key, ++sw_generation, sizeof(sw_key));
    sw_key_ready = true;
  }
  gcm_ctx ctx;
  assert(gcm_init_and_key(sw_key, sizeof(sw_key), &ctx) == RETURN_GOOD);
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
  /* Revoking everything resets the SAES record key. */
  vault_wipe();
  assert(sw_last.op == VAULT_SAES_RESET && !sw_key_ready);
}

int main(void) {
  test_records();
  test_failures();
  test_dispatcher();
  puts("SAES record sealing tests passed");
  return 0;
}
