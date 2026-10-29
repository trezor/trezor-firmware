/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <sec/vault_mode.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define VAULT_CIPHER_RECORD_SIZE 160
#define VAULT_CIPHER_AAD_SIZE 32
#define VAULT_GCM_IV_SIZE 12
#define VAULT_GCM_TAG_SIZE 16

typedef enum {
  VAULT_CIPHER_SEAL = 1,
  VAULT_CIPHER_OPEN = 2,
  VAULT_CIPHER_RESET = 3,
} vault_cipher_op_t;
#define VAULT_CIPHER_OK 0xA5C3965Au
#define VAULT_CIPHER_AUTH_FAILED 0x5A3C69A5u
#define VAULT_CIPHER_FAILED 0u

typedef struct {
  /* VAULT_CIPHER_REQUEST_ABI across the kernel-to-secure-world boundary.
   * First, so that its offset survives any layout change. */
  uint32_t abi;
  uint32_t op;
  uint32_t length;
  uint8_t iv[VAULT_GCM_IV_SIZE];
  uint8_t aad[VAULT_CIPHER_AAD_SIZE];
  uint8_t data[VAULT_CIPHER_RECORD_SIZE];
  uint8_t tag[VAULT_TAG_BUFFER_SIZE];
} vault_cipher_request_t;
/* The request size and the cipher identify the layout: the cipher fixes the
 * envelope size and its meaning. A kernel and secure monitor from different
 * builds must refuse each other's requests rather than misread them. */
#define VAULT_CIPHER_REQUEST_ABI                    \
  ((uint32_t)sizeof(vault_cipher_request_t) << 16 | \
   (uint32_t)VAULT_SEAL_MODE << 8 | 0x5aU)
static inline bool vault_cipher_request_abi_ok(
    const vault_cipher_request_t *request) {
  return request->abi == VAULT_CIPHER_REQUEST_ABI;
}

/* Backend-private, never part of a syscall. context is an opaque hardware
 * key/engine handle, not key bytes. All buffers below belong to trusted
 * scratch. A native GCM operation produces a computed tag; the common layer
 * checks it twice before releasing plaintext. A hardware error must return
 * false, and must never trigger a software retry with a RAM-held key. */
typedef bool (*vault_cipher_block_t)(const void *context, bool encrypt,
                                     const uint8_t in[16], uint8_t out[16]);
typedef bool (*vault_native_gcm_t)(const void *context, bool encrypt,
                                   const uint8_t iv[VAULT_GCM_IV_SIZE],
                                   const uint8_t aad[VAULT_CIPHER_AAD_SIZE],
                                   const uint8_t *in, size_t length,
                                   uint8_t *out,
                                   uint8_t tag[VAULT_GCM_TAG_SIZE]);
typedef struct {
  const void *context;
  vault_cipher_block_t block;
  vault_native_gcm_t native_gcm;
} vault_cipher_provider_t;
