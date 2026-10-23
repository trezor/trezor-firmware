/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef TREZOR_SECRET_STORE_H
#define TREZOR_SECRET_STORE_H
#include <sec/vault.h>
#include "memzero.h"
#define SECRET_OWNER_CAPACITY 64
#define SECRET_STORE_BYTES VAULT_SECRET_SIZE
static uint32_t secret_owner;
typedef struct {
  uint32_t id, parent;
} secret_owner_t;
static bool secret_rpc(vault_request_t *r, vault_response_t *out) {
  r->abi = VAULT_ABI;
  if (!r->owner) r->owner = secret_owner;
  bool ok = vault_call(r, out);
  memzero(r, sizeof(*r));
  return ok;
}
static secret_owner_t *secret_owner_find(uint32_t id) {
  static secret_owner_t info;
  if (!id) return NULL;
  vault_request_t r = {.op = VAULT_OWNER_INFO, .owner = id};
  vault_response_t out = {0};
  if (!secret_rpc(&r, &out)) return NULL;
  info = (secret_owner_t){id, out.parent};
  return &info;
}
static uint32_t secret_owner_create(uint32_t parent) {
  vault_request_t r = {.op = VAULT_OWNER_CREATE, .owner = parent};
  vault_response_t out = {0};
  /* Root owner creation must not inherit active request. */
  r.abi = VAULT_ABI;
  return vault_call(&r, &out) ? out.value : 0;
}
static void secret_owner_destroy(uint32_t id) {
  if (!id) return;
  vault_request_t r = {.op = VAULT_OWNER_DESTROY, .owner = id};
  vault_response_t out = {0};
  secret_rpc(&r, &out);
  if (secret_owner == id) secret_owner = 0;
}
/* Blobs are sealed by the kernel and hold no kernel state: dropping one is a
 * local wipe, and copying one shares the same secret. Revocation happens in
 * the kernel, by owner. */
static bool secret_blob_empty(const vault_blob_t *b) {
  for (size_t i = 0; i < sizeof(b->bytes); i++)
    if (b->bytes[i]) return false;
  return true;
}
/* Non-empty and owned by a live owner; does not authenticate the blob. */
static bool secret_blob_live(const vault_blob_t *b) {
  uint32_t owner = 0;
  for (size_t i = 0; i < 4; i++) owner |= (uint32_t)b->bytes[i] << (8 * i);
  return owner && secret_owner_find(owner) != NULL;
}
static bool secret_retain(vault_blob_t *b, uint32_t active,
                          secret_kind_t kind) {
  vault_request_t r = {
      .op = VAULT_RETAIN, .owner = active, .blob = *b, .arg = kind};
  vault_response_t out = {0};
  if (!secret_rpc(&r, &out)) return false;
  *b = out.blob;
  memzero(&out, sizeof(out));
  return true;
}
static void secret_revoke_requests(void) {
  vault_request_t r = {.op = VAULT_REVOKE_REQUESTS};
  vault_response_t out = {0};
  secret_rpc(&r, &out);
  secret_owner = 0;
}
static void secret_revoke_all(void) {
  vault_request_t r = {.op = VAULT_RESET};
  vault_response_t out = {0};
  secret_rpc(&r, &out);
  secret_owner = 0;
}
#endif
