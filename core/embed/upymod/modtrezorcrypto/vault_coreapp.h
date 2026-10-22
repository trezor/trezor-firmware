/* SPDX-License-Identifier: GPL-3.0-or-later */
/* AES-only migration checkpoint. Private plaintext is allowed in native coreapp
 * scratch, never Python objects. The next stages move these operations into
 * the kernel and finally remove VAULT_OPEN_NATIVE. */
#ifndef TREZOR_COREAPP_VAULT_H
#define TREZOR_COREAPP_VAULT_H
#include <sec/storage.h>
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
#include "zkp_bip340.h"
#include "zkp_context.h"
#define VAULT_RECORD_SIZE VAULT_SECRET_SIZE
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
  switch (id) {
    case 0:
      return SECP256K1_NAME;
    case 1:
      return NIST256P1_NAME;
    case 2:
      return ED25519_NAME;
    default:
      return NULL;
  }
}
static bool app_secret_curve_allowed(const char *name) {
  for (uint8_t i = 0; app_secret_curve_name(i); i++)
    if (!strcmp(name, app_secret_curve_name(i))) return true;
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
  data[106] = n->curve == get_curve_by_name(NIST256P1_NAME) ? 1
              : n->curve == get_curve_by_name(ED25519_NAME) ? 2
                                                            : 0;
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
      memcmp(p->node.private_key_extension, (uint8_t[32]){0}, 32))
    return false;
  vault_request_t r = {
      .abi = VAULT_ABI,
      .op = VAULT_IMPORT_BYTES,
      .owner = owner,
      .arg = kind,
      .length = kind == SECRET_BYTES ? length : VAULT_NODE_SIZE};
  app_secret_encode(kind, length, p, r.data);
  vault_response_t out = {0};
  bool ok = vault_call(&r, &out);
  if (ok) *blob = out.blob;
  memzero(&r, sizeof(r));
  memzero(&out, sizeof(out));
  return ok;
}
static bool app_node_has_private_key(const HDNode *node) {
  /* Public-only nodes carry an all-zero private key. */
  return memcmp(node->private_key, (uint8_t[32]){0}, 32) != 0;
}

/* All vault curves use HASH160 fingerprints. Avoid the generic runtime hash
 * dispatcher, which links unrelated coin hash implementations into the kernel.
 * Check the invariant explicitly before admitting another curve. */
static bool app_vault_fingerprint(HDNode *node, uint32_t *fingerprint) {
  if (node->curve->hasher_pubkey != HASHER_SHA2_RIPEMD ||
      hdnode_fill_public_key(node) != 0)
    return false;
  uint8_t digest[32] = {0}, hash160[20] = {0};
  sha256_Raw(node->public_key, sizeof(node->public_key), digest);
  ripemd160(digest, sizeof(digest), hash160);
  *fingerprint = ((uint32_t)hash160[0] << 24) | ((uint32_t)hash160[1] << 16) |
                 ((uint32_t)hash160[2] << 8) | hash160[3];
  memzero(digest, sizeof(digest));
  memzero(hash160, sizeof(hash160));
  return true;
}

/* Kernel-local view of a validated snapshot. Public inputs stay in the
 * originating snapshot; compact message requests need no full RPC envelope. */
typedef struct {
  uint32_t abi, op, owner, arg, length, child_num;
  const vault_blob_t *blob;
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
      if (r->length != 4) break;
      made = app_secret_open(r->blob, r->owner, SECRET_NODE, NULL);
      if (!made) break;
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
      if (!p || r->arg > 1 || !(made = app_secret_scratch_take())) break;
      made_kind = SECRET_BYTES;
      made_length = 32;
      memcpy(made->bytes,
             r->arg ? p->node.private_key_extension : p->node.private_key, 32);
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
      uint8_t recovery = 0;
      if (!key || len != 32 || r->length != 32 || r->arg > 1) break;
      ok = ecdsa_sign_digest(&secp256k1, key, r->data, out->signature + 1,
                             &recovery, NULL) == 0;
      if (ok) out->signature[0] = 27 + recovery + 4 * r->arg;
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
      if (length != 32 || r->arg > 1) break;
      if (r->op == VAULT_NIST_PUBLIC) {
        if (r->length) break;
        ok = (r->arg ? ecdsa_get_public_key33(&nist256p1, key->bytes,
                                              out->signature)
                     : ecdsa_get_public_key65(&nist256p1, key->bytes,
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
    case VAULT_SEED_STORAGE: {
      char mnemonic[256] = {0};
      uint8_t backup_type = 0;
      uint16_t len = 0;
      /* Narrow BIP39 path; SLIP39 is explicitly unsupported. */
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
      memzero(mnemonic, sizeof(mnemonic));
      break;
    }
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
  if (!vault_call(&check, &info) || storage_is_unlocked() != sectrue)
    return false;
  app_busy = true;
  bool ecc = (r->op >= VAULT_FROM_SEED && r->op <= VAULT_SIGN) ||
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
  if (r->op <= VAULT_SIGN || r->op == VAULT_SEED_STORAGE ||
      (r->op >= VAULT_SCHNORR_GENERATE && r->op <= VAULT_SCHNORR_SIGN))
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
                           .blob = &copy.blob};
  bool ok = copy.op == VAULT_ED_SIGN && app_dispatch(&c, out, snapshot, length);
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
static __attribute__((noinline)) bool app_message_large(
    const vault_message_request_t *r, const uint8_t *message, size_t length,
    vault_response_t *out) {
  uint8_t snapshot[VAULT_ED25519_MAX_MESSAGE];
  bool ok = app_message_into(r, message, length, out, snapshot);
  memzero(snapshot, sizeof(snapshot));
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
