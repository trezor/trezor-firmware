/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <sec/vault.h>
#include "aes/aes.h"
#include "blake256.h"
#include "cardano.h"
#if USE_MONERO
#include "ed25519-donna/ed25519-donna.h"
#include "sha3.h"
#endif
#include "chacha20poly1305/rfc7539.h"
#include "consteq.h"
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
#include "slip21.h"
#include "store.h"
#if !defined(TREZOR_EMULATOR) && !defined(VAULT_TEST)
#include <sys/stack_utils.h>
#define vault_scrub_stack() clear_unused_stack()
#else
#define vault_scrub_stack() ((void)0)
#endif
#include "zkp_bip340.h"
#include "zkp_context.h"
#ifndef VAULT_TEST
#include <sec/storage.h>
#include "bip39.h"
#include "pbkdf2.h"
#endif

/* Kernel-only: 1 while the stored mnemonic awaits its first backup. */
#define VAULT_BACKUP_PENDING 0x0129
/* One repeated backup, granted by a matching backup check until lock. */
static bool vault_backup_granted;

bool vault_storage_key_allowed(uint16_t key) {
  /* Strip public/writable-lock namespace flags as well: no alias bypass. */
  key &= 0x3fff;
  return key != 0x0102 && key != 0x0125 && key != VAULT_BACKUP_PENDING;
}
#ifndef VAULT_TEST
/* The mnemonic is write-once: the first store goes to the canonical private
 * slot; replacing it requires a storage wipe. Only the kernel creates the THP
 * device secret, the backup state and the binary mnemonic, so coreapp can
 * plant none of them. */
bool vault_storage_write_allowed(uint16_t key) {
  return vault_storage_key_allowed(key) ||
         (key == 0x0102 && storage_has(key) != sectrue);
}

static bool vault_backup_set_pending(uint8_t pending) {
  return storage_set(VAULT_BACKUP_PENDING, &pending, 1) == sectrue;
}

/* A new mnemonic may be disclosed once for its first backup. Coreapp chose or
 * received it, so that disclosure reveals nothing coreapp did not have. */
void vault_storage_written(uint16_t key) {
  if (key == 0x0102) vault_backup_set_pending(1);
}

/* Firmware upgrade: adopt the backup state once, right after an unlock and
 * before coreapp can write private storage to fake it. */
void vault_storage_unlocked(void) {
  if (storage_has(VAULT_BACKUP_PENDING) == sectrue ||
      storage_has(0x0102) != sectrue)
    return;
  uint8_t needs_backup = 0;
  uint16_t length = 0;
  vault_backup_set_pending(storage_get(0x0107, &needs_backup, 1, &length) ==
                               sectrue &&
                           length == 1 && needs_backup == 1);
}

void vault_storage_locked(void) { vault_backup_granted = false; }

/* Consumes the permission for one disclosure of the stored mnemonic. */
static bool vault_backup_take(void) {
  uint8_t pending = 0;
  uint16_t length = 0;
  bool first =
      storage_get(VAULT_BACKUP_PENDING, &pending, 1, &length) == sectrue &&
      length == 1 && pending == 1;
  bool granted = vault_backup_granted;
  vault_backup_granted = false;
  if (first) return vault_backup_set_pending(0);
  return granted;
}
#endif

void vault_wipe(void) {
  vault_backup_granted = false;
  secret_revoke_all();
  /* Rotate the per-boot key: every outstanding blob stops authenticating. */
  vault_seal_wipe();
}

void vault_revoke_caller(uintptr_t caller) {
  for (size_t i = 0; i < SECRET_OWNER_CAPACITY; i++)
    if (secret_owners[i].caller == caller && secret_owners[i].id)
      secret_owner_destroy(secret_owners[i].id);
}

#ifndef VAULT_TEST
#if USE_CARDANO
/* Cardano Icarus entropy comes from the stored words, never from the copy at
 * 0x0125: a coreapp could plant that copy while it was missing, and the
 * planted value would outlive firmware updates. Returns the length in bytes,
 * or 0. Noinline: the words stay off the shared operation frame. */
