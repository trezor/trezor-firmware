/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Byte-buffer ownership and encryption, independent of EC operations. */
#define main sealing_test_main
#include "test_vault_sealing.c"
#undef main
#include "../../embed/sec/vault/vault.c"

/* Used only if later kernel-operation tests link an EC-enabled dispatcher. */
void rng_fill_buffer(void *out, size_t n) { memset(out, 0x42, n); }
void random_buffer(uint8_t *out, size_t n) { rng_fill_buffer(out, n); }
void __attribute__((noreturn)) __assert_impl(const char *file, int line) {
  fprintf(stderr, "firmware assertion: %s:%d\n", file, line);
  abort();
}
static bool call(uintptr_t caller, vault_request_t *r, vault_response_t *out) {
  r->abi = VAULT_ABI;
  return vault_dispatch(caller, r, out, true);
}
static uint32_t owner_create(uintptr_t caller, uint32_t parent) {
  vault_request_t r = {.op = VAULT_OWNER_CREATE, .owner = parent};
  vault_response_t out = {0};
  return call(caller, &r, &out) ? out.value : 0;
}
/* Storage callbacks may inspect/revoke owners without entering crypto or
 * disturbing an interrupted transaction. The handler entry accepts no crypto.
 */
static void lifecycle_callbacks(void) {
  vault_lifecycle_request_t r = {VAULT_ABI, VAULT_OWNER_CREATE, 0};
  vault_lifecycle_response_t out = {0};
  assert(vault_lifecycle_dispatch(17, &r, &out));
  uint32_t session = out.value;
  r.owner = session;
  assert(!vault_lifecycle_dispatch(18, &r, &out));
  assert(vault_lifecycle_dispatch(17, &r, &out));
  uint32_t request = out.value;
  r = (vault_lifecycle_request_t){VAULT_ABI, VAULT_OWNER_INFO, request};
  assert(vault_lifecycle_dispatch(17, &r, &out));
  assert(out.parent == session);
  secret_owner_find(request)->authorized_locked = true;
  assert(vault_lifecycle_dispatch(17, &r, &out) && out.value == 1);
  assert(!vault_lifecycle_dispatch(18, &r, &out));
  assert(is_zero(&out, sizeof(out)));
  r.abi++;
  assert(!vault_lifecycle_dispatch(17, &r, &out));
  r.abi = VAULT_ABI;
  for (uint32_t op = VAULT_RETAIN; op <= VAULT_NEM_SHARED; op++) {
    r.op = op;
    assert(!vault_lifecycle_dispatch(17, &r, &out));
  }
  r.op = VAULT_OWNER_INFO;
  memset(secret_scratch, 0x5a, sizeof(secret_scratch));
  secret_busy = true;
  assert(!vault_lifecycle_dispatch(17, &r, &out));
  assert(secret_busy && ((uint8_t *)secret_scratch)[0] == 0x5a);
  secret_busy = false;
  memzero(secret_scratch, sizeof(secret_scratch));
  r.op = VAULT_REVOKE_REQUESTS;
  assert(vault_lifecycle_dispatch(17, &r, &out));
  assert(!secret_owner_find(request) && secret_owner_find(session));
  r.op = VAULT_RESET;
  assert(vault_lifecycle_dispatch(17, &r, &out));
  assert(!secret_owner_find(session));
  assert(!secret_busy);
}

int main(void) {
  lifecycle_callbacks();
  uint32_t session = owner_create(1, 0), request = owner_create(1, session);
  uint32_t sibling = owner_create(1, session);
  assert(session && request && sibling && !owner_create(2, session));
  assert(!owner_create(1, request));
  for (size_t length = 1; length <= VAULT_SECRET_SIZE; length++) {
    vault_request_t r = {
        .op = VAULT_IMPORT_BYTES, .owner = request, .length = length};
    for (size_t i = 0; i < length; i++) r.data[i] = i + 1;
    vault_response_t out = {0};
    assert(call(1, &r, &out));
    assert(is_zero(secret_scratch, sizeof(secret_scratch)));
    vault_blob_t blob = out.blob;
    size_t used =
        VAULT_HEADER_SIZE + vault_ciphertext_size(length) + VAULT_TAG_SIZE;
    assert(is_zero(blob.bytes + used, sizeof(blob.bytes) - used));
    secret_transaction_begin();
    size_t actual = 0;
    assert(!secret_open(&blob, sibling, SECRET_BYTES, NULL));
    secret_payload_t *p = secret_open(&blob, request, SECRET_BYTES, &actual);
    assert(p && actual == length && !memcmp(p->bytes, r.data, length));
    assert(secret_transaction_end());
    assert(is_zero(secret_scratch, sizeof(secret_scratch)));
    r = (vault_request_t){.op = VAULT_RETAIN,
                          .owner = request,
                          .arg = SECRET_BYTES,
                          .blob = blob};
    assert(!call(2, &r, &out));
    r.abi = VAULT_ABI;
    assert(!vault_dispatch(1, &r, &out, false));
    assert(call(1, &r, &out));
    secret_transaction_begin();
    assert(secret_open(&out.blob, sibling, SECRET_BYTES, NULL));
    assert(secret_transaction_end());
    r.blob = out.blob;
    assert(
        !call(1, &r, &out)); /* already retained, not a request-owned value */
  }
  vault_request_t r = {
      .op = VAULT_IMPORT_BYTES, .owner = request, .length = 32};
  vault_response_t out = {0};
  assert(call(1, &r, &out));
  vault_blob_t old = out.blob;
  vault_revoke_caller(1);
  assert(!secret_owner_find(request) && !secret_owner_find(session));
  uint32_t fresh = owner_create(1, 0);
  secret_transaction_begin();
  assert(!secret_open(&old, fresh, SECRET_BYTES, NULL));
  assert(secret_transaction_end());
  vault_wipe();
  assert(is_zero(secret_scratch, sizeof(secret_scratch)));
  puts("AES byte-buffer ownership, length, retain and cleanup tests passed");
  return 0;
}
