/* SPDX-License-Identifier: GPL-3.0-or-later */
/* The vault card backend against the card model, linked in-process. The
 * local vault is stubbed: only its owner table matters here. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sec/vault.h>
#include "bip32.h"
#include "bip39.h"
#include "curves.h"
#include "ecdsa.h"
#include "secp256k1.h"

#include <sec/vault_card.h>
#include "card_model.h"
#include "vault_stub.h"

#define ALL "all all all all all all all all all all all all"
#define XPUB_44_0_0                                                        \
  "xpub6BiVtCpG9fQPxnPmHXG8PhtzQdWC2Su4qWu6XW9tpWFYhxydCLJGrWBJZ5H6qTAHdP" \
  "Q7pQhtpjiYZVZARo14qHiay2fvrX996oEP42u8wZy"
#define H 0x80000000u

extern int card_model_present;
extern bool vault_card_test_unlocked;

static int failures;
#define CHECK(x)                                                   \
  do {                                                             \
    if (!(x)) {                                                    \
      fprintf(stderr, "%s:%d: FAIL %s\n", __FILE__, __LINE__, #x); \
      failures++;                                                  \
    }                                                              \
  } while (0)

static vault_card_state_t outcome;
static bool record(vault_card_state_t state, uint32_t remaining_ms) {
  (void)remaining_ms;
  outcome = state;
  return false;
}

/* --- Helpers --- */

static vault_request_t request(uint32_t op, uint32_t owner,
                               const vault_blob_t *blob) {
  vault_request_t r = {.abi = VAULT_ABI, .op = op, .owner = owner};
  if (blob) r.blob = *blob;
  return r;
}

static bool seed(uint32_t owner, const char *passphrase, vault_blob_t *out) {
  vault_request_t r = request(VAULT_SEED_STORAGE, owner, NULL);
  vault_response_t response;
  r.length = strlen(passphrase);
  memcpy(r.data, passphrase, r.length);
  bool ok = vault_call(&r, &response);
  *out = response.blob;
  return ok;
}

static bool from_seed(uint32_t owner, const vault_blob_t *seed,
                      const char *curve, vault_blob_t *out) {
  vault_request_t r = request(VAULT_FROM_SEED, owner, seed);
  vault_response_t response;
  r.arg = 1;
  strcpy(r.curve, curve);
  bool ok = vault_call(&r, &response);
  *out = response.blob;
  return ok;
}

/* In place, as HDNode.derive does. */
static bool derive(uint32_t owner, vault_blob_t *blob, uint32_t index,
                   bool public, uint32_t *fingerprint) {
  vault_request_t r = request(VAULT_DERIVE, owner, blob);
  vault_response_t response;
  r.arg = public;
  r.length = 4;
  memcpy(r.data, &index, 4);
  if (!vault_call(&r, &response)) return false;
  *blob = response.blob;
  if (fingerprint) *fingerprint = response.value;
  return true;
}

static bool public_node(uint32_t owner, vault_blob_t *blob, HDNode *node) {
  vault_request_t r = request(VAULT_PUBLIC, owner, blob);
  vault_response_t response;
  if (!vault_call(&r, &response)) return false;
  bool any = false;
  for (size_t i = 0; i < sizeof(response.blob); i++)
    any |= response.blob.bytes[i];
  if (any) *blob = response.blob;
  memset(node, 0, sizeof(*node));
  node->curve = get_curve_by_name(SECP256K1_NAME);
  node->depth = response.depth;
  node->child_num = response.child_num;
  memcpy(node->chain_code, response.chain_code, 32);
  memcpy(node->public_key, response.public_key, 33);
  node->is_public_key_set = true;
  return true;
}

static bool sign(uint32_t owner, const vault_blob_t *blob,
                 const uint8_t digest[32], uint8_t signature[65]) {
  vault_request_t r = request(VAULT_SIGN, owner, blob);
  vault_response_t response;
  r.arg = 1; /* compressed */
  r.length = 32;
  memcpy(r.data, digest, 32);
  bool ok = vault_call(&r, &response);
  memcpy(signature, response.signature, 65);
  return ok;
}

/* The same node computed directly from the mnemonic, without the card. */
static void reference(const char *passphrase, const uint32_t *path,
                      size_t depth, HDNode *node) {
  uint8_t s[64];
  mnemonic_to_seed(ALL, passphrase, s, NULL);
  hdnode_from_seed(s, 64, SECP256K1_NAME, node);
  for (size_t i = 0; i < depth; i++) hdnode_private_ckd(node, path[i]);
  hdnode_fill_public_key(node);
}

