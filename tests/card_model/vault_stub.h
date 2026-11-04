/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <sec/vault.h>

/* Owners 1 (session) and 2, 4 (its requests), 3 (another session). */
#define STUB_OWNERS 4
typedef struct {
  uint32_t id, parent, authorized;
} stub_owner_t;
extern stub_owner_t owners[STUB_OWNERS];
/* Requests the card backend handed to the local vault. */
extern int local_calls;
