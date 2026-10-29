/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <stddef.h>
#include "memzero.h"
static size_t key_erases, context_erases;
static void observed_memzero(void *p, size_t len);
#define memzero observed_memzero
#define main vault_boundary_main
#include "test_vault.c"
#undef main
#undef memzero

static void zero(const void *p, size_t len) {
  for (size_t i = 0; i < len; i++) assert(((const uint8_t *)p)[i] == 0);
}
/* Observe erasure while stack allocations are still alive, avoiding reads
 * through pointers into returned/dead stack frames. */
static void observed_memzero(void *p, size_t len) {
  memzero(p, len);
  zero(p, len);
  if (len == 40) key_erases++;
  if (len == sizeof(record_ctx)) context_erases++;
}
static void idle(void) {
  zero(secret_scratch, sizeof(secret_scratch));
  zero(secret_scratch_used, sizeof(secret_scratch_used));
  zero(&record_ctx, sizeof(record_ctx));
  assert(!key_active && !secret_busy && !secret_crypto_failed);
  assert(!zkp_context_is_initialized());
}
static void unhex(const char *hex, uint8_t *data, size_t len) {
  for (size_t i = 0; i < len; i++) {
    unsigned byte;
    assert(sscanf(hex + 2 * i, "%2x", &byte) == 1);
    data[i] = byte;
  }
}
/* A fresh vault key and an owner holding one 32-byte secret. */
static uint32_t key_owner;
static vault_blob_t new_key(void) {
  vault_wipe();
  fail_after = -1;
  key_owner = owner_create(1, 0);
  assert(key_owner);
  vault_response_t out = {0};
  vault_request_t r = {.op = VAULT_IMPORT_BYTES,
                       .arg = VAULT_KEY_SECP256K1,
                       .owner = key_owner,
                       .length = 32};
  memset(r.data, 1, 32);
  assert(call(1, &r, &out));
  idle();
  return out.blob;
}
static bool sign_key(const vault_blob_t *blob) {
  bool ok = sign(key_owner, blob, NULL);
  idle();
  return ok;
}
static void keywrap_vector(void) {
  /* RFC 3394 section 4.6: 256-bit KEK wrapping a 256-bit key. */
  for (int i = 0; i < 32; i++) test_kek[i] = i;
  uint8_t value[40] = {0}, expected[40], original[32];
  unhex("00112233445566778899aabbccddeeff000102030405060708090a0b0c0d0e0f",
        value + 8, 32);
  memcpy(original, value + 8, 32);
  unhex(
      "28c9f404c4b810f4cbccb35cfb87f8263f5786e2d80ed326cbc7f0e71a99f43bfb988b9b"
      "7a02dd21",
      expected, 40);
  assert(vault_keywrap(true, value, vault_wrap_block));
  assert(!memcmp(value, expected, 40));
  assert(vault_keywrap(false, value, vault_wrap_block));
  assert(!memcmp(value + 8, original, 32));
  for (size_t i = 0; i < 40; i++) {
    memcpy(value, expected, 40);
    value[i] ^= 1;
    assert(!vault_keywrap(false, value, vault_wrap_block));
    zero(value, sizeof(value));
  }
  /* Fail every individual AES step in wrapping and unwrapping. */
  for (int step = 0; step < 24; step++) {
    for (int encrypt = 0; encrypt < 2; encrypt++) {
      memcpy(value, expected, 40);
      fail_after = step;
      assert(!vault_keywrap(encrypt, value, vault_wrap_block));
      zero(value, sizeof(value));
    }
  }
  fail_after = -1;
}
static void gcm_reference(void) {
  /* Independent cryptography.AESGCM reference: key=0^256,
   * IV="SV01" || be64(1), AAD=0^256, plaintext=0^1280. */
  uint8_t key[40] = {0}, data[VAULT_RECORD_SIZE] = {0},
          tag[VAULT_TAG_BUFFER_SIZE], expected[176], aad[VAULT_AAD_SIZE] = {0};
  assert(vault_keywrap(true, key, vault_wrap_block));
  memcpy(wrapped_dek, key, 40);
  key_ready = true;
  unhex(
      "182475f27c1399d17930e8b97e107697bf9f04c724f0236bbfc7e1b7eb30338fe68ba0b0"
      "0ac22c026a1386d01b55391d6fb418065d0e6856dd2e08091fa50b681a21cb0d981f03e2"
      "5300c3a5ad28f35f6f419eb03648f570092d622bd8462138dc058f6a289fb99ba24ca44b"
      "f195c1270cf076c9f99715bbd9d71d457518ef673f2f574c19e1138752cdb587be8eb83f"
      "1d0fb6e15f71c8f374dd88157483a734715d59d763265123a867bc5c0072b322",
      expected, sizeof(expected));
  assert(vault_seal_record(true, 1, aad, data, sizeof(data), tag));
  assert(!memcmp(data, expected, sizeof(data)) &&
         !memcmp(tag, expected + sizeof(data), 16));
  assert(vault_seal_record(false, 1, aad, data, sizeof(data), tag));
  zero(data, sizeof(data));
  vault_seal_end();
  idle();
  vault_seal_wipe();
}
/* Exercise every compact record size, including both sides of AES block
 * boundaries. Wire padding must remain zero and length/tag tampering fails. */
