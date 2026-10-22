/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stddef.h>

/* Keep selection identical in the kernel, syscall verifier and Python binding.
 * Firmware builds set this through TREZOR_VAULT_MODE=gcm|siv|ecb. */
#define VAULT_SEAL_AES_SIV 1
#define VAULT_SEAL_AES_ECB 2
#define VAULT_SEAL_AES_GCM 3
#ifndef VAULT_SEAL_MODE
#define VAULT_SEAL_MODE VAULT_SEAL_AES_SIV
#endif

#if VAULT_SEAL_MODE == VAULT_SEAL_AES_GCM
#define VAULT_HEADER_SIZE 16
#define VAULT_TAG_SIZE 16
#define VAULT_KEY_COUNT 1
#elif VAULT_SEAL_MODE == VAULT_SEAL_AES_SIV
#define VAULT_HEADER_SIZE 8
#define VAULT_TAG_SIZE 16
#define VAULT_KEY_COUNT 2
#elif VAULT_SEAL_MODE == VAULT_SEAL_AES_ECB
/* Experimental confidentiality-only mode. Header and ciphertext are
 * unauthenticated. */
#define VAULT_HEADER_SIZE 8
#define VAULT_TAG_SIZE 0
#define VAULT_KEY_COUNT 1
#else
#error "Unknown vault sealing mode"
#endif

static inline size_t vault_ciphertext_size(size_t length) {
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_ECB
  return (length + 15) & ~(size_t)15;
#else
  return length;
#endif
}
static inline size_t vault_bytes_blob_size(size_t length) {
  return VAULT_HEADER_SIZE + vault_ciphertext_size(length) + VAULT_TAG_SIZE;
}
