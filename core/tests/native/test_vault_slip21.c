/* SPDX-License-Identifier: GPL-3.0-or-later */
#define main sealing_test_main
#include "test_vault_sealing.c"
#undef main
#include "../../embed/sec/vault/vault.c"
static bool call(uintptr_t caller, vault_request_t *r, vault_response_t *out) {
  r->abi = VAULT_ABI;
  return vault_dispatch(caller, r, out, true);
}
static uint32_t owner_create(uintptr_t caller, uint32_t parent) {
  vault_request_t r = {.op = VAULT_OWNER_CREATE, .owner = parent};
  vault_response_t out = {0};
  return call(caller, &r, &out) ? out.value : 0;
}
#include "hmac.h"
static uintptr_t slip21_caller = 1;
bool vault_call(const vault_request_t *r, vault_response_t *out) {
  return vault_dispatch(slip21_caller, r, out, true);
}
#include "../../embed/upymod/modtrezorcrypto/vault_slip21.h"
static bool derived_call(uintptr_t caller, vault_request_t *r,
                         vault_response_t *out) {
  slip21_caller = caller;
  r->abi = VAULT_ABI;
  if (r->op == VAULT_SLIP21 || r->op == VAULT_HMAC_TAG)
    return vault_slip21_call(r, out);
  return call(caller, r, out);
}
#define call derived_call
/* Reference SLIP-0021 node along length-prefixed labels. */
static void slip21_reference(const uint8_t *seed, size_t seed_len,
                             const uint8_t *labels, size_t length,
                             uint8_t node[64]) {
  static const char salt[] = "Symmetric key seed";
  hmac_sha512((const uint8_t *)salt, sizeof(salt) - 1, seed, seed_len, node);
  for (size_t i = 0; i < length; i += 1 + labels[i]) {
    uint8_t message[256] = {0};
    memcpy(message + 1, labels + i + 1, labels[i]);
    hmac_sha512(node, 32, message, 1 + labels[i], node);
  }
}

static bool slip21_call(uint32_t owner, const vault_blob_t *source,
                        uint32_t arg, const char *labels, size_t length,
                        vault_response_t *out) {
  vault_request_t r = {.op = VAULT_SLIP21,
                       .owner = owner,
                       .blob = *source,
                       .arg = arg,
                       .length = length};
  memcpy(r.data, labels, length);
  memset(out, 0, sizeof(*out));
  return call(1, &r, out);
}

static void slip21_vectors(void) {
  uint32_t owner = owner_create(1, owner_create(1, 0));
  uint8_t seed[64];
  for (int i = 0; i < 64; i++) seed[i] = i;
  vault_request_t r = {
      .op = VAULT_IMPORT_BYTES, .owner = owner, .length = sizeof(seed)};
  memcpy(r.data, seed, sizeof(seed));
  vault_response_t out = {0};
  assert(call(1, &r, &out));
  vault_blob_t root = out.blob;

  static const char auth[] = "\011SLIP-0021\022Authentication key";
  static const char evolu[] = "\006TREZOR\005Evolu";
  static const char index[] = "\006TREZOR\013Evolu Index\0017";
  uint8_t expected[64], tag[32];

  /* Key output, from the seed and stepwise from a sealed node. */
  slip21_reference(seed, sizeof(seed), (const uint8_t *)auth, sizeof(auth) - 1,
                   expected);
  hmac_sha256(expected + 32, 32, (const uint8_t *)"m", 1, tag);
  assert(slip21_call(owner, &root, VAULT_SLIP21_ROOT, auth, 10, &out));
  vault_blob_t node = out.blob;
  assert(slip21_call(owner, &node, VAULT_SLIP21_KEY, auth + 10,
                     sizeof(auth) - 11, &out));
  vault_blob_t key = out.blob;
  assert(slip21_call(owner, &root, VAULT_SLIP21_ROOT | VAULT_SLIP21_KEY, auth,
                     sizeof(auth) - 1, &out));
  vault_blob_t direct = out.blob;
  const vault_blob_t *keys[] = {&key, &direct};
  for (size_t i = 0; i < 2; i++) {
    r = (vault_request_t){.op = VAULT_HMAC_TAG,
                          .owner = owner,
                          .blob = *keys[i],
                          .arg = 256,
                          .length = 1};
    r.data[0] = 'm';
    assert(call(1, &r, &out));
    assert(!memcmp(out.signature, tag, 32));
  }

  /* Export: only from a seed and only under the Evolu namespace. */
  slip21_reference(seed, sizeof(seed), (const uint8_t *)evolu,
                   sizeof(evolu) - 1, expected);
  assert(slip21_call(owner, &root, VAULT_SLIP21_ROOT | VAULT_SLIP21_EXPORT,
                     evolu, sizeof(evolu) - 1, &out));
  assert(!memcmp(out.signature, expected, 64));
  slip21_reference(seed, sizeof(seed), (const uint8_t *)index,
                   sizeof(index) - 1, expected);
  assert(slip21_call(owner, &root, VAULT_SLIP21_ROOT | VAULT_SLIP21_EXPORT,
                     index, sizeof(index) - 1, &out));
  assert(!memcmp(out.signature, expected, 64));
  assert(!slip21_call(owner, &root, VAULT_SLIP21_ROOT | VAULT_SLIP21_EXPORT,
                      auth, sizeof(auth) - 1, &out));
  assert(!slip21_call(owner, &root, VAULT_SLIP21_ROOT | VAULT_SLIP21_EXPORT,
                      index, sizeof(index) - 3, &out)); /* no index label */
  assert(!slip21_call(owner, &root, VAULT_SLIP21_ROOT | VAULT_SLIP21_EXPORT,
                      "\006TREZOR\005Evolu\000", 14, &out));
  assert(!slip21_call(owner, &node, VAULT_SLIP21_EXPORT, "", 0, &out));
  assert(is_zero(&out, sizeof(out)));

  /* Malformed requests. */
  assert(!slip21_call(owner, &key, VAULT_SLIP21_NODE, "", 0, &out)); /* 32 */
  assert(!slip21_call(owner, &root, VAULT_SLIP21_ROOT | 8, "", 0, &out));
  assert(!slip21_call(owner, &root, VAULT_SLIP21_ROOT, "\005ab", 3, &out));
  assert(
      !slip21_call(owner_create(1, 0), &root, VAULT_SLIP21_ROOT, "", 0, &out));
  memzero(expected, sizeof(expected));
}

int main(void) {
  slip21_vectors();
  assert(is_zero(secret_scratch, sizeof(secret_scratch)));
  puts("sealed SLIP-0021 policy and ownership tests passed");
}
