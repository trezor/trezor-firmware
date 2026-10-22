/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <trezor_types.h>

/* RFC 3394 wrap (encrypt) or unwrap of a 32-byte key under the BHK. value
 * holds the 8-byte integrity block followed by the key; on wrap the first 8
 * bytes are ignored. Unwrap fails on an integrity mismatch and then zeroes
 * value. Runs in the secure world: directly in a secure-mode kernel, through
 * an smcall when secmon owns SAES. The BHK must not be used for anything else,
 * as this exposes a wrap/unwrap oracle under it to the caller. */
secbool vault_kek_wrap(bool encrypt, uint8_t value[40]);

/* Stage C3: AES-256-GCM of one vault record in SAES. The per-boot record key
 * is generated in the secure world, kept only wrapped under DHUK, and loaded
 * into the SAES key registers for each call, so it never exists in RAM after
 * generation and no software AES ever runs on it. RESET drops the key; the
 * next call generates a new one, which invalidates every earlier record. */
#define VAULT_SAES_RECORD_SIZE 160
#define VAULT_SAES_AAD_SIZE 32

typedef enum {
  VAULT_SAES_SEAL = 1,
  VAULT_SAES_OPEN = 2,
  VAULT_SAES_RESET = 3,
} vault_saes_op_t;

/* Multi-bit results, so a single fault cannot turn a failure into success. */
#define VAULT_SAES_OK 0xA5C3965Au
#define VAULT_SAES_AUTH_FAILED 0x5A3C69A5u /* tag mismatch: caller's data */
#define VAULT_SAES_FAILED 0u               /* hardware or key failure */

typedef struct {
  uint32_t op;
  uint32_t length; /* 1..VAULT_SAES_RECORD_SIZE bytes of data */
  uint8_t iv[12];
  uint8_t aad[VAULT_SAES_AAD_SIZE];
  uint8_t data[VAULT_SAES_RECORD_SIZE];
  uint8_t tag[16];
} vault_saes_request_t;

/* SEAL encrypts data in place and fills tag; OPEN verifies tag and decrypts
 * data in place, zeroing it on any failure. Runs in the secure world. */
uint32_t vault_saes_record(vault_saes_request_t* request);
