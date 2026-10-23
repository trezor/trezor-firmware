/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <sec/vault.h>
#include "curves.h"
#include "ecdsa.h"
#include "ed25519-donna/ed25519-keccak.h"
#include "ed25519-donna/ed25519.h"
#include "hmac.h"
#include "nist256p1.h"
#include "rand.h"
#include "ripemd160.h"
#include "secp256k1.h"
#include "sha2.h"
#include "store.h"
#include "zkp_bip340.h"
#include "zkp_context.h"
#ifndef VAULT_TEST
#include <sec/storage.h>
#include "bip39.h"
#endif

bool vault_storage_key_allowed(uint16_t key) {
  /* Strip public/writable-lock namespace flags as well: no alias bypass. */
  key &= 0x3fff;
  return key != 0x0102 && key != 0x0125;
}

void vault_wipe(void) {
  secret_revoke_all();
  /* Rotate the per-boot key: every outstanding blob stops authenticating. */
  vault_seal_wipe();
}

void vault_revoke_caller(uintptr_t caller) {
  for (size_t i = 0; i < SECRET_OWNER_CAPACITY; i++)
    if (secret_owners[i].caller == caller && secret_owners[i].id)
      secret_owner_destroy(secret_owners[i].id);
}

static bool node_has_private_key(const HDNode *node) {
  /* Public-only ECDSA nodes carry an all-zero private key. Ed25519 imports
   * require a private seed, and an all-zero seed is valid. */
  return !node->curve->params ||
         memcmp(node->private_key, (uint8_t[32]){0}, 32) != 0;
}

/* All vault curves use HASH160 fingerprints. Avoid the generic runtime hash
 * dispatcher, which links unrelated coin hash implementations into the kernel.
 * Check the invariant explicitly before admitting another curve. */
static bool vault_fingerprint(HDNode *node, uint32_t *fingerprint) {
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
} vault_command_t;

/* The dispatcher scopes one transient ZKP context around wallet operations. */
static bool vault_schnorr(const vault_command_t *r, vault_response_t *out,
                          secret_payload_t **made) {
  bool ok = false;
  size_t length = 0;
  secret_payload_t *key = NULL;
  if (r->op == VAULT_SCHNORR_GENERATE) {
    *made = secret_scratch_take();
    if (!*made) goto cleanup;
    do {
      random_buffer((*made)->bytes, 32);
    } while (!hdnode_validate_private_key(get_curve_by_name(SECP256K1_NAME),
                                          (*made)->bytes));
    ok = true;
    goto cleanup;
  }
  key = secret_open(r->blob, r->owner, SECRET_BYTES, &length);
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
          !(*made = secret_scratch_take()))
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

/* No caller-owned pointers are used by the implementation. The syscall verifier
 * copies requests before entry and copies only this public response out. */
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

/* SLIP-0021: each label replaces the 64-byte node by
 * HMAC-SHA512(node[0:32], 0x00 || label). Labels are length-prefixed. */
static bool vault_slip21_derive(uint8_t node[64], const uint8_t *data,
                                size_t length) {
  static const uint8_t zero = 0;
  for (size_t i = 0; i < length;) {
    size_t n = data[i++];
    if (n > length - i) return false;
    HMAC_SHA512_CTX ctx = {0};
    hmac_sha512_Init(&ctx, node, 32);
    hmac_sha512_Update(&ctx, &zero, 1);
    hmac_sha512_Update(&ctx, data + i, n);
    hmac_sha512_Final(&ctx, node);
    i += n;
  }
  return true;
}
/* Evolu hands its node to the host: TREZOR/Evolu, or TREZOR/Evolu Index plus
 * one index label. No other SLIP-0021 node leaves the vault. */
static bool vault_slip21_exportable(const uint8_t *data, size_t length) {
  static const uint8_t evolu[] = "\006TREZOR\005Evolu";
  static const uint8_t evolu_index[] = "\006TREZOR\013Evolu Index";
  const size_t evolu_len = sizeof(evolu) - 1,
               index_len = sizeof(evolu_index) - 1;
  if (length == evolu_len && !memcmp(data, evolu, evolu_len)) return true;
  return length > index_len + 1 && !memcmp(data, evolu_index, index_len) &&
         data[index_len] == length - index_len - 1;
}

