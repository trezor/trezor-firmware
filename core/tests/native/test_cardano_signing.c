/* SPDX-License-Identifier: GPL-3.0-or-later */
#undef BITCOIN_ONLY
#define BITCOIN_ONLY 0
#undef USE_CARDANO
#define USE_CARDANO 1
#define main cardano_boundary_main
#ifdef TEST_COREAPP
#include "test_vault_coreapp.c"
#elif defined(VAULT_SEAL_HW) && VAULT_SEAL_HW
#include "test_vault_saes.c"
#else
#include "test_vault.c"
#endif
#undef main

static bool cardano_request(vault_request_t *request, vault_response_t *out) {
  request->abi = VAULT_ABI;
  return vault_dispatch(1, request, out, true);
}
static uint32_t cardano_owner(uint32_t parent) {
  vault_request_t r = {.op = VAULT_OWNER_CREATE, .owner = parent};
  vault_response_t out = {0};
  assert(cardano_request(&r, &out));
  return out.value;
}
static bool cardano_sign(vault_message_request_t *request,
                         const uint8_t *message, size_t length,
                         vault_response_t *out) {
  request->abi = VAULT_ABI;
#ifdef TEST_COREAPP
  return vault_coreapp_call_message(request, message, length, out);
#else
  return vault_message_snapshot(1, request, message, length, out, true);
#endif
}
int main(void) {
  uint8_t seed[64] = {1}, secret[96] = {0};
  assert(secret_from_seed_cardano_ledger(seed, sizeof(seed), secret) == 1);
  HDNode reference = {0};
  assert(hdnode_from_secret_cardano(secret, &reference) == 1);
  uint32_t session = cardano_owner(0), request = cardano_owner(session);
  vault_request_t r = {.op = VAULT_CARDANO, .owner = request, .length = 96};
  memcpy(r.data, secret, 96);
  vault_response_t out = {0};
  assert(cardano_request(&r, &out));
  vault_blob_t node = out.blob;
  uint8_t message[1024], expected[64];
  memset(message, 0x42, sizeof(message));
  ed25519_sign_ext(message, sizeof(message), reference.private_key,
                   reference.private_key_extension, expected);
  vault_message_request_t sign = {
      .op = VAULT_ED_SIGN_EXT, .owner = request, .blob = node};
  assert(cardano_sign(&sign, message, sizeof(message), &out));
  assert(!memcmp(out.signature, expected, sizeof(expected)));
  /* Neither key half may escape the node, even as a sealed scalar/seed. */
  for (unsigned half = 0; half < 2; half++) {
    r = (vault_request_t){
        .op = VAULT_SNAPSHOT, .owner = request, .blob = node, .arg = half};
    assert(!cardano_request(&r, &out));
    assert(is_zero(&out, sizeof(out)));
  }
  /* Legacy split records and node + attacker-selected prefix are refused. */
  r = (vault_request_t){
      .op = VAULT_IMPORT_BYTES, .owner = request, .length = 32};
#ifndef TEST_COREAPP
  r.arg = VAULT_KEY_ED25519_SEED;
#endif
  memset(r.data, 1, 32);
  assert(cardano_request(&r, &out));
  vault_blob_t half = out.blob;
  sign.blob = half;
  sign.extension = half;
  assert(!cardano_sign(&sign, message, sizeof(message), &out));
  assert(is_zero(&out, sizeof(out)));
  sign.blob = node;
  assert(!cardano_sign(&sign, message, sizeof(message), &out));
  assert(is_zero(&out, sizeof(out)));
  memset(&sign.extension, 0, sizeof(sign.extension));
  const char *curves[] = {SECP256K1_NAME, NIST256P1_NAME, ED25519_NAME};
  for (size_t i = 0; i < sizeof(curves) / sizeof(curves[0]); i++) {
    r = (vault_request_t){
        .op = VAULT_FROM_SEED, .owner = request, .length = 16};
    strcpy(r.curve, curves[i]);
    memset(r.data, 1, 16);
    assert(cardano_request(&r, &out));
    sign.blob = out.blob;
    assert(!cardano_sign(&sign, message, sizeof(message), &out));
    assert(is_zero(&out, sizeof(out)));
  }
  sign.blob = node;
  sign.arg = 1;
  assert(!cardano_sign(&sign, message, sizeof(message), &out));
  sign.arg = 0;
  assert(!cardano_sign(&sign, message, 0, &out));
  assert(cardano_sign(&sign, message, sizeof(message), &out));
  assert(!memcmp(out.signature, expected, 64));
  /* Retention preserves the node and both halves, never a separable pair. */
  r = (vault_request_t){
      .op = VAULT_RETAIN, .owner = request, .blob = node, .arg = SECRET_NODE};
  assert(cardano_request(&r, &out));
  sign.blob = out.blob;
  r = (vault_request_t){.op = VAULT_OWNER_DESTROY, .owner = request};
  assert(cardano_request(&r, &out));
  sign.owner = cardano_owner(session);
  assert(cardano_sign(&sign, message, sizeof(message), &out));
  assert(!memcmp(out.signature, expected, 64));
  r = (vault_request_t){.op = VAULT_OWNER_DESTROY, .owner = session};
  assert(cardano_request(&r, &out));
  assert(!cardano_sign(&sign, message, sizeof(message), &out));
  assert(is_zero(&out, sizeof(out)));
  memzero(secret, sizeof(secret));
  memzero(&reference, sizeof(reference));
  puts(
      "Cardano bound-node signing, split-key refusal and lifetime tests "
      "passed");
  return 0;
}
