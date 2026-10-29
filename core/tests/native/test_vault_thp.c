/* SPDX-License-Identifier: GPL-3.0-or-later */
#define main vault_boundary_main
#if defined(VAULT_SEAL_HW) && VAULT_SEAL_HW
#include "test_vault_saes.c"
#else
#include "test_vault.c"
#endif
#undef main
static void unhex(const char *hex, uint8_t *out, size_t length) {
  for (size_t i = 0; i < length; i++) {
    unsigned byte = 0;
    assert(sscanf(hex + 2 * i, "%2x", &byte) == 1);
    out[i] = byte;
  }
}
static uint32_t thp_owner_create(void) {
  vault_request_t r = {.op = VAULT_OWNER_CREATE};
  vault_response_t out = {0};
  assert(call(1, &r, &out));
  return out.value;
}
int main(void) {
  const char *private_keys[] = {
      "9c762377b24ffb1a022b20d2f78b2ff5ee212e9011f1e3f6df75f6c65d559023",
      "bdf1b57c1e4c46d8f269a5c50f9f7e1bd90f8ed4ad6909be1117f80127b2daf3",
      "7efb2325d9c027cb58dea80cd98a05ca4f89134290dc57cb172f688d4078bc97"};
  const char *public_keys[] = {
      "cc6436c3681de6602d80e782e3e0a023e59e7fbd20d77ab8806ed15e80e77843",
      "4288cccef083658378cbf154a86ffd3376325d733304d2850076020be6e23974",
      "61ab2fc9e91180a1c0cf004fceed95be08a141585a17f36f9ec0e8679578a11e"};
  for (size_t vector = 0; vector < 3; vector++) {
    vault_wipe();
    uint32_t owner = thp_owner_create();
    vault_response_t out = {0};
    vault_request_t r = {.op = VAULT_IMPORT_BYTES,
                         .arg = VAULT_KEY_THP_DEVICE,
                         .owner = owner,
                         .length = 16};
    for (size_t i = 0; i < 16; i++)
      r.data[i] = vector == 0 ? 0 : vector == 1 ? i : 255;
    assert(call(1, &r, &out));
    r = (vault_request_t){
        .op = VAULT_THP_DERIVE, .owner = owner, .blob = out.blob};
    assert(call(1, &r, &out));
    vault_blob_t key = out.blob;
    r = (vault_request_t){.op = VAULT_THP_PUBLIC, .owner = owner, .blob = key};
    uint8_t expected[32];
    unhex(public_keys[vector], expected, 32);
    assert(call(1, &r, &out));
    assert(memcmp(out.signature, expected, 32) == 0);
    r.op = VAULT_THP_DH;
    r.length = 32;
    uint8_t peer_key[32] = {0x55}, private_key[32];
    curve25519_scalarmult_basepoint(r.data, peer_key);
    unhex(private_keys[vector], private_key, 32);
    curve25519_scalarmult(expected, private_key, r.data);
    assert(call(1, &r, &out));
    assert(memcmp(out.signature, expected, 32) == 0);
    memset(r.data, 0, 32);
    assert(!call(1, &r, &out));
    assert(is_zero(&out, sizeof(out)));
    r.op = VAULT_THP_PUBLIC;
    r.length = 0;
    assert(!call(2, &r, &out));
    assert(is_zero(&out, sizeof(out)));
    assert(!vault_dispatch(1, &r, &out, false));
    assert(is_zero(&out, sizeof(out)));
    r.blob.bytes[VAULT_HEADER_SIZE] ^= 1;
    assert(!call(1, &r, &out));
    assert(is_zero(&out, sizeof(out)));
    r.blob = key;
    secret_owner_destroy(owner);
    assert(!call(1, &r, &out));
    assert(is_zero(&out, sizeof(out)));
    memzero(private_key, sizeof(private_key));
    assert(!secret_busy && vault_seal_ready());
  }
  assert(!vault_storage_key_allowed(0x0117));
  assert(!vault_storage_key_allowed(0xc117));
  puts("THP vault identity and DH checks passed");
}