static __attribute__((noinline)) size_t
vault_stored_mnemonic_bits(uint8_t bits[33]) {
  char mnemonic[256] = {0};
  uint16_t length = 0;
  size_t n = 0;
  if (storage_get(0x0102, mnemonic, sizeof(mnemonic) - 1, &length) == sectrue &&
      length && length < sizeof(mnemonic) && !memchr(mnemonic, 0, length))
    n = (mnemonic_to_bits(mnemonic, bits) + 7) / 8;
  memzero(mnemonic, sizeof(mnemonic));
  if (n > 33) n = 0;
  return n;
}
#endif

/* SLIP-0039 decrypts the stored EMS without exposing either half to coreapp.
 * The identifier and exponent are read from the same protected storage. */
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

static bool node_has_private_key(const HDNode *node) {
  /* Public-only ECDSA nodes carry an all-zero private key. Ed25519 imports
   * require a private seed, and an all-zero seed is valid. */
  return !node->curve->params ||
         memcmp(node->private_key, (uint8_t[32]){0}, 32) != 0;
}

/* A node's private scalar keeps its curve when it leaves the node.
 * Cardano nodes still map to Ed25519 until they sign in place. */
static uint8_t node_key_type(const HDNode *node) {
  if (node->curve->params == &secp256k1) return VAULT_KEY_SECP256K1;
  if (node->curve->params == &nist256p1) return VAULT_KEY_NIST256P1;
  if (node->curve == get_curve_by_name(CURVE25519_NAME))
    return VAULT_KEY_X25519;
  return VAULT_KEY_ED25519_SEED;
}

/* Fingerprints use HASH160 (BLAKE-256 for Decred). Selecting those two
 * implementations directly avoids pulling every coin's address/checksum
 * hasher into the kernel while preserving all admitted curves. */
static bool vault_fingerprint(HDNode *node, uint32_t *fingerprint) {
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

/* Kernel-local view of a validated snapshot. Public inputs stay in the
 * originating snapshot; compact message requests need no full RPC envelope. */
typedef struct {
  uint32_t abi, op, owner, arg, length, child_num;
  const vault_blob_t *blob;
  const vault_blob_t *extension;
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
  key = secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_SECP256K1), &length);
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
                                                   size_t *made_length,
                                                   uint8_t *made_type) {
  bool root = r->arg & VAULT_SLIP21_ROOT;
  uint32_t output = r->arg & ~(uint32_t)VAULT_SLIP21_ROOT;
  if (output != VAULT_SLIP21_NODE && output != VAULT_SLIP21_KEY &&
      output != VAULT_SLIP21_EXPORT)
    return false;
  if (output == VAULT_SLIP21_EXPORT &&
      !(root && vault_slip21_exportable(r->data, r->length)))
    return false;
  /* Roots come from the wallet seed, or from the THP device secret for its
   * credential keys; only the wallet seed may be exported from. */
  uint32_t sources =
      !root ? VAULT_KEY(VAULT_KEY_SLIP21_NODE)
      : output == VAULT_SLIP21_EXPORT
          ? VAULT_KEY(VAULT_KEY_SEED)
          : VAULT_KEY(VAULT_KEY_SEED) | VAULT_KEY(VAULT_KEY_THP_DEVICE);
  size_t len = 0;
  secret_payload_t *src = secret_open(r->blob, r->owner, sources, &len);
  if (!src || (!root && len != 64)) return false;
  uint8_t node[64] = {0};
  if (root) {
    slip21_from_seed(src->bytes, len, node);
  } else {
    memcpy(node, src->bytes, 64);
  }
  bool ok = false;
  if (slip21_derive_path(node, r->data, r->length)) {
    if (output == VAULT_SLIP21_EXPORT) {
      memcpy(out->signature, node, 64);
      ok = true;
    } else if ((*made = secret_scratch_take())) {
      *made_length = output == VAULT_SLIP21_KEY ? 32 : 64;
      *made_type = output == VAULT_SLIP21_KEY ? VAULT_KEY_SYMMETRIC
                                              : VAULT_KEY_SLIP21_NODE;
      memcpy((*made)->bytes, output == VAULT_SLIP21_KEY ? node + 32 : node,
             *made_length);
      ok = true;
    }
  }
  memzero(node, sizeof(node));
  return ok;
}

