/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdio.h>
#define VAULT_TEST 1
#include "../../embed/sec/vault/seal.c"
#include "../../embed/sec/vault/vault.c"
#include "zkp_context.h"
/* Test-only blinding entropy. Never linked into firmware. */
void rng_fill_buffer(void *p, size_t n) { memset(p, 0x42, n); }
void random_buffer(uint8_t *p, size_t n) { rng_fill_buffer(p, n); }

/* Test-injected AES and entropy for seal.c (see VAULT_TEST there). */
static uint8_t test_kek[32];
static int fail_after = -1;
bool vault_wrap_block(bool encrypt, const uint8_t in[16], uint8_t out[16]) {
  if (fail_after == 0) return false;
  if (fail_after > 0) fail_after--;
  bool ok;
  if (encrypt) {
    aes_encrypt_ctx ctx = {0};
    ok = aes_encrypt_key256(test_kek, &ctx) == 0 &&
         aes_encrypt(in, out, &ctx) == 0;
    memzero(&ctx, sizeof(ctx));
  } else {
    aes_decrypt_ctx ctx = {0};
    ok = aes_decrypt_key256(test_kek, &ctx) == 0 &&
         aes_decrypt(in, out, &ctx) == 0;
    memzero(&ctx, sizeof(ctx));
  }
  return ok;
}
void vault_random(void *dest, size_t len) {
  static uint8_t sequence;
  memset(dest, ++sequence, len);
}

static bool call(uintptr_t caller, vault_request_t *r, vault_response_t *out) {
  r->abi = VAULT_ABI;
  return vault_dispatch(caller, r, out, true);
}
static uint32_t owner_create(uintptr_t caller, uint32_t parent) {
  vault_response_t out = {0};
  vault_request_t r = {.op = VAULT_OWNER_CREATE, .owner = parent};
  return call(caller, &r, &out) ? out.value : 0;
}
static bool sign(uint32_t owner, const vault_blob_t *blob, uint8_t sig[65]) {
  vault_response_t out = {0};
  vault_request_t r = {
      .op = VAULT_SIGN, .owner = owner, .blob = *blob, .length = 32, .arg = 1};
  memset(r.data, 0x42, 32);
  bool ok = call(1, &r, &out);
  if (ok && sig) memcpy(sig, out.signature, 65);
  return ok;
}
static bool is_zero(const void *p, size_t len) {
  for (size_t i = 0; i < len; i++)
    if (((const uint8_t *)p)[i]) return false;
  return true;
}
static void locked_authorization(void) {
  secret_revoke_all();
  uint32_t session = owner_create(1, 0), request = owner_create(1, session);
  vault_request_t r = {
      .op = VAULT_IMPORT_BYTES, .owner = request, .length = 32};
  memset(r.data, 1, 32);
  vault_response_t out = {0};
  assert(call(1, &r, &out));
  vault_blob_t key = out.blob;
  r = (vault_request_t){.abi = VAULT_ABI,
                        .op = VAULT_SIGN,
                        .owner = request,
                        .blob = key,
                        .length = 32,
                        .arg = 1};
  memset(r.data, 0x42, 32);
  assert(vault_dispatch(1, &r, &out, true));
  assert(!vault_dispatch(1, &r, &out, false));
  vault_request_t grant = {.abi = VAULT_ABI,
                           .op = VAULT_AUTHORIZE_LOCKED,
                           .owner = request,
                           .arg = 1};
  assert(!vault_dispatch(1, &grant, &out, false));
  assert(vault_dispatch(1, &grant, &out, true));
  assert(
      vault_dispatch(1, &grant, &out, false)); /* preserve an existing grant */
  assert(!vault_dispatch(1, &r, &out, false));
  grant.arg = 2;
  assert(vault_dispatch(1, &grant, &out, false));
  assert(vault_dispatch(1, &r, &out, false));
  vault_request_t storage = {
      .abi = VAULT_ABI, .op = VAULT_SEED_STORAGE, .owner = request};
  assert(!vault_dispatch(1, &storage, &out, false));
  grant.arg = 0;
  assert(vault_dispatch(1, &grant, &out, false));
  /* Consuming the last round must not invalidate its in-flight signature. */
  assert(vault_dispatch(1, &r, &out, false));
  secret_owner_destroy(request);
  request = owner_create(1, session);
  r.owner = request;
  grant.owner = request;
  grant.arg = 2;
  assert(!vault_dispatch(1, &grant, &out, false));
  assert(!vault_dispatch(1, &r, &out, false));
  secret_owner_destroy(session);
}

