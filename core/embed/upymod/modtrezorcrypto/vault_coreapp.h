/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Transitional native adapter; plaintext stays outside Python. */
#ifndef TREZOR_COREAPP_VAULT_H
#define TREZOR_COREAPP_VAULT_H
#ifndef VAULT_TEST
#include <sec/storage.h>
#endif
#include "aes/aes.h"
#include "blake256.h"
#include "cardano.h"
#include "chacha20poly1305/rfc7539.h"
#include "consteq.h"
#include "pbkdf2.h"
#if USE_MONERO
#include "ed25519-donna/ed25519-donna.h"
#include "sha3.h"
#endif
#include "bip32.h"
#include "bip39.h"
#include "curves.h"
#include "ecdsa.h"
#include "ed25519-donna/ed25519-keccak.h"
#include "ed25519-donna/ed25519.h"
#include "hmac.h"
#include "memzero.h"
#include "nist256p1.h"
#include "rand.h"
#include "ripemd160.h"
#include "secp256k1.h"
#include "sha2.h"
#include "vault_slip21.h"
#include "zkp_bip340.h"
#include "zkp_context.h"
#ifndef VAULT_RECORD_SIZE
#define VAULT_RECORD_SIZE VAULT_SECRET_SIZE
#endif
typedef union {
  HDNode node;
  uint8_t bytes[VAULT_SECRET_SIZE];
} app_secret_payload_t;
static app_secret_payload_t app_scratch[2];
static bool app_used[2], app_busy;
static app_secret_payload_t *app_secret_scratch_take(void) {
  for (size_t i = 0; i < 2; i++) {
    if (!app_used[i]) {
      app_used[i] = true;
      memzero(&app_scratch[i], sizeof(app_scratch[i]));
      return &app_scratch[i];
    }
  }
  return NULL;
}
static uint32_t app_secret_get32(const uint8_t *p) {
  return p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 |
         (uint32_t)p[3] << 24;
}
static void app_secret_put32(uint8_t *p, uint32_t v) {
  for (size_t i = 0; i < 4; i++) p[i] = v >> (8 * i);
}
/* Stable wire IDs, never serialize native curve pointers. */
static const char *app_secret_curve_name(uint8_t id) {
  static const char *const curves[] = {
      SECP256K1_NAME,         NIST256P1_NAME,         ED25519_NAME,
      SECP256K1_DECRED_NAME,  SECP256K1_GROESTL_NAME, SECP256K1_SMART_NAME,
      "ed25519 cardano seed", ED25519_SHA3_NAME,      ED25519_KECCAK_NAME,
      CURVE25519_NAME};
  return id < sizeof(curves) / sizeof(curves[0]) ? curves[id] : NULL;
}
static uint8_t app_secret_curve_id(const HDNode *n) {
  for (uint8_t i = 0; app_secret_curve_name(i); ++i)
    if (n->curve == get_curve_by_name(app_secret_curve_name(i))) return i;
  return UINT8_MAX;
}
static bool app_secret_curve_allowed(const char *name) {
  for (uint8_t i = 0; app_secret_curve_name(i); ++i)
    if (!strcmp(name, app_secret_curve_name(i)))
      return get_curve_by_name(name) != NULL;
  return false;
}
/* Canonical node encoding: no struct padding, addresses or curve pointers. */
static void app_secret_encode(secret_kind_t kind, size_t length,
                              const app_secret_payload_t *p,
                              uint8_t data[VAULT_RECORD_SIZE]) {
  memset(data, 0, VAULT_RECORD_SIZE);
  if (kind == SECRET_BYTES) {
    memcpy(data, p->bytes, length);
    return;
  }
  const HDNode *n = &p->node;
  app_secret_put32(data, n->depth);
  app_secret_put32(data + 4, n->child_num);
  memcpy(data + 8, n->chain_code, 32);
  memcpy(data + 40, n->private_key, 32);
  memcpy(data + 72, n->public_key, 33);
  data[105] = n->is_public_key_set;
  data[106] = app_secret_curve_id(n);
  memcpy(data + 107, n->private_key_extension, 32);
}
static bool app_secret_decode(secret_kind_t kind, size_t length,
                              const uint8_t data[VAULT_RECORD_SIZE],
                              app_secret_payload_t *p) {
  memzero(p, sizeof(*p));
  if (kind == SECRET_BYTES) {
    if (length > VAULT_SECRET_SIZE) return false;
    memcpy(p->bytes, data, length);
    return true;
  }
  if (kind != SECRET_NODE || data[105] > 1 || !app_secret_curve_name(data[106]))
    return false;
  HDNode *n = &p->node;
  n->depth = app_secret_get32(data);
  n->child_num = app_secret_get32(data + 4);
  memcpy(n->chain_code, data + 8, 32);
  memcpy(n->private_key, data + 40, 32);
  memcpy(n->public_key, data + 72, 33);
  memcpy(n->private_key_extension, data + 107, 32);
  n->is_public_key_set = data[105];
  n->curve = get_curve_by_name(app_secret_curve_name(data[106]));
  return n->curve != NULL;
}