#if USE_MONERO
static
    __attribute__((noinline)) bool vault_monero_public(const vault_command_t *r,
                                                       vault_response_t *out) {
  if (r->length != 8 || r->arg > 1) return false;
  secret_payload_t *key =
      secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_NODE), NULL);
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
    secret_put32(data + 40, major);
    secret_put32(data + 44, minor);
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

/* No crypto transaction or storage access: this entry also runs while the
 * kernel is suspended in an unprivileged storage progress callback. */
bool vault_lifecycle_dispatch(uintptr_t caller,
                              const vault_lifecycle_request_t *r,
                              vault_lifecycle_response_t *out) {
  memset(out, 0, sizeof(*out));
  if (!caller || r->abi != VAULT_ABI || !vault_is_lifecycle(r->op) ||
      secret_busy)
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
    out->value = owner->parent && owner->authorized_locked;
    return true;
  }
  if (r->op == VAULT_OWNER_DESTROY) {
    secret_owner_destroy(r->owner);
    return true;
  }
  return false;
}

static bool vault_execute(uintptr_t caller, const vault_command_t *r,
                          vault_response_t *out, bool unlocked,
                          const uint8_t *message, size_t message_length) {
  memset(out, 0, sizeof(*out));
  if (!caller || r->abi != VAULT_ABI || r->length > VAULT_DATA_SIZE ||
      (r->curve && !memchr(r->curve, 0, VAULT_CURVE_SIZE)))
    return false;
  secret_owner_t *owner = secret_owner_find(r->owner);
  if (!owner || owner->caller != caller) return false;
  if (r->op == VAULT_AUTHORIZE_LOCKED) {
    /* Only an unlocked, live request can grant the existing CoinJoin
     * session authorization. Revocation is also allowed while locked. */
    if (r->arg > 3 || !owner->parent) return false;
    if (r->arg == 3) {
      /* A transaction confirmed while unlocked may finish after autolock.
       * This grant belongs only to this request, never its session. */
      if (!unlocked && !owner->authorized_locked) return false;
      owner->authorized_locked = true;
      return true;
    }
    secret_owner_t *session = secret_owner_find(owner->parent);
    if (!session || session->caller != caller) return false;
    if (r->arg == 2) {
      if (!session->authorized_locked) return false;
      owner->authorized_locked = true;
      return true;
    }
    if (r->arg && !unlocked && !session->authorized_locked) return false;
    session->authorized_locked = r->arg;
    return true;
  }
  /* Session existence survives lock. Every operation using secret state is
   * independently gated by trusted storage state. Cleanup remains available. */
  /* A confirmed CoinJoin authorization intentionally survives screen lock.
   * Keep storage reads/imports and backup disclosure gated by real unlock. */
  bool authorized_locked = owner->parent && owner->authorized_locked;
  bool crypto_only =
      r->op == VAULT_RETAIN || r->op == VAULT_FROM_SEED ||
      (r->op >= VAULT_PUBLIC && r->op <= VAULT_SIGN) ||
      (r->op >= VAULT_SCHNORR_GENERATE && r->op <= VAULT_SLIP21) ||
      r->op == VAULT_ED_SIGN_EXT;
  volatile bool unlocked_check = unlocked || (authorized_locked && crypto_only);
  if (!unlocked_check) return false;
  /* The result, if any, is sealed for `made_owner` into out->blob. */
  secret_payload_t *made = NULL;
  uint8_t made_type = VAULT_KEY_NODE;
  size_t made_length = sizeof(HDNode);
  uint32_t made_owner = r->owner;
  HDNode *node = NULL;
  bool ok = false;
  switch (r->op) {
    case VAULT_RETAIN: {
      /* Re-seal a request secret for its session. */
      if (r->arg != SECRET_BYTES && r->arg != SECRET_NODE) break;
      if (!owner->parent || secret_get32(r->blob->bytes) != r->owner) break;
      made = secret_open(r->blob, r->owner,
                         r->arg == SECRET_NODE ? VAULT_KEY(VAULT_KEY_NODE)
                                               : VAULT_KEY_ANY_BYTES,
                         &made_length);
      /* Retention never changes a type; the header authenticated above. */
      made_type = r->blob->bytes[6];
      made_owner = owner->parent;
      ok = made != NULL;
      break;
    }
    case VAULT_IMPORT_BYTES:
      /* Any type but a node: coreapp knows this plaintext, so nothing the
       * kernel computes from it reveals more. The range check comes first:
       * arg is a request value, and must never reach a shift unchecked. */
      if (!r->length || r->length > VAULT_SECRET_SIZE ||
          r->arg <= VAULT_KEY_NODE || r->arg >= VAULT_KEY_TYPE_END ||
          !(made = secret_scratch_take()))
        break;
      made_type = r->arg;
      made_length = r->length;
      memcpy(made->bytes, r->data, r->length);
      ok = true;
      break;
    case VAULT_THP_DERIVE: {
      size_t length = 0;
      secret_payload_t *seed = secret_open(
          r->blob, r->owner, VAULT_KEY(VAULT_KEY_THP_DEVICE), &length);
      if (!seed || length != 16 || !(made = secret_scratch_take())) break;
      /* Legacy SLIP-10 curve25519 root and hardened 0x80544850 child.
       * Independent of the restricted wallet HDNode curve implementation. */
      uint8_t root[64] = {0}, child[64] = {0}, data[37] = {0};
      hmac_sha512((const uint8_t *)"curve25519 seed", 15, seed->bytes, 16,
                  root);
      memcpy(data + 1, root, 32);
      data[33] = 0x80;
      data[34] = 0x54;
      data[35] = 0x48;
      data[36] = 0x50;
      hmac_sha512(root + 32, 32, data, sizeof(data), child);
      memcpy(made->bytes, child, 32);
      memzero(root, sizeof(root));
      memzero(child, sizeof(child));
      memzero(data, sizeof(data));
      made_type = VAULT_KEY_X25519;
      made_length = 32;
      ok = true;
      break;
    }
    case VAULT_THP_PUBLIC:
    case VAULT_THP_DH: {
      size_t length = 0;
      secret_payload_t *key =
          secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_X25519), &length);
      if (!key || length != 32 || (r->op == VAULT_THP_DH && r->length != 32))
        break;
      if (r->op == VAULT_THP_PUBLIC) {
        curve25519_scalarmult_basepoint(out->signature, key->bytes);
        ok = true;
      } else {
        curve25519_scalarmult(out->signature, key->bytes, r->data);
        uint8_t nonzero = 0;
        for (size_t i = 0; i < 32; i++) nonzero |= out->signature[i];
        ok = nonzero != 0;
      }
      break;
    }
