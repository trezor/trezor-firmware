/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#ifndef VAULT_CACHE_RECORD_CONTEXT
#define VAULT_CACHE_RECORD_CONTEXT 0
#endif
#include <sec/vault_mode.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define VAULT_RECORD_SIZE 160
#define VAULT_AAD_SIZE 32
/* Private kernel implementation; never exported through sec/vault.h. */
bool vault_seal_record(bool encrypt, uint64_t nonce,
                       const uint8_t aad[VAULT_AAD_SIZE],
                       uint8_t data[VAULT_RECORD_SIZE], size_t length,
                       uint8_t tag[16]);
/* False after a trusted wrapping/key-setup failure, unlike an invalid tag. */
bool vault_seal_ready(void);
/* True when no expanded record key remains in RAM. */
bool vault_seal_idle(void);
void vault_seal_end(void);
void vault_seal_wipe(void);