static app_secret_payload_t *app_secret_open(const vault_blob_t *blob,
                                             uint32_t owner, secret_kind_t kind,
                                             size_t *length) {
  vault_request_t r = {.abi = VAULT_ABI,
                       .op = VAULT_OPEN_NATIVE,
                       .owner = owner,
                       .arg = kind,
                       .blob = *blob};
  vault_response_t out = {0};
  app_secret_payload_t *p = NULL;
  if (vault_call(&r, &out) && (p = app_secret_scratch_take())) {
    size_t n = kind == SECRET_BYTES ? out.value : sizeof(HDNode);
    if ((kind == SECRET_NODE && out.value != VAULT_NODE_SIZE) ||
        !app_secret_decode(kind, n, out.opened, p))
      p = NULL;
    if (p && length) *length = n;
  }
  memzero(&r, sizeof(r));
  memzero(&out, sizeof(out));
  return p;
}
static bool app_secret_seal(uint32_t owner, secret_kind_t kind, size_t length,
                            const app_secret_payload_t *p, vault_blob_t *blob) {
  if (kind == SECRET_NODE &&
      (app_secret_curve_id(&p->node) == UINT8_MAX ||
       (memcmp(p->node.private_key_extension, (uint8_t[32]){0}, 32) &&
        p->node.curve != get_curve_by_name("ed25519 cardano seed"))))
    return false;
  vault_request_t r = {
      .abi = VAULT_ABI,
      .op = VAULT_IMPORT_BYTES,
      .owner = owner,
      .arg = kind,
      .child_num = 1,
      .length = kind == SECRET_BYTES ? length : VAULT_NODE_SIZE};
  app_secret_encode(kind, length, p, r.data);
  vault_response_t out = {0};
  bool ok = vault_call(&r, &out);
  if (ok) *blob = out.blob;
  memzero(&r, sizeof(r));
  memzero(&out, sizeof(out));
  return ok;
}
#ifndef VAULT_TEST
/* SLIP-0039 seed derivation from stored EMS and parameters. */
static __attribute__((noinline)) bool vault_slip39_seed(
    const uint8_t *passphrase, size_t passphrase_length, uint8_t backup_type,
    uint8_t *seed, size_t *seed_length) {
  uint8_t ems[32] = {0}, password[201] = {0}, salt[24] = {0};
  uint8_t round_key[16] = {0}, next[16] = {0}, identifier[2] = {0};
  uint8_t exponent = 0;
  uint16_t length = 0;
  bool ok = false;
  if (backup_type < 1 || backup_type > 5 || passphrase_length > 200 ||
      storage_get(0x0102, ems, sizeof(ems), &length) != sectrue ||
      (length != 16 && length != 32))
    goto cleanup;
  size_t half = length / 2;
  *seed_length = length;
  if (storage_get(0x0111, &exponent, 1, &length) != sectrue || length != 1 ||
      exponent > 15)
    goto cleanup;
  size_t salt_length = 0;
  if (backup_type < 3) {
    if (storage_get(0x0110, identifier, 2, &length) != sectrue || length != 2)
      goto cleanup;
    memcpy(salt, "shamir", 6);
    memcpy(salt + 6, identifier, 2);
    salt_length = 8;
  }
  memcpy(password + 1, passphrase, passphrase_length);
  for (int round = 3; round >= 0; --round) {
    password[0] = round;
    memcpy(salt + salt_length, ems + half, half);
    pbkdf2_hmac_sha256(password, passphrase_length + 1, salt,
                       salt_length + half, (10000U << exponent) / 4, round_key,
                       half);
    for (size_t i = 0; i < half; ++i) next[i] = ems[i] ^ round_key[i];
    memcpy(ems, ems + half, half);
    memcpy(ems + half, next, half);
  }
  memcpy(seed, ems + half, half);
  memcpy(seed + half, ems, half);
  ok = true;
cleanup:
  memzero(ems, sizeof(ems));
  memzero(password, sizeof(password));
  memzero(salt, sizeof(salt));
  memzero(round_key, sizeof(round_key));
  memzero(next, sizeof(next));
  memzero(identifier, sizeof(identifier));
  return ok;
}
#endif

static bool app_node_has_private_key(const HDNode *node) {
  /* Public-only ECDSA nodes carry an all-zero private key. Ed25519 imports
   * require a private seed, and an all-zero seed is valid. */
  return !node->curve->params ||
         memcmp(node->private_key, (uint8_t[32]){0}, 32) != 0;
}

/* Fingerprints use HASH160 (BLAKE-256 for Decred). Selecting those two
 * implementations directly avoids pulling every coin's address/checksum
 * hasher into the kernel while preserving all admitted curves. */
