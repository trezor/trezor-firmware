/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stddef.h>

/* One record cipher per feature branch; all layers share this layout. */
#define VAULT_SEAL_AES_GCM 3
#define VAULT_SEAL_AES_KWP 4

#define VAULT_HEADER_SIZE 8
/* Wrapped metadata (12 bytes), KWP integrity/length and padding. */
#define VAULT_TAG_SIZE 24
#define VAULT_KEY_COUNT 1

#define VAULT_TAG_BUFFER_SIZE (VAULT_TAG_SIZE > 16 ? VAULT_TAG_SIZE : 16)

/* Constant-expression form is shared by fixed-size ABI objects and flexible
 * holders. Backend selection never changes the format for a given cipher. */
#define VAULT_CIPHERTEXT_SIZE(length) (((length) + 7) & ~(size_t)7)
static inline size_t vault_ciphertext_size(size_t length) {
  return VAULT_CIPHERTEXT_SIZE(length);
}
static inline size_t vault_bytes_blob_size(size_t length) {
  return VAULT_HEADER_SIZE + vault_ciphertext_size(length) + VAULT_TAG_SIZE;
}
