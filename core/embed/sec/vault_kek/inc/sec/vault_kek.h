/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <sec/vault_cipher.h>
#include <trezor_types.h>

/* RFC 3394 wrap (encrypt) or unwrap of a 32-byte key under the BHK. value
 * holds the 8-byte integrity block followed by the key; on wrap the first 8
 * bytes are ignored. Unwrap fails on an integrity mismatch and then zeroes
 * value. Runs in the secure world: directly in a secure-mode kernel, through
 * an smcall when secmon owns SAES. The BHK must not be used for anything else,
 * as this exposes a wrap/unwrap oracle under it to the caller. */
secbool vault_kek_wrap(bool encrypt, uint8_t value[40]);

/* Hardware KWP record sealing. Key representation is MCU-private: U5 retains
 * generated keys wrapped under DHUK and loads them directly into SAES. Every
 * backend must preserve separate record/cache key domains, fresh keys across
 * counter restarts, RESET invalidation, and no software export of hardware
 * record keys. The provider interface does not prescribe an H5 key-container
 * layout.
 */
/* Compatibility names for the existing secure-world transport. The cipher
 * request ABI is independent of the MCU and its native-GCM capability. */
#define VAULT_SAES_RECORD_SIZE VAULT_CIPHER_RECORD_SIZE
#define VAULT_SAES_AAD_SIZE VAULT_CIPHER_AAD_SIZE
#define VAULT_SAES_SEAL VAULT_CIPHER_SEAL
#define VAULT_SAES_OPEN VAULT_CIPHER_OPEN
#define VAULT_SAES_RESET VAULT_CIPHER_RESET
#define VAULT_SAES_OK VAULT_CIPHER_OK
#define VAULT_SAES_AUTH_FAILED VAULT_CIPHER_AUTH_FAILED
#define VAULT_SAES_FAILED VAULT_CIPHER_FAILED
typedef vault_cipher_op_t vault_saes_op_t;
typedef vault_cipher_request_t vault_saes_request_t;

/* SEAL encrypts data in place and fills the authenticated envelope. OPEN
 * authenticates and decrypts data in place, zeroing it on any failure. Runs in
 * the secure world.
 */
uint32_t vault_saes_record(vault_saes_request_t* request);

/* Always GCM with a separate key for the storage key cache. Secure world only:
 * no smcall reaches it, so the kernel cannot use the storage key. */
uint32_t vault_saes_storage(vault_saes_request_t* request);
