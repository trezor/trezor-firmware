/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Owner table: the only per-identity state the kernel keeps. */
#define main vault_boundary_main
#include "test_vault.c"
#undef main

int main(void) {
  uint32_t session = secret_owner_create(0);
  uint32_t request = secret_owner_create(session);
  uint32_t sibling = secret_owner_create(session);
  uint32_t other_session = secret_owner_create(0);
  uint32_t other = secret_owner_create(other_session);
  assert(session && request && sibling && other_session && other);
  assert(!secret_owner_create(request));    /* no cycles or arbitrary depth */
  assert(!secret_owner_create(UINT32_MAX)); /* unknown parent */
  assert(secret_owner_access(request, request));
  assert(secret_owner_access(request, session));
  assert(!secret_owner_access(request, sibling));
  assert(!secret_owner_access(session, request));
  assert(!secret_owner_access(other, session));
  assert(!secret_owner_access(0, session));

  secret_owner = request;
  secret_owner_destroy(request);
  assert(!secret_owner_find(request) && secret_owner == 0);
  uint32_t replacement = secret_owner_create(session);
  assert(replacement && replacement != request);
  secret_owner_destroy(request); /* stale owner must not destroy replacement */
  assert(secret_owner_find(replacement));
  secret_owner_destroy(session); /* cascade to all requests */
  assert(!secret_owner_find(replacement) && !secret_owner_find(sibling));
  assert(secret_owner_find(other));
  secret_revoke_requests();
  assert(!secret_owner_find(other));
  assert(secret_owner_find(other_session));
  secret_revoke_all();
  for (size_t i = 0; i < SECRET_OWNER_CAPACITY; i++)
    assert(!secret_owners[i].id && !secret_owners[i].parent);

  uint32_t owners[SECRET_OWNER_CAPACITY];
  for (size_t i = 0; i < SECRET_OWNER_CAPACITY; i++) {
    owners[i] = secret_owner_create(0);
    assert(owners[i]);
  }
  assert(!secret_owner_create(0));
  secret_revoke_all();
  secret_next_owner = UINT32_MAX;
  assert(secret_owner_create(0) == UINT32_MAX);
  secret_revoke_all();
  assert(!secret_owner_create(0)); /* no identity reuse even across resets */
  puts("secret store tests passed");
  return 0;
}