/* Noinline: the SLIP-0021 workspace stays off every other vault op's frame. */
static __attribute__((noinline)) bool vault_slip21(const vault_command_t *r,
                                                   vault_response_t *out,
                                                   secret_payload_t **made,
                                                   size_t *made_length) {
  bool root = r->arg & VAULT_SLIP21_ROOT;
  uint32_t output = r->arg & ~(uint32_t)VAULT_SLIP21_ROOT;
  if (output != VAULT_SLIP21_NODE && output != VAULT_SLIP21_KEY &&
      output != VAULT_SLIP21_EXPORT)
    return false;
  if (output == VAULT_SLIP21_EXPORT &&
      !(root && vault_slip21_exportable(r->data, r->length)))
    return false;
  size_t len = 0;
  secret_payload_t *src = secret_open(r->blob, r->owner, SECRET_BYTES, &len);
  if (!src || (!root && len != 64)) return false;
  uint8_t node[64] = {0};
  if (root) {
    static const char salt[] = "Symmetric key seed";
    hmac_sha512((const uint8_t *)salt, sizeof(salt) - 1, src->bytes, len, node);
  } else {
    memcpy(node, src->bytes, 64);
  }
  bool ok = false;
  if (vault_slip21_derive(node, r->data, r->length)) {
    if (output == VAULT_SLIP21_EXPORT) {
      memcpy(out->signature, node, 64);
      ok = true;
    } else if ((*made = secret_scratch_take())) {
      *made_length = output == VAULT_SLIP21_KEY ? 32 : 64;
      memcpy((*made)->bytes, output == VAULT_SLIP21_KEY ? node + 32 : node,
             *made_length);
      ok = true;
    }
  }
  memzero(node, sizeof(node));
  return ok;
}

