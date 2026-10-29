/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <sec/vault.h>
#include "store.h"
#if !defined(TREZOR_EMULATOR) && !defined(VAULT_TEST)
#include <sys/stack_utils.h>
#define vault_scrub_stack() clear_unused_stack()
#else
#define vault_scrub_stack() ((void)0)
#endif
#ifndef VAULT_TEST
#include <sec/storage.h>
#endif
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

static bool vault_execute(uintptr_t caller, const vault_request_t *r,
                          vault_response_t *out, bool unlocked) {
  memset(out, 0, sizeof(*out));
  if (!caller || r->abi != VAULT_ABI || r->length > VAULT_DATA_SIZE)
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
  secret_payload_t *made = NULL;
  size_t made_length = r->length;
  uint32_t made_owner = r->owner;
  bool ok = false;
  switch (r->op) {
    case VAULT_RETAIN:
      if (r->arg != SECRET_BYTES || !owner->parent ||
          secret_get32(r->blob.bytes) != r->owner)
        break;
      made = secret_open(&r->blob, r->owner, SECRET_BYTES, &made_length);
      made_owner = owner->parent;
      ok = made != NULL;
      break;
    case VAULT_IMPORT_BYTES:
      if (!r->length || r->length > VAULT_SECRET_SIZE ||
          !(made = secret_scratch_take()))
        break;
      memcpy(made->bytes, r->data, r->length);
      ok = true;
      break;
    default:
      break;
  }
  if (ok && made)
    ok = secret_seal(made_owner, SECRET_BYTES, made_length, made, &out->blob);
  if (!ok) memzero(out, sizeof(*out));
  return ok;
}
bool vault_dispatch(uintptr_t caller, const vault_request_t *r,
                    vault_response_t *out, bool unlocked) {
  if (secret_busy) {
    memzero(out, sizeof(*out));
    return false;
  }
  secret_transaction_begin();
  bool ok = vault_execute(caller, r, out, unlocked);
  if (!secret_transaction_end()) {
    memzero(out, sizeof(*out));
    ok = false;
  }
  vault_scrub_stack();
  return ok;
}
#if defined(TREZOR_EMULATOR) && !defined(VAULT_TEST)
bool vault_call(const vault_request_t *request, vault_response_t *response) {
  vault_request_t copy = *request;
  bool ok =
      vault_dispatch(1, &copy, response, storage_is_unlocked() == sectrue);
  memzero(&copy, sizeof(copy));
  return ok;
}
#endif
#ifndef VAULT_TEST
void systask_revoke_secrets(void *applet) {
  vault_revoke_caller((uintptr_t)applet);
}
#endif