static int test_ethereum_canonical(uint8_t v, uint8_t signature[64]) {
  (void)signature;
  return (v & 2) == 0;
}
static int test_eos_canonical(uint8_t v, uint8_t signature[64]) {
  (void)v;
  return !(signature[0] & 0x80) &&
         !(signature[0] == 0 && !(signature[1] & 0x80)) &&
         !(signature[32] & 0x80) &&
         !(signature[32] == 0 && !(signature[33] & 0x80));
}
/* Canonical vault signatures equal trezor-crypto's for the same key. */
static void canonical_vectors(uint32_t owner, const vault_blob_t *key,
                              const uint8_t private_key[32]) {
  int (*const forms[])(uint8_t, uint8_t[64]) = {NULL, test_ethereum_canonical,
                                                test_eos_canonical};
  for (uint32_t canonical = 0; canonical < 3; canonical++) {
    for (uint32_t compressed = 0; compressed < 2; compressed++) {
      for (uint8_t d = 1; d <= 16; d++) { /* a zero digest is refused */
        vault_request_t r = {.op = VAULT_SIGN,
                             .owner = owner,
                             .blob = *key,
                             .length = 32,
                             .arg = compressed | canonical << 1};
        memset(r.data, d, 32);
        vault_response_t out = {0};
        assert(call(1, &r, &out));
        uint8_t expected[65] = {0}, recovery = 0;
        /* The vault keeps no ZKP context between calls; neither does this. */
        assert(zkp_context_init() == 0);
        assert(ecdsa_sign_digest(&secp256k1, private_key, r.data, expected + 1,
                                 &recovery, forms[canonical]) == 0);
        zkp_context_destroy();
        expected[0] = 27 + recovery + 4 * compressed;
        assert(!memcmp(out.signature, expected, 65));
        if (canonical)
          assert(forms[canonical](out.signature[0] - 27 - 4 * compressed,
                                  out.signature + 1));
      }
    }
  }
  vault_request_t r = {.op = VAULT_SIGN,
                       .owner = owner,
                       .blob = *key,
                       .length = 32,
                       .arg = 1 | 3 << 1}; /* unknown selector */
  vault_response_t out = {0};
  assert(!call(1, &r, &out) && is_zero(&out, sizeof(out)));
}

static void fingerprint_vectors(void) {
#if USE_BIP32_VAULT
  /* Bitcoin-only archives omit the Cardano name symbol; still check the name.
   */
  const char *excluded[] = {SECP256K1_DECRED_NAME, SECP256K1_GROESTL_NAME,
                            SECP256K1_SMART_NAME,  ED25519_SHA3_NAME,
                            ED25519_KECCAK_NAME,   "ed25519 cardano seed",
                            CURVE25519_NAME};
  for (size_t i = 0; i < sizeof(excluded) / sizeof(*excluded); i++)
    assert(get_curve_by_name(excluded[i]) == NULL);
#endif
  const char *curves[] = {SECP256K1_NAME, NIST256P1_NAME, ED25519_NAME};
  const uint8_t seed[16] = {1, 2, 3};
  for (size_t c = 0; c < sizeof(curves) / sizeof(*curves); c++) {
    uint32_t owner = owner_create(1, 0);
    vault_request_t r = {
        .op = VAULT_FROM_SEED, .owner = owner, .length = sizeof(seed)};
    strcpy(r.curve, curves[c]);
    memcpy(r.data, seed, sizeof(seed));
    vault_response_t out = {0};
    assert(call(1, &r, &out));
    HDNode expected = {0};
    assert(hdnode_from_seed(seed, sizeof(seed), curves[c], &expected));
    for (uint32_t step = 0; step < 3; step++) {
      vault_blob_t parent = out.blob;
      uint32_t index = 0x80000000 | step;
      assert(zkp_context_init() == 0);
      uint32_t fingerprint = hdnode_fingerprint(&expected);
      assert(hdnode_private_ckd(&expected, index));
      zkp_context_destroy();
      r = (vault_request_t){
          .op = VAULT_DERIVE, .owner = owner, .blob = parent, .length = 4};
      memcpy(r.data, &index, sizeof(index));
      assert(call(1, &r, &out));
      assert(out.value == fingerprint);
    }
    memzero(&expected, sizeof(expected));
    secret_owner_destroy(owner);
  }
  /* Unsupported hashing must fail explicitly when adding new curves. */
  HDNode unsupported = {0};
  uint32_t fingerprint = 0;
  assert(!vault_fingerprint(&unsupported, &fingerprint));
}