static void compact_records(void) {
  vault_wipe();
  fail_after = -1;
  uint32_t owner = owner_create(1, 0);
  for (size_t length = 1; length <= VAULT_SECRET_SIZE; length++) {
    vault_request_t r = {.op = VAULT_IMPORT_BYTES,
                         .arg = VAULT_KEY_SYMMETRIC,
                         .owner = owner,
                         .length = length};
    for (size_t i = 0; i < length; i++) r.data[i] = i + 1;
    vault_response_t out = {0};
    assert(call(1, &r, &out));
    idle();
    size_t end = vault_bytes_blob_size(length);
    zero(out.blob.bytes + end, VAULT_BLOB_SIZE - end);
    secret_transaction_begin();
    size_t decoded_length = 0;
    secret_payload_t *p =
        secret_open(&out.blob, owner, VAULT_KEY_ANY_BYTES, &decoded_length);
    assert(p && decoded_length == length);
    assert(!memcmp(p->bytes, r.data, length));
    assert(secret_transaction_end());
    idle();
    for (size_t index = 0; index < VAULT_BLOB_SIZE; index++) {
      vault_blob_t forged = out.blob;
      forged.bytes[index] ^= 1;
      secret_transaction_begin();
      assert(!secret_open(&forged, owner, VAULT_KEY_ANY_BYTES, NULL));
      assert(secret_transaction_end());
      idle();
      assert(secret_owner_find(owner));
    }
  }
  vault_wipe();
}
static void compact_nodes(void) {
  vault_wipe();
  fail_after = -1;
  uint32_t owner = owner_create(1, 0);
  const char *curves[] = {SECP256K1_NAME, NIST256P1_NAME, ED25519_NAME};
  for (size_t c = 0; c < sizeof(curves) / sizeof(*curves); c++) {
    vault_request_t r = {.op = VAULT_FROM_SEED, .owner = owner, .length = 16};
    strcpy(r.curve, curves[c]);
    memset(r.data, 0x42, r.length);
    vault_response_t out = {0};
    assert(call(1, &r, &out));
    vault_blob_t blob = out.blob;
    zero(blob.bytes + VAULT_NODE_BLOB_SIZE,
         sizeof(blob.bytes) - VAULT_NODE_BLOB_SIZE);
    r = (vault_request_t){.op = VAULT_PUBLIC, .owner = owner, .blob = blob};
    assert(call(1, &r, &out));
    vault_blob_t cached = out.blob;
    assert(!is_zero(&cached, sizeof(cached)));
    r.blob = cached;
    assert(call(1, &r, &out));
    assert(is_zero(&out.blob, sizeof(out.blob)));
    size_t start = VAULT_TAG_SIZE ? 0 : VAULT_NODE_BLOB_SIZE;
    for (size_t i = start; i < sizeof(blob.bytes); i++) {
      r.blob = cached;
      r.blob.bytes[i] ^= 1;
      assert(!call(1, &r, &out));
      zero(&out, sizeof(out));
      idle();
    }
    /* Compact encoding must not silently discard a future curve's extension. */
    secret_transaction_begin();
    secret_payload_t *p =
        secret_open(&cached, owner, VAULT_KEY(VAULT_KEY_NODE), NULL);
    assert(p && is_zero(p->node.private_key_extension, 32));
    p->node.private_key_extension[0] = 1;
    assert(!secret_seal(owner, VAULT_KEY_NODE, sizeof(HDNode), p, &blob));
    zero(&blob, sizeof(blob));
    assert(secret_transaction_end());
    idle();
  }
  vault_wipe();
}