static bool app_vault_fingerprint(HDNode *node, uint32_t *fingerprint) {
  if (!node->curve || hdnode_fill_public_key(node) != 0) return false;
  uint8_t digest[32] = {0}, hash160[20] = {0};
  if (node->curve->hasher_pubkey == HASHER_SHA2_RIPEMD)
    sha256_Raw(node->public_key, sizeof(node->public_key), digest);
  else if (node->curve->hasher_pubkey == HASHER_BLAKE_RIPEMD)
    blake256(node->public_key, sizeof(node->public_key), digest);
  else
    return false;
  ripemd160(digest, sizeof(digest), hash160);
  *fingerprint = ((uint32_t)hash160[0] << 24) | ((uint32_t)hash160[1] << 16) |
                 ((uint32_t)hash160[2] << 8) | hash160[3];
  memzero(digest, sizeof(digest));
  memzero(hash160, sizeof(hash160));
  return true;
}

/* Coreapp-local view of a validated snapshot. Public inputs stay in the
 * originating snapshot; compact message requests need no full RPC envelope. */
/* Canonical ECDSA forms, selected by VAULT_SIGN's canonical field. Coreapp
 * passes a selector, never a callback. */
static int vault_ethereum_canonical(uint8_t v, uint8_t signature[64]) {
  (void)signature;
  return (v & 2) == 0;
}
static int vault_eos_canonical(uint8_t v, uint8_t signature[64]) {
  (void)v;
  return !(signature[0] & 0x80) &&
         !(signature[0] == 0 && !(signature[1] & 0x80)) &&
         !(signature[32] & 0x80) &&
         !(signature[32] == 0 && !(signature[33] & 0x80));
}

typedef struct {
  uint32_t abi, op, owner, arg, length, child_num;
  const vault_blob_t *blob;
  const vault_blob_t *extension;
  const char *curve;
  const uint8_t *data;
} app_vault_command_t;

/* The dispatcher scopes one transient ZKP context around wallet operations. */
static bool app_vault_schnorr(const app_vault_command_t *r,
                              vault_response_t *out,
                              app_secret_payload_t **made) {
  bool ok = false;
  size_t length = 0;
  app_secret_payload_t *key = NULL;
  if (r->op == VAULT_SCHNORR_GENERATE) {
    *made = app_secret_scratch_take();
    if (!*made) goto cleanup;
    do {
      random_buffer((*made)->bytes, 32);
    } while (!hdnode_validate_private_key(get_curve_by_name(SECP256K1_NAME),
                                          (*made)->bytes));
    ok = true;
    goto cleanup;
  }
  key = app_secret_open(r->blob, r->owner, SECRET_BYTES, &length);
  if (!key || length != 32) goto cleanup;
  switch (r->op) {
    case VAULT_SCHNORR_PUBLIC:
      ok = zkp_bip340_get_public_key(key->bytes, out->signature) == 0;
      break;
    case VAULT_SCHNORR_SIGN:
      if (r->length != 32) break;
      ok = zkp_bip340_sign_digest(key->bytes, r->data, out->signature, NULL) ==
           0;
      break;
    case VAULT_SCHNORR_TWEAK:
      if ((r->length != 0 && r->length != 32) ||
          !(*made = app_secret_scratch_take()))
        break;
      ok = zkp_bip340_tweak_private_key(key->bytes, r->length ? r->data : NULL,
                                        (*made)->bytes) == 0;
      break;
    default:
      break;
  }
cleanup:
  return ok;
}

#if USE_MONERO
static __attribute__((noinline)) bool vault_monero_public(
    const app_vault_command_t *r, vault_response_t *out) {
  if (r->length != 8 || r->arg > 1) return false;
  app_secret_payload_t *key =
      app_secret_open(r->blob, r->owner, SECRET_NODE, NULL);
  if (!key || key->node.curve != get_curve_by_name(ED25519_NAME)) return false;
  uint32_t major = 0, minor = 0;
  memcpy(&major, r->data, 4);
  memcpy(&minor, r->data + 4, 4);
  if (r->arg && (major || minor)) return false;
  bignum256modm spend_scalar = {0}, view_scalar = {0}, sub_scalar = {0};
  ge25519 spend = {0}, view = {0}, sub = {0};
  uint8_t encoded[32] = {0}, hash[32] = {0};
  expand256_modm(spend_scalar, key->node.private_key, 32);
  contract256_modm(encoded, spend_scalar);
  keccak_256(encoded, 32, hash);
  expand256_modm(view_scalar, hash, 32);
  ge25519_scalarmult_base_wrapper(&spend, spend_scalar);
  if (major || minor) {
    uint8_t data[48] = {0};
    memcpy(data, "SubAddr", 8);
    contract256_modm(data + 8, view_scalar);
    app_secret_put32(data + 40, major);
    app_secret_put32(data + 44, minor);
    keccak_256(data, sizeof(data), hash);
    expand256_modm(sub_scalar, hash, sizeof(hash));
    memzero(data, sizeof(data));
    ge25519_scalarmult_base_wrapper(&sub, sub_scalar);
    ge25519_add(&spend, &spend, &sub, 0);
    ge25519_scalarmult(&view, &spend, view_scalar);
  } else {
    ge25519_scalarmult_base_wrapper(&view, view_scalar);
  }
  ge25519_pack(out->data, &spend);
  ge25519_pack(out->data + 32, &view);
  /* Watch-only export is a host-visible operation by design. The private
   * spend scalar is never returned. */
  if (r->arg) contract256_modm(out->data + 64, view_scalar);
  memzero(spend_scalar, sizeof(spend_scalar));
  memzero(view_scalar, sizeof(view_scalar));
  memzero(sub_scalar, sizeof(sub_scalar));
  memzero(encoded, sizeof(encoded));
  memzero(hash, sizeof(hash));
  memzero(&spend, sizeof(spend));
  memzero(&view, sizeof(view));
  memzero(&sub, sizeof(sub));
  return true;
}
#endif

