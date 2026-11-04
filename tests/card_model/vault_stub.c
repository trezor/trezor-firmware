/* SPDX-License-Identifier: GPL-3.0-or-later */
/* The local vault, stubbed for the card tests: only its owner table matters. */
#include <string.h>

#include "vault_stub.h"

stub_owner_t owners[STUB_OWNERS] = {{1, 0, 0}, {2, 1, 0}, {3, 0, 0}, {4, 1, 0}};
int local_calls;

bool vault_lifecycle_dispatch(uintptr_t caller,
                              const vault_lifecycle_request_t *r,
                              vault_lifecycle_response_t *out) {
  memset(out, 0, sizeof(*out));
  if (caller != 1 || r->op != VAULT_OWNER_INFO) return false;
  for (size_t i = 0; i < STUB_OWNERS; i++)
    if (owners[i].id == r->owner) {
      out->parent = owners[i].parent;
      out->value = owners[i].authorized;
      return true;
    }
  return false;
}
bool vault_dispatch(uintptr_t caller, const vault_request_t *r,
                    vault_response_t *out, bool unlocked) {
  (void)caller, (void)r, (void)unlocked;
  memset(out, 0, sizeof(*out));
  local_calls++;
  return true;
}
bool vault_message_snapshot(uintptr_t caller, const vault_message_request_t *r,
                            const uint8_t *message, size_t length,
                            vault_response_t *out, bool unlocked) {
  (void)caller, (void)r, (void)message, (void)length, (void)unlocked;
  memset(out, 0, sizeof(*out));
  local_calls++;
  return true;
}