int main(void) {
  CHECK(card_model_init(ALL));
  const uint32_t account[] = {44 | H, 0 | H, 0 | H, 0, 0};
  vault_blob_t s, root, node, address;
  HDNode got, want;
  uint32_t fingerprint = 0;
  uint8_t digest[32], signature[65];
  memset(digest, 0x42, sizeof(digest));

  /* xpub m/44'/0'/0' matches the device test vector. */
  CHECK(seed(2, "", &s));
  CHECK(from_seed(2, &s, SECP256K1_NAME, &root));
  node = root;
  for (int i = 0; i < 3; i++)
    CHECK(derive(2, &node, account[i], false, &fingerprint));
  CHECK(public_node(2, &node, &got));
  char xpub[120];
  CHECK(hdnode_serialize_public(&got, fingerprint, 0x0488B21E, xpub,
                                sizeof(xpub)) > 0);
  CHECK(strcmp(xpub, XPUB_44_0_0) == 0);

  /* Public derivation runs on the phone, with no card present. */
  card_model_present = 0;
  address = node;
  CHECK(derive(2, &address, 0, true, NULL));
  CHECK(derive(2, &address, 0, true, NULL));
  CHECK(public_node(2, &address, &got));
  reference("", account, 5, &want);
  CHECK(memcmp(got.public_key, want.public_key, 33) == 0);
  /* ... and a public-only node never signs. */
  card_model_present = 1;
  CHECK(!sign(2, &address, digest, signature));

  /* Sign m/44'/0'/0'/0/0 on the card; same RFC 6979 signature as directly. */
  CHECK(derive(2, &node, 0, false, NULL));
  CHECK(derive(2, &node, 0, false, NULL));
  CHECK(sign(2, &node, digest, signature));
  uint8_t direct[64], recovery = 0;
  ecdsa_sign_digest(&secp256k1, want.private_key, digest, direct, &recovery,
                    NULL);
  CHECK(memcmp(signature + 1, direct, 64) == 0);
  CHECK(signature[0] == 27 + recovery + 4);
  CHECK(ecdsa_verify_digest(&secp256k1, want.public_key, signature + 1,
                            digest) == 0);

  /* Card removed: fails. Tapped again: the seed is reselected. */
  card_model_present = 0;
  CHECK(!sign(2, &node, digest, signature));
  card_model_present = 1;
  CHECK(sign(2, &node, digest, signature));

  /* Another card (or mnemonic) behind the same handle: refused. */
  CHECK(card_model_init(
      "abandon abandon abandon abandon abandon abandon abandon abandon "
      "abandon abandon abandon about"));
  vault_card_set_ui(record);
  CHECK(!sign(2, &node, digest, signature));
  CHECK(outcome == VAULT_CARD_FAILED);
  vault_card_set_ui(NULL);
  CHECK(card_model_init(ALL));
  CHECK(sign(2, &node, digest, signature));

  /* A passphrase is a different wallet. */
  vault_blob_t hidden;
  CHECK(seed(2, "TREZOR", &s));
  CHECK(from_seed(2, &s, SECP256K1_NAME, &hidden));
  CHECK(public_node(2, &hidden, &got));
  reference("TREZOR", account, 0, &want);
  CHECK(memcmp(got.public_key, want.public_key, 33) == 0);

  /* Owners: another session cannot use the handle; retain hands it to the
   * session, so a sibling request can. */
  CHECK(!sign(3, &node, digest, signature));
  CHECK(!sign(4, &node, digest, signature));
  vault_request_t r = request(VAULT_RETAIN, 2, &node);
  vault_response_t response;
  r.arg = SECRET_NODE;
  CHECK(vault_call(&r, &response));
  CHECK(sign(4, &response.blob, digest, signature));

  /* Locked: refused, unless the session holds a CoinJoin authorization. */
  vault_card_test_unlocked = false;
  CHECK(!sign(2, &node, digest, signature));
  owners[1].authorized = 1;
  CHECK(sign(2, &node, digest, signature));
  vault_blob_t refused;
  CHECK(!seed(2, "", &refused));
  owners[1].authorized = 0;
  vault_card_test_unlocked = true;

  /* Keys never leave the card. */
  r = request(VAULT_SNAPSHOT, 2, &node);
  CHECK(!vault_call(&r, &response));

  /* Everything else goes to the local vault. */
  r = request(VAULT_IMPORT_BYTES, 2, NULL);
  CHECK(vault_call(&r, &response) && local_calls == 1);

  /* Lock or wipe forgets every seed handle. */
  vault_card_wipe();
  CHECK(!sign(2, &node, digest, signature));
  CHECK(!from_seed(2, &s, SECP256K1_NAME, &root));

  if (failures) {
    fprintf(stderr, "%d failures\n", failures);
    return 1;
  }
  printf("vault card: all checks passed\n");
  return 0;
}
