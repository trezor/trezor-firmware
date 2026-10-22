/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <sec/vault_mode.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define VAULT_ABI (10 + VAULT_SEAL_MODE)
#define VAULT_SECRET_SIZE 160
#define VAULT_DATA_SIZE VAULT_SECRET_SIZE
#define VAULT_BLOB_SIZE (VAULT_HEADER_SIZE + VAULT_SECRET_SIZE + VAULT_TAG_SIZE)
typedef struct {
  uint8_t bytes[VAULT_BLOB_SIZE];
} vault_blob_t;
typedef enum { SECRET_BYTES = 1 } secret_kind_t;
typedef enum {
  VAULT_OWNER_CREATE = 1,
  VAULT_OWNER_INFO,
  VAULT_OWNER_DESTROY,
  VAULT_REVOKE_REQUESTS,
  VAULT_RESET,
  VAULT_RETAIN,
  VAULT_IMPORT_BYTES,
} vault_op_t;
typedef struct {
  uint32_t abi, op, owner, arg, length;
  vault_blob_t blob;
  uint8_t data[VAULT_DATA_SIZE];
} vault_request_t;
typedef struct {
  vault_blob_t blob;
  uint32_t value, parent;
} vault_response_t;
bool vault_call(const vault_request_t *request, vault_response_t *response);
#if defined(KERNEL_MODE) || defined(VAULT_TEST)
bool vault_dispatch(uintptr_t caller, const vault_request_t *request,
                    vault_response_t *response, bool unlocked);
void vault_revoke_caller(uintptr_t caller);
void vault_wipe(void);
#endif
