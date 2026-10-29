/* SPDX-License-Identifier: GPL-3.0-or-later */
#define main vault_boundary_main
#include "test_vault.c"
#undef main

int main(void) {
  uint32_t owner = owner_create(1, 0);
  vault_request_t r = {.op = VAULT_FROM_SEED, .owner = owner, .length = 16};
  vault_response_t out = {0};
  strcpy(r.curve, NIST256P1_NAME);
  memset(r.data, 0x42, r.length);
  HDNode expected = {0};
  assert(hdnode_from_seed(r.data, r.length, NIST256P1_NAME, &expected));
  assert(call(1, &r, &out));
  vault_blob_t node = out.blob;
  r = (vault_request_t){
      .op = VAULT_DERIVE, .owner = owner, .blob = node, .length = 4};
  uint32_t index = 0x80553246;
  memcpy(r.data, &index, sizeof(index));
  assert(hdnode_private_ckd(&expected, index));
  assert(call(1, &r, &out));
  node = out.blob;
  r = (vault_request_t){.op = VAULT_SNAPSHOT, .owner = owner, .blob = node};
  assert(call(1, &r, &out));
  vault_blob_t key = out.blob;
  r = (vault_request_t){.op = VAULT_NIST_PUBLIC, .owner = owner, .blob = key};
  assert(call(1, &r, &out));
  uint8_t public_key[65];
  assert(!ecdsa_get_public_key65(&nist256p1, expected.private_key, public_key));
  assert(!memcmp(public_key, out.signature, 65));
  r = (vault_request_t){
      .op = VAULT_NIST_SIGN, .owner = owner, .blob = key, .length = 32};
  memset(r.data, 0x5a, r.length);
  assert(call(1, &r, &out));
  uint8_t signature[64], recovery;
  assert(!ecdsa_sign_digest(&nist256p1, expected.private_key, r.data, signature,
                            &recovery, NULL));
  assert(!memcmp(signature, out.signature + 1, 64));
  assert(out.signature[0] == 27 + recovery);
  assert(
      !ecdsa_verify_digest(&nist256p1, public_key, out.signature + 1, r.data));
  r.op = VAULT_HMAC_TAG;
  r.length = 64;
  for (size_t i = 0; i < r.length; i++) r.data[i] = i;
  for (size_t bits = 256; bits <= 512; bits += 256) {
    r.arg = bits;
    assert(call(1, &r, &out));
    uint8_t tag[64];
    if (bits == 256)
      hmac_sha256(expected.private_key, 32, r.data, r.length, tag);
    else
      hmac_sha512(expected.private_key, 32, r.data, r.length, tag);
    assert(!memcmp(tag, out.signature, bits / 8));
  }
  r.arg = 42;
  assert(!call(1, &r, &out));
  assert(is_zero(&out, sizeof(out)));
  r.arg = 256;
  assert(!vault_dispatch(1, &r, &out, false));
  secret_owner_destroy(owner);
  assert(!call(1, &r, &out));
  assert(is_zero(secret_scratch, sizeof(secret_scratch)));
  assert(!zkp_context_is_initialized());
  puts("protected FIDO P-256 key tests passed");
}
