/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef TREZOR_SECRET_STORE_H
#define TREZOR_SECRET_STORE_H

#include <sec/vault.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "bip32.h"
#include "curves.h"
#include "memzero.h"
#include "seal.h"

/* Kernel-private store. No pointer-returning interface crosses the boundary.
 * Secrets are not stored here: each one is sealed into a client-held blob, so
 * kernel RAM does not grow with the number of live secrets. The kernel keeps
 * owners, the per-boot key (seal.c) and a nonce counter. Never wrap
 * identities: exhausted counters fail closed until reboot. */
#define SECRET_STORE_BYTES \
  (sizeof(HDNode) > VAULT_SECRET_SIZE ? sizeof(HDNode) : VAULT_SECRET_SIZE)
typedef union {
  HDNode node;
  uint8_t bytes[SECRET_STORE_BYTES];
} secret_payload_t;
_Static_assert(VAULT_RECORD_SIZE == VAULT_SECRET_SIZE, "record size");

#define SECRET_OWNER_CAPACITY 64
/* IDs are generation identities: monotonic across reuse and VM resets. A blob
 * opens only while its owner is live, so destroying an owner revokes every
 * blob it ever sealed, wherever the client keeps it. */
typedef struct {
  uint32_t id;
  uint32_t parent;
  uintptr_t caller;
} secret_owner_t;
static secret_owner_t secret_owners[SECRET_OWNER_CAPACITY];
static uint32_t secret_next_owner = 1;
static uint32_t secret_owner;

static secret_owner_t *secret_owner_find(uint32_t id) {
  if (!id) return NULL;
  for (size_t i = 0; i < SECRET_OWNER_CAPACITY; i++)
    if (secret_owners[i].id == id) return &secret_owners[i];
  return NULL;
}
static uint32_t secret_owner_create(uint32_t parent) {
  secret_owner_t *p = secret_owner_find(parent);
  /* Two levels only: session -> request. Prevent cycles and unbounded walks. */
  if ((parent && (!p || p->parent)) || !secret_next_owner) return 0;
  for (size_t i = 0; i < SECRET_OWNER_CAPACITY; i++) {
    if (!secret_owners[i].id) {
      uint32_t id = secret_next_owner++;
      secret_owners[i] = (secret_owner_t){.id = id, .parent = parent};
      return id;
    }
  }
  return 0;
}
static bool secret_owner_access(uint32_t active, uint32_t owner) {
  secret_owner_t *a = secret_owner_find(active);
  return a && secret_owner_find(owner) &&
         (active == owner || a->parent == owner);
}
/* Allocation-free, idempotent, and independent of Python unwinding. */
static void secret_owner_destroy(uint32_t id) {
  if (!secret_owner_find(id)) return;
  for (size_t i = 0; i < SECRET_OWNER_CAPACITY; i++) {
    if (secret_owners[i].parent == id || secret_owners[i].id == id) {
      if (secret_owner == secret_owners[i].id) secret_owner = 0;
      secret_owners[i] = (secret_owner_t){0};
    }
  }
}
static __attribute__((unused)) void secret_revoke_requests(void) {
  for (size_t i = 0; i < SECRET_OWNER_CAPACITY; i++)
    if (secret_owners[i].parent) secret_owner_destroy(secret_owners[i].id);
  secret_owner = 0;
}
static __attribute__((unused)) void secret_revoke_all(void) {
  for (size_t i = 0; i < SECRET_OWNER_CAPACITY; i++)
    if (secret_owners[i].id) secret_owner_destroy(secret_owners[i].id);
  secret_owner = 0;
}

/* Plaintext lives only in this scratch, for the duration of one call. */
#define SECRET_SCRATCH_CAPACITY 2
static secret_payload_t secret_scratch[SECRET_SCRATCH_CAPACITY];
static bool secret_scratch_used[SECRET_SCRATCH_CAPACITY];
static bool secret_crypto_failed, secret_busy;
/* Monotonic for the entire boot, including across key rotations/VM resets. */
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_GCM
static uint64_t secret_nonce;
#endif

static secret_payload_t *secret_scratch_take(void) {
  for (size_t i = 0; i < SECRET_SCRATCH_CAPACITY; i++) {
    if (!secret_scratch_used[i]) {
      secret_scratch_used[i] = true;
      memzero(&secret_scratch[i], sizeof(secret_scratch[i]));
      return &secret_scratch[i];
    }
  }
  return NULL;
}