int main(void) {
  compact_nodes();
  keywrap_vector();
  gcm_reference();
  compact_records();
  assert(vault_boundary_main() == 0);
  idle();

  /* Every blob byte is authenticated or checked. Clients control blob
   * contents, so a forged blob is an ordinary failure: plaintext scratch is
   * wiped, the owner stays live and the genuine blob keeps working. */
  for (size_t i = 0; i < VAULT_BLOB_SIZE; i++) {
    vault_blob_t genuine = new_key(), forged = genuine;
    forged.bytes[i] ^= 1;
    assert(!sign_key(&forged));
    assert(secret_owner_find(key_owner));
    assert(sign_key(&genuine));
  }
  /* Relabelling must fail in authenticated modes. ECB intentionally exposes
   * the missing protection so no test claims it has authenticated ownership. */
  vault_blob_t h = new_key();
  uint32_t first_owner = key_owner;
  key_owner = owner_create(1, 0);
  assert(key_owner);
  vault_blob_t relabelled = h;
  for (size_t i = 0; i < 4; i++) relabelled.bytes[i] = key_owner >> (8 * i);
  assert(!sign_key(&relabelled));
  key_owner = first_owner;
  assert(sign_key(&h));
  /* Kind confusion: a bytes blob is not a node, and vice versa. */
  vault_response_t out = {0};
  vault_request_t r = {.op = VAULT_PUBLIC, .owner = key_owner, .blob = h};
  assert(!call(1, &r, &out));
  idle();
  /* Blobs are values: an earlier blob of the same secret stays valid for the
   * owner's lifetime. Only owner destruction or key rotation revokes it. */
  r = (vault_request_t){.op = VAULT_IMPORT_BYTES,
                        .arg = VAULT_KEY_SECP256K1,
                        .owner = key_owner,
                        .length = 32};
  memset(r.data, 1, 32);
  assert(call(1, &r, &out));
  assert(memcmp(&out.blob, &h, sizeof(h))); /* fresh nonce, fresh blob */
  assert(sign_key(&out.blob) && sign_key(&h));

  /* Bounded scratch: exhaustion is an ordinary failure. */
  h = new_key();
  secret_transaction_begin();
  for (size_t i = 0; i < SECRET_SCRATCH_CAPACITY; i++)
    assert(secret_scratch_take());
  assert(!secret_scratch_take());
  assert(secret_transaction_end());
  idle();
  assert(sign_key(&h));

  /* Inject failures while first creating/wrapping and then unwrapping a DEK:
   * kernel-side key failures fail closed, revoking all owners. */
  for (int step = 0; step < 48 * VAULT_KEY_COUNT; step++) {
    vault_wipe();
    fail_after = -1;
    uint32_t owner = owner_create(1, 0);
    r = (vault_request_t){.op = VAULT_IMPORT_BYTES,
                          .arg = VAULT_KEY_SYMMETRIC,
                          .owner = owner,
                          .length = 32};
    memset(r.data, 1, 32);
    fail_after = step;
    assert(!call(1, &r, &out));
    zero(&out, sizeof(out));
    idle();
    assert(!secret_owner_find(owner));
  }
  fail_after = -1;

  /* Nonce exhaustion never wraps, including failed writes. */
  h = new_key();
  secret_nonce = UINT64_MAX;
  r = (vault_request_t){.op = VAULT_IMPORT_BYTES,
                        .arg = VAULT_KEY_SECP256K1,
                        .owner = key_owner,
                        .length = 32};
  assert(!call(1, &r, &out));
  assert(secret_nonce == UINT64_MAX);
  idle();
  assert(sign_key(&h)); /* opening needs no nonce */
  secret_nonce = 10000; /* test-only fresh boot state */

  /* Failing the DEK unwrap on use: the call fails and nothing leaks. */
  for (int step = 0; step < 24 * VAULT_KEY_COUNT; step++) {
    h = new_key();
    fail_after = step;
    assert(!sign_key(&h));
    assert(!secret_owner_find(key_owner));
    fail_after = -1;
  }
  h = new_key();
  wrapped_dek[8] ^= 1;
  assert(!sign_key(&h));
  vault_wipe();
  zero(wrapped_dek, sizeof(wrapped_dek));
  idle();
  assert(key_erases > 0 && context_erases > 0);
  puts("encrypted vault tests passed");
  return 0;
}
