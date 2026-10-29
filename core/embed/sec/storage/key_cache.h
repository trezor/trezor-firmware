/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Kernel-private volatile DEK/SAK cache; no persistent storage format change.
 */
#define STORAGE_CACHED_KEYS_SIZE 48
bool storage_key_cache_set(const uint8_t keys[STORAGE_CACHED_KEYS_SIZE]);
bool storage_key_cache_get(uint8_t *out, size_t offset, size_t length);
void storage_key_cache_wipe(void);