static void secret_put32(uint8_t *p, uint32_t value) {
  for (size_t i = 0; i < 4; i++) p[i] = value >> (8 * i);
}
static uint32_t secret_get32(const uint8_t *p) {
  uint32_t result = 0;
  for (size_t i = 0; i < 4; i++) result |= (uint32_t)p[i] << (8 * i);
  return result;
}
static __attribute__((unused)) uint64_t secret_get64(const uint8_t *p) {
  return secret_get32(p) | (uint64_t)secret_get32(p + 4) << 32;
}

/* Blob header: owner u32 | kind u8 | length u8 | zero u16 | nonce u64. */
#define SECRET_BLOB_HEADER VAULT_HEADER_SIZE

/* The whole header is authenticated, bound to the ABI version. */
static void secret_aad(const uint8_t header[SECRET_BLOB_HEADER],
                       uint8_t aad[VAULT_AAD_SIZE]) {
  memset(aad, 0, VAULT_AAD_SIZE);
  memcpy(aad, "TVB", 3);
  aad[3] = VAULT_ABI;
  memcpy(aad + 4, header, SECRET_BLOB_HEADER);
}

/* Stable wire IDs, never serialize native curve pointers. */
static const char *secret_curve_name(uint8_t id) {
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
/* Inverse of secret_curve_name() for the curves a node can carry. */
static uint8_t secret_curve_id(const HDNode *n) {
  return n->curve == get_curve_by_name(NIST256P1_NAME) ? 1
         : n->curve == get_curve_by_name(ED25519_NAME) ? 2
                                                       : 0;
}
static bool secret_curve_allowed(const char *name) {
  for (uint8_t i = 0; secret_curve_name(i); i++)
    if (!strcmp(name, secret_curve_name(i))) return true;
  return false;
}
/* Canonical node encoding: no struct padding, addresses or curve pointers. */
static void secret_encode(secret_kind_t kind, size_t length,
                          const secret_payload_t *p,
                          uint8_t data[VAULT_RECORD_SIZE]) {
  memset(data, 0, VAULT_RECORD_SIZE);
  if (kind == SECRET_BYTES) {
    memcpy(data, p->bytes, length);
    return;
  }
  const HDNode *n = &p->node;
  secret_put32(data, n->depth);
  secret_put32(data + 4, n->child_num);
  memcpy(data + 8, n->chain_code, 32);
  memcpy(data + 40, n->private_key, 32);
  memcpy(data + 72, n->public_key, 33);
  data[105] = n->is_public_key_set;
  data[106] = secret_curve_id(n);
}
static bool secret_decode(secret_kind_t kind, size_t length,
                          const uint8_t data[VAULT_RECORD_SIZE],
                          secret_payload_t *p) {
  memzero(p, sizeof(*p));
  if (kind == SECRET_BYTES) {
    if (length > VAULT_SECRET_SIZE) return false;
    memcpy(p->bytes, data, length);
    return true;
  }
  if (kind != SECRET_NODE || data[105] > 1 || !secret_curve_name(data[106]))
    return false;
  HDNode *n = &p->node;
  n->depth = secret_get32(data);
  n->child_num = secret_get32(data + 4);
  memcpy(n->chain_code, data + 8, 32);
  memcpy(n->private_key, data + 40, 32);
  memcpy(n->public_key, data + 72, 33);
  n->is_public_key_set = data[105];
  n->curve = get_curve_by_name(secret_curve_name(data[106]));
  return n->curve != NULL;
}

/* Seal a payload for a live owner into a fresh blob. */
static bool secret_seal(uint32_t owner, secret_kind_t kind, size_t length,
                        const secret_payload_t *p, vault_blob_t *out) {
  memzero(out, sizeof(*out));
  if (!secret_busy || secret_crypto_failed || !secret_owner_find(owner) ||
      (kind != SECRET_BYTES && kind != SECRET_NODE) ||
      (kind == SECRET_BYTES && (!length || length > VAULT_SECRET_SIZE)) ||
      (kind == SECRET_NODE &&
       (length != sizeof(HDNode) ||
        memcmp(p->node.private_key_extension, (uint8_t[32]){0}, 32))))
    return false;
  uint64_t nonce = 0;
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_GCM
  /* Advance before encryption: failed writes never reuse a nonce. */
  if (secret_nonce == UINT64_MAX) return false;
  nonce = ++secret_nonce;
#endif
  uint8_t *b = out->bytes;
  secret_put32(b, owner);
  b[4] = kind;
  b[5] = kind == SECRET_BYTES ? length : 0;
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_GCM
  secret_put32(b + 8, nonce);
  secret_put32(b + 12, nonce >> 32);
#endif
  uint8_t data[VAULT_RECORD_SIZE], aad[VAULT_AAD_SIZE];
  secret_encode(kind, length, p, data);
  secret_aad(b, aad);
  size_t encoded_length =
      vault_ciphertext_size(kind == SECRET_BYTES ? length : VAULT_NODE_SIZE);
  uint8_t tag[16] = {0};
  bool ok = vault_seal_record(true, nonce, aad, data, encoded_length, tag);
  if (ok && VAULT_TAG_SIZE)
    memcpy(b + SECRET_BLOB_HEADER + encoded_length, tag, VAULT_TAG_SIZE);
  memzero(tag, sizeof(tag));
  if (ok) memcpy(b + SECRET_BLOB_HEADER, data, encoded_length);
  memzero(data, sizeof(data));
  if (!ok) {
    /* Kernel-side key failure: fail closed for the whole vault. */
    memzero(out, sizeof(*out));
    secret_crypto_failed = true;
  }
  return ok;
}

/* Open a blob into call-local scratch. Fails unless the active owner may use
 * the blob's owner and the blob authenticates. A tampered blob is an ordinary
 * failure, not a crypto failure: clients control blob contents. */
static secret_payload_t *secret_open(const vault_blob_t *blob, uint32_t active,
                                     secret_kind_t kind, size_t *length) {
  const uint8_t *b = blob->bytes;
  if (!secret_busy || secret_crypto_failed ||
      !secret_owner_access(active, secret_get32(b)) || b[4] != kind || b[6] ||
      b[7])
    return NULL;
  size_t len = kind == SECRET_BYTES ? b[5] : sizeof(HDNode);
  if (kind == SECRET_NODE && b[5]) return NULL;
  if (kind == SECRET_BYTES && (!len || len > VAULT_SECRET_SIZE)) return NULL;
  size_t encoded_length =
      vault_ciphertext_size(kind == SECRET_BYTES ? len : VAULT_NODE_SIZE);
  size_t blob_length = SECRET_BLOB_HEADER + encoded_length + VAULT_TAG_SIZE;
  /* Reject noncanonical envelopes; every supplied byte is authenticated or
   * checked, including unused wire padding. */
  for (size_t i = blob_length; i < sizeof(blob->bytes); i++)
    if (b[i]) return NULL;
  secret_payload_t *p = secret_scratch_take();
  if (!p) return NULL;
  uint8_t data[VAULT_RECORD_SIZE] = {0}, tag[16] = {0}, aad[VAULT_AAD_SIZE];
  memcpy(data, b + SECRET_BLOB_HEADER, encoded_length);
  memcpy(tag, b + SECRET_BLOB_HEADER + encoded_length, VAULT_TAG_SIZE);
  secret_aad(b, aad);
  uint64_t nonce = 0;
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_GCM
  nonce = secret_get64(b + 8);
#endif
  bool ok = vault_seal_record(false, nonce, aad, data, encoded_length, tag) &&
            secret_decode(kind, len, data, p);
  memzero(data, sizeof(data));
  if (!ok) {
    if (!vault_seal_ready()) secret_crypto_failed = true;
    memzero(p, sizeof(*p));
    return NULL;
  }
  if (length) *length = len;
  return p;
}

static void secret_transaction_begin(void) {
  secret_busy = true;
  secret_crypto_failed = false;
}
/* Returns false when the call hit a kernel-side key failure; the vault has
 * then been revoked and rekeyed. */
static bool secret_transaction_end(void) {
  bool ok = !secret_crypto_failed;
  memzero(secret_scratch, sizeof(secret_scratch));
  memzero(secret_scratch_used, sizeof(secret_scratch_used));
  vault_seal_end();
  secret_busy = false;
  if (!ok) {
    secret_revoke_all();
    vault_seal_wipe();
  }
  secret_crypto_failed = false;
  return ok;
}

#endif