static void node_import_vectors(void) {
  const char *curves[] = {SECP256K1_NAME, NIST256P1_NAME, ED25519_NAME};
  uint32_t owner = owner_create(1, 0);
  for (size_t c = 0; c < sizeof(curves) / sizeof(*curves); c++) {
    HDNode expected = {0};
    uint8_t private_key[32] = {0};
    private_key[31] = c == 2 ? 0 : 1; /* Zero is a valid Ed25519 seed. */
    assert(hdnode_from_xprv(0, 0, (uint8_t[32]){0}, private_key, curves[c],
                            &expected));
    assert(zkp_context_init() == 0);
    assert(hdnode_fill_public_key(&expected) == 0);
    zkp_context_destroy();
    vault_request_t r = {.op = VAULT_IMPORT_NODE, .owner = owner, .length = 98};
    strcpy(r.curve, curves[c]);
    memcpy(r.data + 32, private_key, 32);
    memcpy(r.data + 64, expected.public_key, 33);
    r.data[97] = 3;
    vault_response_t out = {0};
    assert(call(1, &r, &out));
    vault_blob_t node = out.blob;
    /* A different, valid public key must not be accepted as this key's cache.
     */
    expected.private_key[31]++;
    expected.is_public_key_set = false;
    assert(zkp_context_init() == 0);
    assert(hdnode_fill_public_key(&expected) == 0);
    zkp_context_destroy();
    memcpy(r.data + 64, expected.public_key, 33);
    assert(!call(1, &r, &out));
    assert(is_zero(&out, sizeof(out)));
    r = (vault_request_t){.op = VAULT_SNAPSHOT, .owner = owner, .blob = node};
    assert(call(1, &r, &out));
    r = (vault_request_t){
        .op = VAULT_DERIVE, .owner = owner, .blob = node, .length = 4};
    uint32_t index = 0x80000000;
    memcpy(r.data, &index, sizeof(index));
    assert(call(1, &r, &out));
    memzero(&expected, sizeof(expected));
  }
  secret_owner_destroy(owner);
}

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

static void schnorr_vectors(void) {
  bool was_initialized = zkp_context_is_initialized();
  if (was_initialized) zkp_context_destroy();
  uint32_t owner = owner_create(1, 0);
  vault_request_t r = {.op = VAULT_IMPORT_BYTES, .owner = owner, .length = 32};
  r.data[31] = 3;
  vault_response_t out = {0};
  assert(call(1, &r, &out));
  vault_blob_t key = out.blob;
  r = (vault_request_t){
      .op = VAULT_SCHNORR_PUBLIC, .owner = owner, .blob = key};
  assert(call(1, &r, &out));
  const uint8_t expected[32] = {0xf9, 0x30, 0x8a, 0x01, 0x92, 0x58, 0xc3, 0x10,
                                0x49, 0x34, 0x4f, 0x85, 0xf8, 0x9d, 0x52, 0x29,
                                0xb5, 0x31, 0xc8, 0x45, 0x83, 0x6f, 0x99, 0xb0,
                                0x86, 0x01, 0xf1, 0x13, 0xbc, 0xe0, 0x36, 0xf9};
  assert(!memcmp(out.signature, expected, 32));
  assert(!zkp_context_is_initialized());
  r.op = VAULT_SCHNORR_SIGN;
  r.length = 32;
  memset(r.data, 0x42, 32);
  assert(call(1, &r, &out));
  assert(!zkp_context_is_initialized());
  uint8_t sig[64];
  memcpy(sig, out.signature, 64);
  assert(zkp_context_init() == 0);
  assert(zkp_bip340_verify_digest(expected, sig, r.data) == 0);
  zkp_context_destroy();
  r.op = VAULT_SCHNORR_TWEAK;
  r.length = 0;
  assert(call(1, &r, &out));
  vault_blob_t tweaked = out.blob;
  assert(!zkp_context_is_initialized());
  r.op = VAULT_SCHNORR_PUBLIC;
  r.blob = tweaked;
  assert(call(1, &r, &out));
  uint8_t tweaked_public[32];
  memcpy(tweaked_public, out.signature, 32);
  assert(zkp_context_init() == 0);
  uint8_t expected_tweaked[32];
  assert(zkp_bip340_tweak_public_key(expected, NULL, expected_tweaked) == 0);
  assert(!memcmp(expected_tweaked, tweaked_public, 32));
  zkp_context_destroy();
  r.op = VAULT_SCHNORR_GENERATE;
  assert(call(1, &r, &out));
  assert(!zkp_context_is_initialized());
  secret_owner_destroy(owner);
  r.op = VAULT_SCHNORR_PUBLIC;
  assert(!call(1, &r, &out));
  if (was_initialized) assert(zkp_context_init() == 0);
}