static bool vault_execute(uintptr_t caller, const vault_command_t *r,
                          vault_response_t *out, bool unlocked,
                          const uint8_t *message, size_t message_length) {
  memset(out, 0, sizeof(*out));
  if (!caller || r->abi != VAULT_ABI || r->length > VAULT_DATA_SIZE ||
      (r->curve && !memchr(r->curve, 0, VAULT_CURVE_SIZE)))
    return false;
  secret_owner_t *owner = secret_owner_find(r->owner);
  if (r->op == VAULT_OWNER_CREATE) {
    if (r->owner && (!owner || owner->caller != caller)) return false;
    uint32_t id = secret_owner_create(r->owner);
    owner = secret_owner_find(id);
    if (!owner) return false;
    owner->caller = caller;
    out->value = id;
    return true;
  }
  if (r->op == VAULT_RESET || r->op == VAULT_REVOKE_REQUESTS) {
    for (size_t i = 0; i < SECRET_OWNER_CAPACITY; i++)
      if (secret_owners[i].id && secret_owners[i].caller == caller &&
          (r->op == VAULT_RESET || secret_owners[i].parent))
        secret_owner_destroy(secret_owners[i].id);
    return true;
  }
  if (!owner || owner->caller != caller) return false;
  if (r->op == VAULT_OWNER_INFO) {
    out->parent = owner->parent;
    return true;
  }
  if (r->op == VAULT_OWNER_DESTROY) {
    secret_owner_destroy(r->owner);
    return true;
  }
  /* Session existence survives lock. Every operation using secret state is
   * independently gated by trusted storage state. Cleanup remains available. */
  if (!unlocked) return false;
  /* The result, if any, is sealed for `made_owner` into out->blob. */
  secret_payload_t *made = NULL;
  secret_kind_t made_kind = SECRET_NODE;
  size_t made_length = sizeof(HDNode);
  uint32_t made_owner = r->owner;
  HDNode *node = NULL;
  bool ok = false;
  switch (r->op) {
    case VAULT_RETAIN: {
      /* Re-seal a request secret for its session. */
      if (r->arg != SECRET_BYTES && r->arg != SECRET_NODE) break;
      if (!owner->parent || secret_get32(r->blob->bytes) != r->owner) break;
      made_kind = r->arg;
      made = secret_open(r->blob, r->owner, made_kind, &made_length);
      made_owner = owner->parent;
      ok = made != NULL;
      break;
    }
    case VAULT_IMPORT_BYTES:
      if (!r->length || r->length > VAULT_SECRET_SIZE ||
          !(made = secret_scratch_take()))
        break;
      made_kind = SECRET_BYTES;
      made_length = r->length;
      memcpy(made->bytes, r->data, r->length);
      ok = true;
      break;
    case VAULT_FROM_SEED: {
      if (!secret_curve_allowed(r->curve)) break;
      const uint8_t *seed = r->data;
      size_t len = r->length;
      if (r->arg) {
        secret_payload_t *p =
            secret_open(r->blob, r->owner, SECRET_BYTES, &len);
        seed = p ? p->bytes : NULL;
      }
      if (!seed || !len || !(made = secret_scratch_take())) break;
      ok = hdnode_from_seed(seed, len, r->curve, &made->node) != 0;
      break;
    }
    case VAULT_IMPORT_NODE: {
      if (!secret_curve_allowed(r->curve)) break;
      /* Wire format: chain[32], private[32], public[33], presence flags.
       * Ed25519 public keys start with zero; do not infer presence from it. */
      if (r->length != 98 || !r->data[97] || r->data[97] > 3 ||
          !(made = secret_scratch_take()))
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
      secret_payload_t *p = secret_open(r->blob, r->owner, SECRET_NODE, NULL);
      if (!p) break;
      node = &p->node;
      bool computed = !node->is_public_key_set;
      if (hdnode_fill_public_key(node)) break;
      out->depth = node->depth;
      out->child_num = node->child_num;
      out->value = secret_curve_id(node);
      memcpy(out->chain_code, node->chain_code, 32);
      memcpy(out->public_key, node->public_key, 33);
      /* Hand back a blob that carries the computed key, so the client does
       * not pay for the point multiplication again. */
      if (computed) {
        made = p;
        made_owner = secret_get32(r->blob->bytes);
      }
      ok = true;
      break;
    }
    case VAULT_DERIVE: {
      if (r->length != 4 || r->arg > 1) break;
      made = secret_open(r->blob, r->owner, SECRET_NODE, NULL);
      if (!made) break;
      if (!r->arg && !node_has_private_key(&made->node)) break;
      made_owner = secret_get32(r->blob->bytes);
      uint32_t index;
      memcpy(&index, r->data, 4);
      if (!vault_fingerprint(&made->node, &out->value)) break;
      ok = (r->arg ? hdnode_public_ckd(&made->node, index)
                   : hdnode_private_ckd(&made->node, index)) != 0;
      break;
    }
    case VAULT_SNAPSHOT: {
      secret_payload_t *p = secret_open(r->blob, r->owner, SECRET_NODE, NULL);
      if (!p || !node_has_private_key(&p->node) || r->arg > 1 ||
          !(made = secret_scratch_take()))
        break;
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
        secret_payload_t *p =
            secret_open(r->blob, r->owner, SECRET_BYTES, &len);
        key = p ? p->bytes : NULL;
      } else {
        /* Sign from a node in place: no snapshot, no second key copy. */
        secret_payload_t *p = secret_open(r->blob, r->owner, SECRET_NODE, NULL);
        if (p && p->node.curve && p->node.curve->params == &secp256k1 &&
            node_has_private_key(&p->node)) {
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
      secret_payload_t *key =
          secret_open(r->blob, r->owner, SECRET_BYTES, &length);
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
      secret_payload_t *key =
          secret_open(r->blob, r->owner, SECRET_BYTES, &length);
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
    case VAULT_SLIP21:
      made_kind = SECRET_BYTES;
      ok = vault_slip21(r, out, &made, &made_length);
      break;
    case VAULT_SCHNORR_GENERATE:
    case VAULT_SCHNORR_PUBLIC:
    case VAULT_SCHNORR_TWEAK:
    case VAULT_SCHNORR_SIGN:
      made_kind = SECRET_BYTES;
      made_length = 32;
      ok = vault_schnorr(r, out, &made);
      break;
#ifndef VAULT_TEST
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
          (made = secret_scratch_take())) {
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
#endif
    default:
      break;
  }
  if (ok && made)
    ok = secret_seal(made_owner, made_kind, made_length, made, &out->blob);
  if (!ok) memzero(out, sizeof(*out));
  return ok;
}

static bool vault_dispatch_inner(uintptr_t caller, const vault_command_t *r,
                                 vault_response_t *out, bool unlocked,
                                 const uint8_t *message, size_t length) {
  if (secret_busy) {
    memzero(out, sizeof(*out));
    return false;
  }
  secret_transaction_begin();
  /* All wallet ECC operations can reach the ZKP backend, including HDNode
   * public-key caching and ECDSA after enabling kernel Schnorr support. */
  bool ecc = (r->op >= VAULT_FROM_SEED && r->op <= VAULT_SIGN) ||
             (r->op >= VAULT_SCHNORR_GENERATE && r->op <= VAULT_SCHNORR_SIGN);
  bool own_context = ecc && !zkp_context_is_initialized();
  bool ready = !own_context || zkp_context_init() == 0;
  bool ok = ready && vault_execute(caller, r, out, unlocked, message, length);
  if (own_context && ready) zkp_context_destroy();
  if (!ready) memzero(out, sizeof(*out));
  if (!secret_transaction_end()) {
    memzero(out, sizeof(*out));
    ok = false;
  }
  return ok;
}

bool vault_dispatch(uintptr_t caller, const vault_request_t *r,
                    vault_response_t *out, bool unlocked) {
  vault_command_t command = {.abi = r->abi,
                             .op = r->op,
                             .owner = r->owner,
                             .arg = r->arg,
                             .length = r->length,
                             .child_num = r->child_num,
                             .blob = &r->blob,
                             .curve = r->curve,
                             .data = r->data};
  return vault_dispatch_inner(caller, &command, out, unlocked, NULL, 0);
}
bool vault_dispatch_message(uintptr_t caller, const vault_message_request_t *r,
                            const uint8_t *message, size_t length,
                            vault_response_t *out, bool unlocked) {
  if (r->op != VAULT_ED_SIGN || !message || !length ||
      length > VAULT_ED25519_MAX_MESSAGE) {
    memzero(out, sizeof(*out));
    return false;
  }
  vault_command_t command = {.abi = r->abi,
                             .op = r->op,
                             .owner = r->owner,
                             .arg = r->arg,
                             .length = r->length,
                             .blob = &r->blob};
  return vault_dispatch_inner(caller, &command, out, unlocked, message, length);
}

/* Separate noinline workspaces keep the large reservation off small calls.
 * Every buffer is bounded at compile time; no VLA or persistent workspace. */
static inline __attribute__((always_inline)) bool vault_snapshot_into(
    uintptr_t caller, const vault_message_request_t *request,
    const uint8_t *message, size_t length, vault_response_t *response,
    bool unlocked, uint8_t *snapshot) {
  vault_message_request_t copy = *request;
  memcpy(snapshot, message, length);
  bool ok = vault_dispatch_message(caller, &copy, snapshot, length, response,
                                   unlocked);
  memzero(&copy, sizeof(copy));
  return ok;
}

static __attribute__((noinline)) bool vault_snapshot_small(
    uintptr_t caller, const vault_message_request_t *request,
    const uint8_t *message, size_t length, vault_response_t *response,
    bool unlocked) {
  uint8_t snapshot[256];
  bool ok = vault_snapshot_into(caller, request, message, length, response,
                                unlocked, snapshot);
  memzero(snapshot, sizeof(snapshot));
  return ok;
}

static __attribute__((noinline)) bool vault_snapshot_large(
    uintptr_t caller, const vault_message_request_t *request,
    const uint8_t *message, size_t length, vault_response_t *response,
    bool unlocked) {
  uint8_t snapshot[VAULT_ED25519_MAX_MESSAGE];
  bool ok = vault_snapshot_into(caller, request, message, length, response,
                                unlocked, snapshot);
  memzero(snapshot, sizeof(snapshot));
  return ok;
}

/* Ed25519 reads twice; both passes must use one immutable kernel snapshot. */
bool vault_message_snapshot(uintptr_t caller,
                            const vault_message_request_t *request,
                            const uint8_t *message, size_t length,
                            vault_response_t *response, bool unlocked) {
  if (!message || !length || length > VAULT_ED25519_MAX_MESSAGE) {
    memzero(response, sizeof(*response));
    return false;
  }
  if (length <= 256)
    return vault_snapshot_small(caller, request, message, length, response,
                                unlocked);
  return vault_snapshot_large(caller, request, message, length, response,
                              unlocked);
}

#if defined(TREZOR_EMULATOR) && !defined(VAULT_TEST)
bool vault_call(const vault_request_t *request, vault_response_t *response) {
  vault_request_t copy = *request;
  bool ok =
      vault_dispatch(1, &copy, response, storage_is_unlocked() == sectrue);
  memzero(&copy, sizeof(copy));
  return ok;
}
bool vault_call_message(const vault_message_request_t *request,
                        const uint8_t *message, size_t length,
                        vault_response_t *response) {
  return vault_message_snapshot(1, request, message, length, response,
                                storage_is_unlocked() == sectrue);
}

#endif

#ifndef VAULT_TEST
void systask_revoke_secrets(void *applet) {
  vault_revoke_caller((uintptr_t)applet);
}
#endif
