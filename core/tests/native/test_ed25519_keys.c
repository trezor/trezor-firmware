/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include "memzero.h"
static void observed_memzero(void *out, size_t length);
#define memzero observed_memzero
#define main vault_boundary_main
#include "test_vault.c"
#undef main
#undef memzero

static uint8_t *source;
static const uint8_t *observed_snapshot;
static vault_message_request_t *source_request;
static unsigned snapshot_erases, request_erases, signs;
static void observed_memzero(void *out, size_t length) {
  memzero(out, length);
  if (out == observed_snapshot) {
    assert(length == 256 || length == VAULT_ED25519_MAX_MESSAGE);
    assert(is_zero(out, length));
    observed_snapshot = NULL;
    snapshot_erases++;
  }
  if (length == sizeof(vault_message_request_t)) {
    assert(is_zero(out, length));
    request_erases++;
  }
}
void __real_ed25519_sign(const unsigned char *, size_t,
                         const ed25519_secret_key, ed25519_signature);
void __real_ed25519_sign_keccak(const unsigned char *, size_t,
                                const ed25519_secret_key, ed25519_signature);
void __wrap_ed25519_sign(const unsigned char *message, size_t length,
                         const ed25519_secret_key key, ed25519_signature sig) {
  if (source) {
    observed_snapshot = message;
    assert(message != source);
    source[0] ^=
        1; /* an adversarial caller cannot change the kernel snapshot */
    memset(source_request, 0xff, sizeof(*source_request));
    signs++;
  }
  __real_ed25519_sign(message, length, key, sig);
}
void __wrap_ed25519_sign_keccak(const unsigned char *message, size_t length,
                                const ed25519_secret_key key,
                                ed25519_signature sig) {
  if (source) {
    observed_snapshot = message;
    assert(message != source);
    source[0] ^= 1;
    memset(source_request, 0xff, sizeof(*source_request));
    signs++;
  }
  __real_ed25519_sign_keccak(message, length, key, sig);
}

int main(void) {
  uint32_t owner = owner_create(1, 0);
  vault_request_t r = {.op = VAULT_FROM_SEED, .owner = owner, .length = 16};
  vault_response_t out = {0};
  strcpy(r.curve, ED25519_NAME);
  memset(r.data, 0x42, r.length);
  HDNode expected = {0};
  assert(hdnode_from_seed(r.data, r.length, ED25519_NAME, &expected));
  assert(call(1, &r, &out));
  vault_blob_t node = out.blob;
  r = (vault_request_t){
      .op = VAULT_DERIVE, .owner = owner, .blob = node, .length = 4};
  uint32_t index = 0x80002726;
  memcpy(r.data, &index, 4);
  assert(hdnode_private_ckd(&expected, index));
  assert(call(1, &r, &out));
  node = out.blob;
  /* A non-hardened derivation must fail, leaving the original blob usable. */
  memset(r.data, 0, 4);
  r.blob = node;
  assert(!call(1, &r, &out));
  r = (vault_request_t){.op = VAULT_PUBLIC, .owner = owner, .blob = node};
  assert(call(1, &r, &out));
  assert(!hdnode_fill_public_key(&expected));
  assert(!memcmp(expected.public_key, out.public_key, 33));
  r.op = VAULT_SNAPSHOT;
  assert(call(1, &r, &out));
  vault_blob_t key = out.blob;
  r = (vault_request_t){.op = VAULT_ED_PUBLIC, .owner = owner, .blob = key};
  assert(call(1, &r, &out));
  assert(!memcmp(expected.public_key + 1, out.signature, 32));
  r.op = VAULT_ED_SIGN;
  r.abi = VAULT_ABI;
  vault_message_request_t mr = {
      .abi = r.abi, .op = r.op, .owner = r.owner, .blob = r.blob};
  uint8_t message[VAULT_ED25519_MAX_MESSAGE + 1], signature[64];
  memset(message, 0x37, sizeof(message));
  const size_t lengths[] = {
      1, 255, 256, 257, 1232, 1536, VAULT_ED25519_MAX_MESSAGE};
  for (size_t variant = 0; variant < 2; variant++) {
    mr.arg = variant;
    for (size_t i = 0; i < sizeof(lengths) / sizeof(*lengths); i++) {
      size_t length = lengths[i];
      if (variant)
        __real_ed25519_sign_keccak(message, length, expected.private_key,
                                   signature);
      else
        __real_ed25519_sign(message, length, expected.private_key, signature);
      source = message;
      source_request = &mr;
      vault_message_request_t original = mr;
      assert(vault_message_snapshot(1, &mr, message, length, &out, true));
      source = NULL;
      source_request = NULL;
      assert(mr.op == UINT32_MAX);
      mr = original;
      message[0] ^= 1;
      assert(!memcmp(signature, out.signature, 64));
      uint8_t public_key[32];
      if (variant) {
        ed25519_publickey_keccak(expected.private_key, public_key);
        assert(ed25519_sign_open_keccak(message, length, public_key,
                                        out.signature) == 0);
        out.signature[0] ^= 1;
        assert(ed25519_sign_open_keccak(message, length, public_key,
                                        out.signature) != 0);
      } else {
        ed25519_publickey(expected.private_key, public_key);
        assert(ed25519_sign_open(message, length, public_key, out.signature) ==
               0);
        out.signature[0] ^= 1;
        assert(ed25519_sign_open(message, length, public_key, out.signature) !=
               0);
      }
      assert(is_zero(secret_scratch, sizeof(secret_scratch)));
    }
  }
  assert(signs == 14);
  assert(snapshot_erases == signs);
  assert(request_erases == signs);
  assert(!vault_message_snapshot(1, &mr, message, 0, &out, true));
  assert(!vault_message_snapshot(1, &mr, message, sizeof(message), &out, true));
  assert(!vault_message_snapshot(1, &mr, NULL, 1, &out, true));
  assert(!call(1, &r, &out)); /* no message on an ordinary RPC */
  mr.length = 1;
  assert(!vault_message_snapshot(1, &mr, message, 1, &out, true));
  mr.length = 0;
  mr.op = VAULT_SIGN;
  assert(!vault_message_snapshot(1, &mr, message, 1, &out, true));
  mr.op = VAULT_ED_SIGN;
  assert(!vault_message_snapshot(2, &mr, message, 1, &out, true));
  assert(!vault_message_snapshot(1, &mr, message, 1, &out, false));
  mr.arg = 2;
  assert(!vault_message_snapshot(1, &mr, message, 1, &out, true));
  mr.arg = 0;
  mr.abi--;
  assert(!vault_message_snapshot(1, &mr, message, 1, &out, true));
  mr.abi++;
  secret_owner_destroy(owner);
  assert(!vault_message_snapshot(1, &mr, message, 1, &out, true));
  assert(is_zero(&out, sizeof(out)));
  puts(
      "protected Ed25519 derivation/signing and message snapshot tests passed");
}