int main(void) {
  /* Match hardware: coreapp and kernel do not share a ZKP context. */
  assert(!zkp_context_is_initialized());
  vault_response_t out = {0};
  uint32_t session = owner_create(1, 0);
  assert(session);
  assert(!owner_create(2, session)); /* another caller's session */
  uint32_t request = owner_create(1, session);
  uint32_t sibling = owner_create(1, session);
  uint32_t other = owner_create(1, owner_create(1, 0));
  assert(request && sibling && other);
  assert(!owner_create(1, request)); /* two levels only */

  vault_request_t r = {.op = VAULT_FROM_SEED, .owner = request, .length = 16};
  strcpy(r.curve, "secp256k1");
  for (int i = 0; i < 16; i++) r.data[i] = i;
  assert(call(1, &r, &out));
  vault_blob_t node = out.blob;
  /* The kernel keeps no per-secret state: only owners and the key. */
  assert(is_zero(secret_scratch, sizeof(secret_scratch)));
  assert(!is_zero(&node, sizeof(node)));

  r = (vault_request_t){.op = VAULT_SNAPSHOT, .owner = request, .blob = node};
  assert(call(1, &r, &out));
  vault_blob_t key = out.blob;
  uint8_t signature[65], again[65];
  assert(sign(request, &key, signature));
  assert(sign(request, &node, again)); /* sign from the node in place */
  assert(!memcmp(signature, again, 65));
  {
    uint8_t seed[16];
    for (int i = 0; i < 16; i++) seed[i] = i;
    HDNode plain = {0};
    assert(hdnode_from_seed(seed, 16, "secp256k1", &plain));
    canonical_vectors(request, &key, plain.private_key);
    canonical_vectors(request, &node, plain.private_key);
    memzero(&plain, sizeof(plain));
  }
  r = (vault_request_t){
      .op = VAULT_SIGN, .owner = request, .blob = key, .length = 32};
  memset(r.data, 0x42, 32);
  r.abi = VAULT_ABI;
  assert(!vault_dispatch(2, &r, &out, true));  /* wrong caller */
  assert(!vault_dispatch(1, &r, &out, false)); /* locked */
  r.abi++;
  assert(!vault_dispatch(1, &r, &out, true));
  r.abi = VAULT_ABI;
  r.length = VAULT_DATA_SIZE + 1;
  assert(!vault_dispatch(1, &r, &out, true));

  /* Ownership: siblings and other sessions cannot open a request's blob. */
  assert(!sign(sibling, &key, NULL));
  assert(!sign(other, &key, NULL));
  assert(!sign(session, &key, NULL)); /* parents do not reach into requests */

  /* Derive returns a new blob; blobs are values, the old one is unchanged. */
  r = (vault_request_t){
      .op = VAULT_DERIVE, .owner = request, .blob = node, .length = 4};
  r.data[0] = 1;
  assert(call(1, &r, &out));
  vault_blob_t child = out.blob;
  assert(memcmp(&child, &node, sizeof(node)));
  assert(sign(request, &child, again));
  assert(memcmp(signature, again, 65));
  assert(sign(request, &node, again));
  assert(!memcmp(signature, again, 65));
  assert(sign(request, &key, again)); /* snapshot independent of the node */
  assert(!memcmp(signature, again, 65));

  /* Public info; a public-only node has no private key to sign with. */
  r = (vault_request_t){.op = VAULT_PUBLIC, .owner = request, .blob = child};
  assert(call(1, &r, &out));
  assert(!is_zero(&out.blob, sizeof(out.blob))); /* carries the computed key */
  vault_response_t pub = out;
  r = (vault_request_t){.op = VAULT_PUBLIC, .owner = request, .blob = pub.blob};
  assert(call(1, &r, &out));
  assert(is_zero(&out.blob, sizeof(out.blob))); /* nothing new to cache */
  assert(!memcmp(out.public_key, pub.public_key, 33));
  r = (vault_request_t){.op = VAULT_IMPORT_NODE,
                        .owner = request,
                        .length = 98,
                        .arg = pub.depth,
                        .child_num = pub.child_num};
  strcpy(r.curve, "secp256k1");
  memcpy(r.data, pub.chain_code, 32);
  memcpy(r.data + 64, pub.public_key, 33);
  r.data[97] = 2;
  assert(call(1, &r, &out));
  vault_blob_t public_only = out.blob;
  assert(!sign(request, &public_only, NULL));
  vault_request_t import = r;
  r = (vault_request_t){
      .op = VAULT_DERIVE, .owner = request, .blob = public_only, .length = 4};
  for (uint32_t index = 0; index <= 1; index++) {
    uint32_t child_index = index ? 0x80000000 : 1;
    memcpy(r.data, &child_index, sizeof(child_index));
    assert(!call(1, &r, &out));
    assert(is_zero(&out, sizeof(out)));
  }
  r.arg = 1; /* Public derivation still works, and remains public-only. */
  uint32_t public_index = 1;
  memcpy(r.data, &public_index, sizeof(public_index));
  assert(call(1, &r, &out));
  vault_blob_t public_child = out.blob;
  assert(!sign(request, &public_child, NULL));
  for (uint32_t field = 0; field < 2; field++) {
    r = (vault_request_t){.op = VAULT_SNAPSHOT,
                          .owner = request,
                          .blob = public_only,
                          .arg = field};
    assert(!call(1, &r, &out));
    assert(is_zero(&out, sizeof(out)));
  }
  r = import;
  r.data[97] = 1; /* explicitly supplied zero is an invalid ECDSA key */
  assert(!call(1, &r, &out));

  /* Retain moves a request secret to its session, readable by siblings. */
  r = (vault_request_t){
      .op = VAULT_RETAIN, .owner = request, .blob = key, .arg = SECRET_BYTES};
  assert(call(1, &r, &out));
  vault_blob_t retained = out.blob;
  assert(sign(sibling, &retained, again));
  assert(!memcmp(signature, again, 65));
  assert(!sign(other, &retained, NULL));
  r.arg = SECRET_NODE; /* wrong kind */
  assert(!call(1, &r, &out));
  r = (vault_request_t){
      .op = VAULT_RETAIN, .owner = sibling, .blob = key, .arg = SECRET_BYTES};
  assert(!call(1, &r, &out)); /* only the owning request retains */

  /* Destroying an owner revokes every blob it sealed. */
  r = (vault_request_t){.op = VAULT_OWNER_DESTROY, .owner = request};
  assert(call(1, &r, &out));
  assert(!sign(request, &key, NULL));
  uint32_t replacement = owner_create(1, session);
  assert(replacement && replacement != request);
  assert(!sign(replacement, &key, NULL)); /* ids are never reused */
  assert(sign(replacement, &retained, NULL));

  /* Key rotation revokes every blob, even for live owners. */
  r = (vault_request_t){.op = VAULT_IMPORT_BYTES, .owner = replacement};
  r.length = 32;
  memset(r.data, 7, 32);
  assert(call(1, &r, &out));
  vault_blob_t before = out.blob;
  assert(sign(replacement, &before, NULL));
  vault_seal_wipe();
#if VAULT_SEAL_MODE != VAULT_SEAL_AES_ECB
  assert(!sign(replacement, &before, NULL));
  assert(!sign(replacement, &retained, NULL));
#else
  /* ECB cannot detect decryption under a different key. Production vault_wipe
   * also revokes owners; rotating only the DEK supplies no integrity check. */
  assert(sign(replacement, &before, NULL));
#endif
  assert(call(1, &r, &out));
  assert(sign(replacement, &out.blob, NULL));

  vault_revoke_caller(2);
  assert(sign(replacement, &out.blob, NULL));
  vault_revoke_caller(1);
  assert(!sign(replacement, &out.blob, NULL));
  assert(!secret_owner_find(session));
  assert(is_zero(secret_scratch, sizeof(secret_scratch)));

  for (int flags = 0; flags < 4; flags++) {
    assert(!vault_storage_key_allowed(0x0102 | (flags << 14)));
    assert(!vault_storage_key_allowed(0x0125 | (flags << 14)));
  }
  assert(vault_storage_key_allowed(0x010e));
  printf("kernel state: owners=%zu scratch=%zu blob=%d\n",
         sizeof(secret_owners), sizeof(secret_scratch), VAULT_BLOB_SIZE);
  schnorr_vectors();
  slip21_vectors();
  fingerprint_vectors();
  node_import_vectors();
  assert(!zkp_context_is_initialized());
  locked_authorization();
  puts("vault boundary tests passed");
  return 0;
}
/* Firmware assertions must fail the host test, rather than being compiled out.
 */
#include <stdlib.h>
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