#ifndef VAULT_TEST
    case VAULT_THP_STORAGE: {
      if (!(made = secret_scratch_take())) break;
      uint16_t length = 0;
      if (storage_has(0x0117) == sectrue) {
        ok = storage_get(0x0117, made->bytes, 16, &length) == sectrue &&
             length == 16;
      } else {
        random_buffer(made->bytes, 16);
        ok = storage_set(0x0117, made->bytes, 16) == sectrue;
      }
      made_type = VAULT_KEY_THP_DEVICE;
      made_length = 16;
      break;
    }
    case VAULT_THP_RESET: {
      /* Reset preserves the transport identity without exporting its seed.
       * All old vault records are revoked after this transaction completes. */
      uint8_t seed[16] = {0};
      uint16_t length = 0;
      if (storage_get(0x0117, seed, sizeof(seed), &length) == sectrue &&
          length == sizeof(seed)) {
        storage_wipe();
        ok = storage_set(0x0117, seed, sizeof(seed)) == sectrue;
      }
      memzero(seed, sizeof(seed));
      break;
    }
#endif
#if USE_CARDANO
    case VAULT_CARDANO: {
      /* 0: master secret, 1: SLIP-23, 2: Ledger, 3: Icarus input,
       * 4: Icarus stored mnemonic. Bit 8 selects a sealed input. */
      uint32_t mode = r->arg & 0xff;
      if (r->arg & ~0x1ffU || mode > 4) break;
      size_t length = r->length;
      const uint8_t *input = r->data;
      if (r->arg & 0x100) {
        /* Sealed input: a master secret for mode 0, a seed for modes 1-2. */
        if (mode > 2) break;
        secret_payload_t *src = secret_open(
            r->blob, r->owner,
            VAULT_KEY(mode ? VAULT_KEY_SEED : VAULT_KEY_CARDANO_SECRET),
            &length);
        if (!src) break;
        input = src->bytes;
      }
      if (!(made = secret_scratch_take())) break;
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
          binary_length = vault_stored_mnemonic_bits(binary);
          pass = input;
          pass_length = length;
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
            made_type = VAULT_KEY_CARDANO_SECRET;
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
      secret_payload_t *key =
          secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_NODE), NULL);
      /* Both scalar and nonce prefix come from one authenticated node. Never
       * permit the legacy two-record request or another curve's node. */
      if (!key || key->node.curve != &ed25519_cardano_info ||
          !node_has_private_key(&key->node) || !message || r->arg)
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
    case VAULT_CHACHA_TAG:
    case VAULT_CHACHA_OPEN: {
      size_t key_length = 0;
      secret_payload_t *key = secret_open(
          r->blob, r->owner, VAULT_KEY(VAULT_KEY_SYMMETRIC), &key_length);
      if (!key || key_length != 32) break;
      chacha20poly1305_ctx ctx = {0};
      if (r->op == VAULT_CHACHA_OPEN) {
        /* message: aad (arg bytes) | ciphertext | tag. Plaintext is released
         * only after the tag verifies, in one call per record. */
        if (!r->extension || !message || r->arg > 32 ||
            message_length < r->arg + 16 ||
            message_length - r->arg - 16 > VAULT_DATA_SIZE)
          break;
        size_t length = message_length - r->arg - 16;
        const uint8_t *ciphertext = message + r->arg;
        uint8_t tag[16] = {0};
        rfc7539_init(&ctx, key->bytes, r->extension->bytes);
        rfc7539_auth(&ctx, message, r->arg);
        chacha20poly1305_auth(&ctx, ciphertext, length);
        rfc7539_finish(&ctx, r->arg, length, tag);
        /* Authentication touched only Poly1305; the keystream is at block 1. */
        if (consteq(tag, ciphertext + length, 16)) {
          ECRYPT_encrypt_bytes(&ctx.chacha20, ciphertext, out->data, length);
          ok = true;
        }
        memzero(tag, sizeof(tag));
      } else if (r->op == VAULT_CHACHA_BLOCK) {
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
      /* arg selects the curve, and the key must be of that curve. */
      if (r->arg > 2) break;
      static const uint8_t ecdh_types[] = {
          VAULT_KEY_SECP256K1, VAULT_KEY_NIST256P1, VAULT_KEY_X25519};
      size_t length = 0;
      secret_payload_t *key = secret_open(
          r->blob, r->owner, VAULT_KEY(ecdh_types[r->arg]), &length);
      if (!key || length != 32) break;
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
      secret_payload_t *node =
          secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_NODE), NULL);
      if (!node || r->length != 64 || !(made = secret_scratch_take())) break;
      ok = hdnode_get_nem_shared_key(&node->node, r->data, r->data + 32, NULL,
                                     made->bytes) != 0;
      made_type = VAULT_KEY_SYMMETRIC;
      made_length = 32;
      break;
    }
