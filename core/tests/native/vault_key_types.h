/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Key-type regression shared by test_vault.c and test_vault_saes.c, so it
 * runs in every sealing mode, with software and SAES records. Include after
 * vault.c. A key works only for its own type; see the secure buffers
 * security fixes document, finding 1. */
#include <assert.h>
#include <stdint.h>
#include <string.h>

static bool key_types_call(vault_request_t *r, vault_response_t *out) {
  r->abi = VAULT_ABI;
  return vault_dispatch(1, r, out, true);
}

static bool key_types_refused(vault_request_t *r) {
  vault_response_t out = {0};
  if (key_types_call(r, &out)) return false;
  for (size_t i = 0; i < sizeof(out); i++)
    if (((const uint8_t *)&out)[i]) return false;
  return true;
}

static uint32_t key_types_owner(uint32_t parent) {
  vault_request_t r = {.op = VAULT_OWNER_CREATE, .owner = parent};
  vault_response_t out = {0};
  return key_types_call(&r, &out) ? out.value : 0;
}

static bool key_types_sign(uint32_t owner, const vault_blob_t *key) {
  vault_request_t r = {
      .op = VAULT_SIGN, .owner = owner, .blob = *key, .length = 32};
  memset(r.data, 0x42, 32);
  vault_response_t out = {0};
  return key_types_call(&r, &out);
}

static void key_types(void) {
  secret_revoke_all();
  uint32_t session = key_types_owner(0), owner = key_types_owner(session);
  assert(session && owner);
  vault_response_t out = {0};
  vault_request_t r = {.op = VAULT_IMPORT_BYTES,
                       .arg = VAULT_KEY_SEED,
                       .owner = owner,
                       .length = 64};
  for (int i = 0; i < 64; i++) r.data[i] = i * 7 + 1;
  assert(key_types_call(&r, &out));
  vault_blob_t seed = out.blob;
  assert(seed.bytes[6] == VAULT_KEY_SEED);
  r = (vault_request_t){
      .op = VAULT_FROM_SEED, .owner = owner, .arg = 1, .blob = seed};
  strcpy(r.curve, SECP256K1_NAME);
  assert(key_types_call(&r, &out));
  vault_blob_t node = out.blob;
  r = (vault_request_t){.op = VAULT_SNAPSHOT, .owner = owner, .blob = node};
  assert(key_types_call(&r, &out));
  vault_blob_t key = out.blob;
  assert(key.bytes[6] == VAULT_KEY_SECP256K1);

  /* The cross-curve signature pair of finding 1: secp256k1 signs, NIST P-256
   * refuses the same key. */
  assert(key_types_sign(owner, &key));
  r = (vault_request_t){
      .op = VAULT_NIST_SIGN, .owner = owner, .blob = key, .length = 32};
  memset(r.data, 0x42, 32);
  assert(key_types_refused(&r));
  r = (vault_request_t){
      .op = VAULT_NIST_PUBLIC, .owner = owner, .blob = key, .arg = 1};
  assert(key_types_refused(&r));
  r.arg = 2 | 1; /* the secp256k1 public key */
  assert(key_types_call(&r, &out));
  uint8_t point[33];
  memcpy(point, out.signature, 33);

  /* ECDH on its own curve only. */
  r = (vault_request_t){
      .op = VAULT_ECDH, .owner = owner, .blob = key, .length = 33};
  memcpy(r.data, point, 33);
  assert(key_types_call(&r, &out));
  for (uint32_t curve = 1; curve <= 2; curve++) {
    r.arg = curve;
    r.length = curve == 2 ? 32 : 33;
    assert(key_types_refused(&r));
  }

  /* Other uses of a secp256k1 key. BIP-340 shares the curve. */
  const uint32_t other_ops[] = {VAULT_ED_PUBLIC, VAULT_THP_PUBLIC,
                                VAULT_HMAC_TAG};
  for (size_t i = 0; i < sizeof(other_ops) / sizeof(*other_ops); i++) {
    r = (vault_request_t){.op = other_ops[i],
                          .owner = owner,
                          .blob = key,
                          .arg = other_ops[i] == VAULT_HMAC_TAG ? 256 : 0,
                          .length = other_ops[i] == VAULT_HMAC_TAG ? 1 : 0};
    assert(key_types_refused(&r));
  }
  r = (vault_request_t){
      .op = VAULT_SCHNORR_PUBLIC, .owner = owner, .blob = key};
  assert(key_types_call(&r, &out));
  r = (vault_request_t){
      .op = VAULT_FROM_SEED, .owner = owner, .arg = 1, .blob = key};
  strcpy(r.curve, SECP256K1_NAME);
  assert(key_types_refused(&r));
  r = (vault_request_t){.op = VAULT_SLIP21,
                        .owner = owner,
                        .blob = key,
                        .arg = VAULT_SLIP21_ROOT};
  assert(key_types_refused(&r));

  /* A seed is not a key. */
  assert(!key_types_sign(owner, &seed));
  r = (vault_request_t){.op = VAULT_HMAC_TAG,
                        .owner = owner,
                        .blob = seed,
                        .arg = 256,
                        .length = 1};
  assert(key_types_refused(&r));

  /* Imports may choose any type but a node. Values past 31 would be
   * undefined as a shift count; the sanitizers check that they are not. */
  const uint32_t bad_types[] = {0,  VAULT_KEY_NODE, VAULT_KEY_TYPE_END, 32,
                                33, UINT32_MAX};
  for (size_t i = 0; i < sizeof(bad_types) / sizeof(*bad_types); i++) {
    r = (vault_request_t){.op = VAULT_IMPORT_BYTES,
                          .arg = bad_types[i],
                          .owner = owner,
                          .length = 32};
    assert(key_types_refused(&r));
  }

  /* Retention keeps the type. */
  r = (vault_request_t){
      .op = VAULT_RETAIN, .owner = owner, .arg = SECRET_BYTES, .blob = key};
  assert(key_types_call(&r, &out));
  assert(out.blob.bytes[6] == VAULT_KEY_SECP256K1);
  assert(secret_get32(out.blob.bytes) == session);

#if VAULT_TAG_SIZE
  /* The type is authenticated: relabelling breaks the record. ECB records
   * carry no tag, so there the header is not protected. */
  vault_blob_t relabelled = key;
  relabelled.bytes[6] = VAULT_KEY_NIST256P1;
  r = (vault_request_t){
      .op = VAULT_NIST_SIGN, .owner = owner, .blob = relabelled, .length = 32};
  assert(key_types_refused(&r));
#endif
  secret_owner_destroy(session);
}