static bool app_execute(const app_vault_command_t *r, vault_response_t *out,
                        const uint8_t *message, size_t message_length) {
  /* The result, if any, is sealed for `made_owner` into out->blob. */
  app_secret_payload_t *made = NULL;
  secret_kind_t made_kind = SECRET_NODE;
  size_t made_length = sizeof(HDNode);
  uint32_t made_owner = r->owner;
  HDNode *node = NULL;
  bool ok = false;
  switch (r->op) {
    case VAULT_IMPORT_BYTES:
      if (!r->length || r->length > VAULT_SECRET_SIZE ||
          !(made = app_secret_scratch_take()))
        break;
      made_kind = SECRET_BYTES;
      made_length = r->length;
      memcpy(made->bytes, r->data, r->length);
      ok = true;
      break;
#if USE_CARDANO
    case VAULT_CARDANO: {
      /* 0: master secret, 1: SLIP-23, 2: Ledger, 3: Icarus input,
       * 4: Icarus stored mnemonic. Bit 8 selects a sealed input. */
      uint32_t mode = r->arg & 0xff;
      if (r->arg & ~0x1ffU || mode > 4) break;
      size_t length = r->length;
      const uint8_t *input = r->data;
      if (r->arg & 0x100) {
        app_secret_payload_t *src =
            app_secret_open(r->blob, r->owner, SECRET_BYTES, &length);
        if (!src) break;
        input = src->bytes;
      }
      if (!(made = app_secret_scratch_take())) break;
      uint8_t secret[96] = {0}, binary[33] = {0};
      if (mode <= 2) {
        if (mode == 0) {
          if (length == sizeof(secret)) {
            memcpy(secret, input, length);
            ok = true;
          }
        } else if (length) {
          ok = (mode == 1
                    ? secret_from_seed_cardano_slip23(input, length, secret)
                    : secret_from_seed_cardano_ledger(input, length, secret)) ==
               1;
        }
        if (ok) ok = hdnode_from_secret_cardano(secret, &made->node) == 1;
      } else {
        size_t binary_length = 0, pass_length = 0;
        const uint8_t *pass = NULL;
        if (mode == 3 && length && input[0] <= sizeof(binary) &&
            length >= 1U + input[0]) {
          binary_length = input[0];
          memcpy(binary, input + 1, binary_length);
          pass = input + 1 + binary_length;
          pass_length = length - 1 - binary_length;
        }
#ifndef VAULT_TEST
        if (mode == 4 && !(r->arg & 0x100)) {
          uint16_t n = 0;
          if (storage_get(0x0125, binary, sizeof(binary), &n) == sectrue) {
            binary_length = n;
            pass = input;
            pass_length = length;
          }
        }
#endif
        if ((binary_length >= 17 && binary_length <= 33 &&
             binary_length % 4 == 1) &&
            pass && pass_length <= 200 && r->child_num <= 1) {
          size_t entropy_length = binary_length - (binary_length + 32) / 33;
          if (r->child_num) entropy_length += binary_length / 33;
          ok =
              secret_from_entropy_cardano_icarus(
                  pass, pass_length, binary, entropy_length, secret, NULL) == 1;
          if (ok) {
            made_kind = SECRET_BYTES;
            made_length = sizeof(secret);
            memcpy(made->bytes, secret, sizeof(secret));
          }
        }
      }
      memzero(binary, sizeof(binary));
      memzero(secret, sizeof(secret));
      break;
    }
    case VAULT_ED_SIGN_EXT: {
      app_secret_payload_t *key =
          app_secret_open(r->blob, r->owner, SECRET_NODE, NULL);
      /* Both scalar and nonce prefix come from one authenticated node. Never
       * permit the legacy two-record request or another curve's node. */
      if (!key || key->node.curve != &ed25519_cardano_info ||
          !app_node_has_private_key(&key->node) || !message || r->arg)
        break;
      if (r->extension) {
        bool supplied = false;
        for (size_t i = 0; i < sizeof(r->extension->bytes); i++)
          supplied |= r->extension->bytes[i] != 0;
        if (supplied) break;
      }
      ed25519_sign_ext(message, message_length, key->node.private_key,
                       key->node.private_key_extension, out->signature);
      ok = true;
      break;
    }
#endif
    case VAULT_CHACHA_BLOCK:
    case VAULT_CHACHA_TAG: {
      size_t key_length = 0;
      app_secret_payload_t *key =
          app_secret_open(r->blob, r->owner, SECRET_BYTES, &key_length);
      if (!key || key_length != 32) break;
      chacha20poly1305_ctx ctx = {0};
      if (r->op == VAULT_CHACHA_BLOCK) {
        if (!r->curve || r->arg > 1 || r->child_num % 64 ||
            r->child_num > VAULT_ED25519_MAX_MESSAGE)
          break;
        rfc7539_init(&ctx, key->bytes, (const uint8_t *)r->curve);
        ctx.chacha20.input[12] += r->child_num / 64;
        if (r->arg)
          chacha20poly1305_decrypt(&ctx, r->data, out->data, r->length);
        else
          chacha20poly1305_encrypt(&ctx, r->data, out->data, r->length);
        ok = true;
      } else if (r->extension && message && r->arg <= 32 &&
                 r->arg <= message_length) {
        rfc7539_init(&ctx, key->bytes, r->extension->bytes);
        rfc7539_auth(&ctx, message, r->arg);
        chacha20poly1305_auth(&ctx, message + r->arg, message_length - r->arg);
        rfc7539_finish(&ctx, r->arg, message_length - r->arg, out->signature);
        ok = true;
      }
      memzero(&ctx, sizeof(ctx));
      break;
    }
#if USE_MONERO
    case VAULT_MONERO_PUBLIC:
      ok = vault_monero_public(r, out);
      break;
#endif
    case VAULT_ECDH: {
      size_t length = 0;
      app_secret_payload_t *key =
          app_secret_open(r->blob, r->owner, SECRET_BYTES, &length);
      if (!key || length != 32 || r->arg > 2) break;
      if (r->arg == 2) {
        if (r->length != 32) break;
        curve25519_scalarmult(out->signature, key->bytes, r->data);
        ok = true;
      } else {
        if (r->length != 33 && r->length != 65) break;
        const ecdsa_curve *curve = r->arg ? &nist256p1 : &secp256k1;
        ok = ecdh_multiply(curve, key->bytes, r->data, out->signature) == 0;
      }
      break;
    }
#if USE_NEM
    case VAULT_NEM_SHARED: {
      app_secret_payload_t *node =
          app_secret_open(r->blob, r->owner, SECRET_NODE, NULL);
      if (!node || r->length != 64 || !(made = app_secret_scratch_take()))
        break;
      ok = hdnode_get_nem_shared_key(&node->node, r->data, r->data + 32, NULL,
                                     made->bytes) != 0;
      made_kind = SECRET_BYTES;
      made_length = 32;
      break;
    }
#endif
    case VAULT_KEYVALUE_DERIVE: {
      app_secret_payload_t *key =
          app_secret_open(r->blob, r->owner, SECRET_NODE, NULL);
      if (!key || key->node.curve != get_curve_by_name(SECP256K1_NAME) ||
          !app_node_has_private_key(&key->node) || !message || r->arg ||
          !(made = app_secret_scratch_take()))
        break;
      uint8_t digest[64] = {0};
      HMAC_SHA512_CTX ctx = {0};
      hmac_sha512_Init(&ctx, key->node.private_key, 32);
      hmac_sha512_Update(&ctx, message, message_length);
      hmac_sha512_Final(&ctx, digest);
      memcpy(made->bytes, digest, 32);
      memcpy(out->chain_code, digest + 32, 16);
      made_kind = SECRET_BYTES;
      made_length = 32;
      memzero(digest, sizeof(digest));
      memzero(&ctx, sizeof(ctx));
      ok = true;
      break;
    }
    case VAULT_AES_CBC: {
      size_t length = 0;
      app_secret_payload_t *key =
          app_secret_open(r->blob, r->owner, SECRET_BYTES, &length);
      if (!key || length != 32 || r->arg > 1 || r->length % 16 || !r->curve)
        break;
      uint8_t iv[16] = {0};
      memcpy(iv, r->curve, 16);
      if (r->arg) {
        aes_encrypt_ctx ctx = {0};
        ok = aes_encrypt_key256(key->bytes, &ctx) == 0 &&
             aes_cbc_encrypt(r->data, out->data, r->length, iv, &ctx) == 0;
        memzero(&ctx, sizeof(ctx));
      } else {
        aes_decrypt_ctx ctx = {0};
        ok = aes_decrypt_key256(key->bytes, &ctx) == 0 &&
             aes_cbc_decrypt(r->data, out->data, r->length, iv, &ctx) == 0;
        memzero(&ctx, sizeof(ctx));
      }
      memzero(iv, sizeof(iv));
      break;
    }
    case VAULT_FROM_SEED: {
      if (!app_secret_curve_allowed(r->curve)) break;
      const uint8_t *seed = r->data;
      size_t len = r->length;
      if (r->arg) {
        app_secret_payload_t *p =
            app_secret_open(r->blob, r->owner, SECRET_BYTES, &len);
        seed = p ? p->bytes : NULL;
      }
      if (!seed || !len || !(made = app_secret_scratch_take())) break;
      ok = hdnode_from_seed(seed, len, r->curve, &made->node) != 0;
      break;
    }
    case VAULT_IMPORT_NODE: {
      if (!app_secret_curve_allowed(r->curve)) break;
      /* Wire format: chain[32], private[32], public[33], presence flags.
       * Ed25519 public keys start with zero; do not infer presence from it. */
      if (r->length != 98 || !r->data[97] || r->data[97] > 3 ||
          !(made = app_secret_scratch_take()))
        break;
      node = &made->node;
      node->curve = get_curve_by_name(r->curve);
      if (!node->curve) break;
      /* HDNode has no private-presence bit. Require a private field for
       * Ed25519 imports so the valid all-zero seed cannot be confused with
       * a public-only node. Public-only imports remain supported for ECDSA. */
      if (node->curve->params == NULL && !(r->data[97] & 1)) break;
      node->depth = r->arg;
      node->child_num = r->child_num;
      memcpy(node->chain_code, r->data, 32);
      if (r->data[97] & 1) memcpy(node->private_key, r->data + 32, 32);
      if (r->data[97] & 2) memcpy(node->public_key, r->data + 64, 33);
      node->is_public_key_set = (r->data[97] & 2) != 0;
      ok = (!(r->data[97] & 1) ||
            hdnode_validate_private_key(node->curve, node->private_key)) &&
           (!node->is_public_key_set ||
            hdnode_validate_public_key(node->curve, node->public_key));
      /* A supplied cache must describe the private key. Otherwise public
       * derivation and signing would silently use different identities. */
      if (ok && r->data[97] == 3) {
        node->is_public_key_set = false;
        ok = hdnode_fill_public_key(node) == 0 &&
             memcmp(node->public_key, r->data + 64, 33) == 0;
      }
      break;
    }
    case VAULT_PUBLIC: {
      app_secret_payload_t *p =
          app_secret_open(r->blob, r->owner, SECRET_NODE, NULL);
      if (!p) break;
      node = &p->node;
      bool computed = !node->is_public_key_set;
      if (hdnode_fill_public_key(node)) break;
      out->depth = node->depth;
      out->child_num = node->child_num;
      out->value = app_secret_curve_id(node);
      memcpy(out->chain_code, node->chain_code, 32);
      memcpy(out->public_key, node->public_key, 33);
      /* Hand back a blob that carries the computed key, so the client does
       * not pay for the point multiplication again. */
      if (computed) {
        made = p;
        made_owner = app_secret_get32(r->blob->bytes);
      }
      ok = true;
      break;
    }
    case VAULT_DERIVE: {
      if (r->length != 4 || r->arg > 1) break;
      made = app_secret_open(r->blob, r->owner, SECRET_NODE, NULL);
      if (!made) break;
      if (!r->arg && !app_node_has_private_key(&made->node)) break;
      made_owner = app_secret_get32(r->blob->bytes);
      uint32_t index;
      memcpy(&index, r->data, 4);
      if (!app_vault_fingerprint(&made->node, &out->value)) break;
      ok = (r->arg ? hdnode_public_ckd(&made->node, index)
                   : hdnode_private_ckd(&made->node, index)) != 0;
      break;
    }
    case VAULT_SNAPSHOT: {
      app_secret_payload_t *p =
          app_secret_open(r->blob, r->owner, SECRET_NODE, NULL);
      if (!p || !app_node_has_private_key(&p->node) ||
#if USE_CARDANO
          p->node.curve == &ed25519_cardano_info ||
#endif
          r->arg != 0 || !(made = app_secret_scratch_take()))
        break;
      made_kind = SECRET_BYTES;
      made_length = 32;
      memcpy(made->bytes, p->node.private_key, 32);
      ok = true;
      break;
    }
    case VAULT_SIGN: {
      size_t len = 0;
      const uint8_t *key = NULL;
      if (r->blob->bytes[4] == SECRET_BYTES) {
        app_secret_payload_t *p =
            app_secret_open(r->blob, r->owner, SECRET_BYTES, &len);
        key = p ? p->bytes : NULL;
      } else {
        /* Sign from a node in place: no snapshot, no second key copy. */
        app_secret_payload_t *p =
            app_secret_open(r->blob, r->owner, SECRET_NODE, NULL);
        if (p && p->node.curve && p->node.curve->params == &secp256k1 &&
            app_node_has_private_key(&p->node)) {
          key = p->node.private_key;
          len = 32;
        }
      }
      /* arg: bit 0 compressed, bits 1-2 VAULT_CANONICAL_*. */
      uint32_t compressed = r->arg & 1, canonical = r->arg >> 1;
      int (*is_canonical)(uint8_t, uint8_t[64]) =
          canonical == VAULT_CANONICAL_ETHEREUM ? vault_ethereum_canonical
          : canonical == VAULT_CANONICAL_EOS    ? vault_eos_canonical
                                                : NULL;
      uint8_t recovery = 0;
      if (!key || len != 32 || r->length != 32 ||
          canonical > VAULT_CANONICAL_EOS)
        break;
      ok = ecdsa_sign_digest(&secp256k1, key, r->data, out->signature + 1,
                             &recovery, is_canonical) == 0;
      if (ok) out->signature[0] = 27 + recovery + 4 * compressed;
      break;
    }
    case VAULT_ED_PUBLIC:
    case VAULT_ED_SIGN: {
      size_t length = 0;
      app_secret_payload_t *key =
          app_secret_open(r->blob, r->owner, SECRET_BYTES, &length);
      if (!key || length != 32 || r->length || r->arg > 1) break;
      if (r->op == VAULT_ED_PUBLIC) {
        if (r->arg) break;
        ed25519_publickey(key->bytes, out->signature);
      } else {
        if (!message || !message_length ||
            message_length > VAULT_ED25519_MAX_MESSAGE)
          break;
        if (r->arg)
          ed25519_sign_keccak(message, message_length, key->bytes,
                              out->signature);
        else
          ed25519_sign(message, message_length, key->bytes, out->signature);
      }
      ok = true;
      break;
    }
    case VAULT_NIST_PUBLIC:
    case VAULT_NIST_SIGN:
    case VAULT_HMAC_TAG: {
      size_t length = 0;
      app_secret_payload_t *key =
          app_secret_open(r->blob, r->owner, SECRET_BYTES, &length);
      if (!key) break;
      if (r->op == VAULT_HMAC_TAG) {
        if (r->arg == 256) {
          hmac_sha256(key->bytes, length, r->data, r->length, out->signature);
          ok = true;
        } else if (r->arg == 512) {
          hmac_sha512(key->bytes, length, r->data, r->length, out->signature);
          ok = true;
        }
        break;
      }
      if (length != 32 || r->arg > (r->op == VAULT_NIST_PUBLIC ? 3U : 1U))
        break;
      if (r->op == VAULT_NIST_PUBLIC) {
        if (r->length) break;
        const ecdsa_curve *curve = r->arg & 2 ? &secp256k1 : &nist256p1;
        ok = ((r->arg & 1)
                  ? ecdsa_get_public_key33(curve, key->bytes, out->signature)
                  : ecdsa_get_public_key65(curve, key->bytes,
                                           out->signature)) == 0;
      } else {
        uint8_t recovery = 0;
        if (r->length != 32) break;
        ok = ecdsa_sign_digest(&nist256p1, key->bytes, r->data,
                               out->signature + 1, &recovery, NULL) == 0;
        if (ok) out->signature[0] = 27 + recovery + 4 * r->arg;
      }
      break;
    }
    case VAULT_SCHNORR_GENERATE:
    case VAULT_SCHNORR_PUBLIC:
    case VAULT_SCHNORR_TWEAK:
    case VAULT_SCHNORR_SIGN:
      made_kind = SECRET_BYTES;
      made_length = 32;
      ok = app_vault_schnorr(r, out, &made);
      break;
#ifndef VAULT_TEST
    case VAULT_MNEMONIC: {
      /* Explicit backup disclosure is distinct from deriving wallet keys.
       * Recovery comparison and storage migration never disclose the value. */
      char mnemonic[256] = {0};
      uint16_t length = 0;
      if (storage_get(0x0102, mnemonic, sizeof(mnemonic) - 1, &length) ==
              sectrue &&
          length && length < sizeof(mnemonic)) {
        if (r->arg == 0) {
          out->data[0] = length;
          memcpy(out->data + 1, mnemonic, length);
          ok = true;
        } else if (r->arg == 1) {
          out->value =
              length == r->length && consteq(mnemonic, r->data, length);
          ok = true;
        } else if (r->arg == 2) {
          uint8_t bits[33] = {0};
          size_t n = mnemonic_to_bits(mnemonic, bits);
          ok = n && storage_set(0x0125, bits, (n + 7) / 8) == sectrue;
          memzero(bits, sizeof(bits));
        }
      }
      memzero(mnemonic, sizeof(mnemonic));
      break;
    }
    case VAULT_SEED_STORAGE: {
      char mnemonic[256] = {0};
      uint8_t backup_type = 0;
      uint16_t len = 0;
      /* Derive inside the vault for both supported backup families. */
      bool bip39 = storage_get(0x010e, &backup_type, 1, &len) != sectrue ||
                   (len == 1 && backup_type == 0);
      if (bip39 && r->length <= 200 && !memchr(r->data, 0, r->length) &&
          storage_get(0x0102, mnemonic, sizeof(mnemonic) - 1, &len) ==
              sectrue &&
          len && len < sizeof(mnemonic) && !memchr(mnemonic, 0, len) &&
          (made = app_secret_scratch_take())) {
        char passphrase[201] = {0};
        memcpy(passphrase, r->data, r->length);
        mnemonic_to_seed(mnemonic, passphrase, made->bytes, NULL);
        memzero(passphrase, sizeof(passphrase));
        made_kind = SECRET_BYTES;
        made_length = 64;
        ok = true;
      }
      if (!bip39 && r->length <= 200 && !memchr(r->data, 0, r->length) &&
          (made = app_secret_scratch_take())) {
        ok = vault_slip39_seed(r->data, r->length, backup_type, made->bytes,
                               &made_length);
        made_kind = SECRET_BYTES;
      }
      memzero(mnemonic, sizeof(mnemonic));
      break;
    }
#endif
    default:
      break;
  }
  if (ok && made)
    ok = app_secret_seal(made_owner, made_kind, made_length, made, &out->blob);
  if (!ok) memzero(out, sizeof(*out));
  return ok;
}
static bool app_dispatch(const app_vault_command_t *r, vault_response_t *out,
                         const uint8_t *message, size_t length) {
  memset(out, 0, sizeof(*out));
  if (app_busy || r->abi != VAULT_ABI || r->length > VAULT_DATA_SIZE ||
      (r->curve && !memchr(r->curve, 0, VAULT_CURVE_SIZE)))
    return false;
  vault_request_t check = {
      .abi = VAULT_ABI, .op = VAULT_OWNER_INFO, .owner = r->owner};
  vault_response_t info = {0};
  bool crypto_only =
      r->op == VAULT_FROM_SEED ||
      (r->op >= VAULT_PUBLIC && r->op <= VAULT_SIGN) ||
      (r->op >= VAULT_SCHNORR_GENERATE && r->op <= VAULT_SLIP21) ||
      r->op == VAULT_ED_SIGN_EXT;
  if (!vault_call(&check, &info) ||
      (storage_is_unlocked() != sectrue && !(info.value && crypto_only)))
    return false;
  app_busy = true;
  bool ecc = r->op == VAULT_ECDH || r->op == VAULT_NIST_PUBLIC ||
             (r->op >= VAULT_FROM_SEED && r->op <= VAULT_SIGN) ||
             (r->op >= VAULT_SCHNORR_GENERATE && r->op <= VAULT_SCHNORR_SIGN);
  bool own = ecc && !zkp_context_is_initialized();
  bool ready = !own || zkp_context_init() == 0;
  bool ok = ready && app_execute(r, out, message, length);
  if (own && ready) zkp_context_destroy();
  memzero(app_scratch, sizeof(app_scratch));
  memzero(app_used, sizeof(app_used));
  app_busy = false;
  return ok;
}
static bool vault_coreapp_call(const vault_request_t *r,
                               vault_response_t *out) {
  if (r->op == VAULT_SLIP21) return vault_slip21_call(r, out);
  if (r->op <= VAULT_IMPORT_BYTES || r->op == VAULT_AUTHORIZE_LOCKED)
    return vault_call(r, out);
  app_vault_command_t c = {.abi = r->abi,
                           .op = r->op,
                           .owner = r->owner,
                           .arg = r->arg,
                           .length = r->length,
                           .child_num = r->child_num,
                           .blob = &r->blob,
                           .curve = r->curve,
                           .data = r->data};
  return app_dispatch(&c, out, NULL, 0);
}
static inline __attribute__((always_inline)) bool app_message_into(
    const vault_message_request_t *r, const uint8_t *message, size_t length,
    vault_response_t *out, uint8_t *snapshot) {
  vault_message_request_t copy = *r;
  memcpy(snapshot, message, length);
  app_vault_command_t c = {.abi = copy.abi,
                           .op = copy.op,
                           .owner = copy.owner,
                           .arg = copy.arg,
                           .length = copy.length,
                           .blob = &copy.blob,
                           .extension = &copy.extension};
  bool supported = copy.op == VAULT_ED_SIGN || copy.op == VAULT_ED_SIGN_EXT ||
                   copy.op == VAULT_CHACHA_TAG ||
                   copy.op == VAULT_KEYVALUE_DERIVE;
  bool ok = supported && app_dispatch(&c, out, snapshot, length);
  memzero(&copy, sizeof(copy));
  return ok;
}
static __attribute__((noinline)) bool app_message_small(
    const vault_message_request_t *r, const uint8_t *message, size_t length,
    vault_response_t *out) {
  uint8_t snapshot[256];
  bool ok = app_message_into(r, message, length, out, snapshot);
  memzero(snapshot, sizeof(snapshot));
  return ok;
}
static uint8_t app_large_message[VAULT_ED25519_MAX_MESSAGE];
static bool app_large_message_busy;
static __attribute__((noinline)) bool app_message_large(
    const vault_message_request_t *r, const uint8_t *message, size_t length,
    vault_response_t *out) {
  if (app_large_message_busy) return false;
  app_large_message_busy = true;
  bool ok = app_message_into(r, message, length, out, app_large_message);
  memzero(app_large_message, sizeof(app_large_message));
  app_large_message_busy = false;
  return ok;
}
static bool vault_coreapp_call_message(const vault_message_request_t *r,
                                       const uint8_t *message, size_t length,
                                       vault_response_t *out) {
  memset(out, 0, sizeof(*out));
  if (!message || !length || length > VAULT_ED25519_MAX_MESSAGE) return false;
  if (length <= 256) return app_message_small(r, message, length, out);
  return app_message_large(r, message, length, out);
}
#endif