#endif
    case VAULT_KEYVALUE_DERIVE: {
      secret_payload_t *key =
          secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_NODE), NULL);
      if (!key || key->node.curve != get_curve_by_name(SECP256K1_NAME) ||
          !node_has_private_key(&key->node) || !message || r->arg ||
          !(made = secret_scratch_take()))
        break;
      uint8_t digest[64] = {0};
      HMAC_SHA512_CTX ctx = {0};
      hmac_sha512_Init(&ctx, key->node.private_key, 32);
      hmac_sha512_Update(&ctx, message, message_length);
      hmac_sha512_Final(&ctx, digest);
      memcpy(made->bytes, digest, 32);
      memcpy(out->chain_code, digest + 32, 16);
      made_type = VAULT_KEY_SYMMETRIC;
      made_length = 32;
      memzero(digest, sizeof(digest));
      memzero(&ctx, sizeof(ctx));
      ok = true;
      break;
    }
    case VAULT_AES_CBC: {
      size_t length = 0;
      secret_payload_t *key = secret_open(
          r->blob, r->owner, VAULT_KEY(VAULT_KEY_SYMMETRIC), &length);
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
      if (!secret_curve_allowed(r->curve)) break;
      const uint8_t *seed = r->data;
      size_t len = r->length;
      if (r->arg) {
        secret_payload_t *p =
            secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_SEED), &len);
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
      secret_payload_t *p =
          secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_NODE), NULL);
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
       * not pay for the point multiplication again. Only for the active
       * owner's own node: results never outlive the request that made them. */
      if (computed && secret_get32(r->blob->bytes) == r->owner) made = p;
      ok = true;
      break;
    }
    case VAULT_DERIVE: {
      if (r->length != 4 || r->arg > 1) break;
      made = secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_NODE), NULL);
      if (!made) break;
      if (!r->arg && !node_has_private_key(&made->node)) break;
      /* The child is sealed for the active owner; only VAULT_RETAIN extends a
       * lifetime to the session. */
      uint32_t index;
      memcpy(&index, r->data, 4);
      if (!vault_fingerprint(&made->node, &out->value)) break;
      ok = (r->arg ? hdnode_public_ckd(&made->node, index)
                   : hdnode_private_ckd(&made->node, index)) != 0;
      break;
    }
    case VAULT_SNAPSHOT: {
      secret_payload_t *p =
          secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_NODE), NULL);
      if (!p || !node_has_private_key(&p->node) ||
#if USE_CARDANO
          p->node.curve == &ed25519_cardano_info ||
#endif
          r->arg != 0 || !(made = secret_scratch_take()))
        break;
      made_type = node_key_type(&p->node);
      made_length = 32;
      memcpy(made->bytes, p->node.private_key, 32);
      ok = true;
      break;
    }
    case VAULT_SIGN: {
      size_t len = 0;
      const uint8_t *key = NULL;
      if (r->blob->bytes[4] == SECRET_BYTES) {
        secret_payload_t *p = secret_open(r->blob, r->owner,
                                          VAULT_KEY(VAULT_KEY_SECP256K1), &len);
        key = p ? p->bytes : NULL;
      } else {
        /* Sign from a node in place: no snapshot, no second key copy. */
        secret_payload_t *p =
            secret_open(r->blob, r->owner, VAULT_KEY(VAULT_KEY_NODE), NULL);
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
      secret_payload_t *key = secret_open(
          r->blob, r->owner, VAULT_KEY(VAULT_KEY_ED25519_SEED), &length);
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
      /* The type is the curve: NIST_SIGN signs only on NIST P-256, and a
       * secp256k1 public key (arg & 2) needs a secp256k1 key. U2F key
       * handles are MACed with the credential's NIST P-256 key; HMAC output
       * reveals nothing about its key. */
      uint32_t types =
          r->op == VAULT_HMAC_TAG
              ? VAULT_KEY(VAULT_KEY_SYMMETRIC) | VAULT_KEY(VAULT_KEY_NIST256P1)
          : r->op == VAULT_NIST_PUBLIC && (r->arg & 2)
              ? VAULT_KEY(VAULT_KEY_SECP256K1)
              : VAULT_KEY(VAULT_KEY_NIST256P1);
      size_t length = 0;
      secret_payload_t *key = secret_open(r->blob, r->owner, types, &length);
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
    case VAULT_SLIP21:
      ok = vault_slip21(r, out, &made, &made_length, &made_type);
      break;
    case VAULT_SCHNORR_GENERATE:
    case VAULT_SCHNORR_PUBLIC:
    case VAULT_SCHNORR_TWEAK:
    case VAULT_SCHNORR_SIGN:
      made_type = VAULT_KEY_SECP256K1;
      made_length = 32;
      ok = vault_schnorr(r, out, &made);
      break;
#ifndef VAULT_TEST
    case VAULT_MNEMONIC: {
      /* Explicit backup disclosure is distinct from deriving wallet keys.
       * Recovery comparison and storage migration never disclose the value.
       * Disclosure needs a pending first backup or a matching check. */
      char mnemonic[256] = {0};
      uint16_t length = 0;
      if (r->arg == 3) {
        vault_backup_granted = false;
        ok = vault_backup_set_pending(0);
      } else if (storage_get(0x0102, mnemonic, sizeof(mnemonic) - 1, &length) ==
                     sectrue &&
                 length && length < sizeof(mnemonic)) {
        if (r->arg == 0 && vault_backup_take()) {
          out->data[0] = length;
          memcpy(out->data + 1, mnemonic, length);
          ok = true;
        } else if (r->arg == 1) {
          out->value =
              length == r->length && consteq(mnemonic, r->data, length);
          vault_backup_granted = out->value;
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
          (made = secret_scratch_take())) {
        char passphrase[201] = {0};
        memcpy(passphrase, r->data, r->length);
        mnemonic_to_seed(mnemonic, passphrase, made->bytes, NULL);
        memzero(passphrase, sizeof(passphrase));
        made_type = VAULT_KEY_SEED;
        made_length = 64;
        ok = true;
      }
      if (!bip39 && r->length <= 200 && !memchr(r->data, 0, r->length) &&
          (made = secret_scratch_take())) {
        ok = vault_slip39_seed(r->data, r->length, backup_type, made->bytes,
                               &made_length);
        made_type = VAULT_KEY_SEED;
      }
      memzero(mnemonic, sizeof(mnemonic));
      break;
    }
#endif
    default:
      break;
  }
  /* Second, independent unlock test before any result leaves the vault. */
  if (!unlocked_check) ok = false;
#ifndef VAULT_TEST
  /* Re-query trusted storage and owner state before release instead of
   * relying only on the unlock flag sampled at syscall entry. */
  if (storage_is_unlocked() != sectrue &&
      !(crypto_only && owner->parent && owner->authorized_locked))
    ok = false;
#endif
  if (ok && made)
    ok = secret_seal(made_owner, made_type, made_length, made, &out->blob);
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
  bool ecc = r->op == VAULT_ECDH || r->op == VAULT_NIST_PUBLIC ||
             (r->op >= VAULT_FROM_SEED && r->op <= VAULT_SIGN) ||
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
  if (r->op == VAULT_THP_RESET) vault_wipe();
  vault_scrub_stack();
  return ok;
}

bool vault_dispatch(uintptr_t caller, const vault_request_t *r,
                    vault_response_t *out, bool unlocked) {
  if (vault_is_lifecycle(r->op)) {
    vault_lifecycle_request_t request = {r->abi, r->op, r->owner};
    vault_lifecycle_response_t response = {0};
    bool ok = vault_lifecycle_dispatch(caller, &request, &response);
    memset(out, 0, sizeof(*out));
    out->value = response.value;
    out->parent = response.parent;
    return ok;
  }
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
  if ((r->op != VAULT_ED_SIGN && r->op != VAULT_ED_SIGN_EXT &&
       r->op != VAULT_CHACHA_TAG && r->op != VAULT_CHACHA_OPEN &&
       r->op != VAULT_KEYVALUE_DERIVE) ||
      !message || !length || length > VAULT_ED25519_MAX_MESSAGE) {
    memzero(out, sizeof(*out));
    return false;
  }
  vault_command_t command = {.abi = r->abi,
                             .op = r->op,
                             .owner = r->owner,
                             .arg = r->arg,
                             .length = r->length,
                             .blob = &r->blob,
                             .extension = &r->extension};
  return vault_dispatch_inner(caller, &command, out, unlocked, message, length);
}

/* Small snapshots stay on the stack. A bounded, serialized public-message
 * workspace supports 4 KiB Solana packets without exceeding MCU stacks. */
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

static uint8_t vault_large_message[VAULT_ED25519_MAX_MESSAGE];
static bool vault_large_message_busy;
static __attribute__((noinline)) bool vault_snapshot_large(
    uintptr_t caller, const vault_message_request_t *request,
    const uint8_t *message, size_t length, vault_response_t *response,
    bool unlocked) {
  if (vault_large_message_busy) {
    memzero(response, sizeof(*response));
    return false;
  }
  vault_large_message_busy = true;
  bool ok = vault_snapshot_into(caller, request, message, length, response,
                                unlocked, vault_large_message);
  memzero(vault_large_message, sizeof(vault_large_message));
  vault_large_message_busy = false;
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
