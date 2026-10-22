/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Versioned, bounded, pointer-free wire messages. Never return a private field.
 */
#include <sec/vault_mode.h>
#define VAULT_ABI (22 + VAULT_SEAL_MODE)
#define VAULT_DATA_SIZE 256
/* Covers FIDO self-attestation and Solana packets without enlarging normal
 * RPCs. */
#define VAULT_ED25519_MAX_MESSAGE 2048
#define VAULT_SECRET_SIZE 160
/* Supported SLIP-10 nodes need no private-key extension. Encode depth/child,
 * chain code, private seed/scalar, cached public key, cache flag and curve ID.
 */
#define VAULT_NODE_SIZE 107
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_ECB
#define VAULT_NODE_CIPHERTEXT_SIZE ((VAULT_NODE_SIZE + 15) & ~15)
#else
#define VAULT_NODE_CIPHERTEXT_SIZE VAULT_NODE_SIZE
#endif
#define VAULT_NODE_BLOB_SIZE \
  (VAULT_HEADER_SIZE + VAULT_NODE_CIPHERTEXT_SIZE + VAULT_TAG_SIZE)
#define VAULT_CURVE_SIZE 32
typedef enum { SECRET_BYTES = 1, SECRET_NODE = 2 } secret_kind_t;
/* Kernel-sealed, client-held records. Every mode starts with:
 *   owner u32 | kind u8 | length u8 | zero u16
 * GCM appends a nonce u64, actual-length ciphertext and tag[16].
 * SIV appends actual-length ciphertext and the synthetic IV/tag[16].
 * ECB appends zero-padded, block-aligned ciphertext WITHOUT authentication.
 * Nodes encode VAULT_NODE_SIZE plaintext bytes. Wire padding is zero.
 * No plaintext is exposed through this interface. An all-zero blob is empty. */
#define VAULT_BLOB_SIZE (VAULT_HEADER_SIZE + VAULT_SECRET_SIZE + VAULT_TAG_SIZE)
typedef struct {
  uint8_t bytes[VAULT_BLOB_SIZE];
} vault_blob_t;
typedef enum {
  VAULT_OWNER_CREATE = 1,
  VAULT_OWNER_INFO,
  VAULT_OWNER_DESTROY,
  VAULT_REVOKE_REQUESTS,
  VAULT_RESET,
  VAULT_RETAIN,
  VAULT_IMPORT_BYTES,
  VAULT_FROM_SEED,
  VAULT_IMPORT_NODE,
  VAULT_PUBLIC,
  VAULT_DERIVE,
  VAULT_SNAPSHOT,
  VAULT_SIGN,
  VAULT_SEED_STORAGE,
  VAULT_SCHNORR_GENERATE,
  VAULT_SCHNORR_PUBLIC,
  VAULT_SCHNORR_TWEAK,
  VAULT_SCHNORR_SIGN,
  VAULT_NIST_PUBLIC,
  VAULT_NIST_SIGN,
  VAULT_HMAC_TAG,
  VAULT_ED_PUBLIC,
  VAULT_ED_SIGN,
  VAULT_SLIP21
} vault_op_t;
/* VAULT_SLIP21: derive from a seed (VAULT_SLIP21_ROOT) or a 64-byte node
 * along length-prefixed labels in data; the other arg bits select the output.
 * Export returns the node in signature and is allowed only from a seed under
 * the Evolu namespace, which hands that node to the host by design. */
#define VAULT_SLIP21_ROOT 1
#define VAULT_SLIP21_NODE 0
#define VAULT_SLIP21_KEY 2
#define VAULT_SLIP21_EXPORT 4
/* VAULT_SIGN canonical selector, in arg bits 1-2 beside compressed (bit 0).
 * Values match secp256k1.CANONICAL_SIG_*. */
#define VAULT_CANONICAL_NONE 0
#define VAULT_CANONICAL_ETHEREUM 1
#define VAULT_CANONICAL_EOS 2
typedef struct {
  uint32_t abi, op, owner, arg, length, child_num;
  vault_blob_t blob;
  char curve[VAULT_CURVE_SIZE];
  uint8_t data[VAULT_DATA_SIZE];
} vault_request_t;
/* Ed25519 message signing has no inline data, curve or derivation fields. */
typedef struct {
  uint32_t abi, op, owner, arg, length;
  vault_blob_t blob;
} vault_message_request_t;
typedef struct {
  union {
    struct {
      vault_blob_t blob;
      uint32_t value, parent, depth, child_num;
      uint8_t chain_code[32], public_key[33];
    };
    uint8_t signature[65];
  };
} vault_response_t;
/* Client entrypoint: syscall on hardware, same dispatcher in emulator. */
bool vault_call(const vault_request_t *request, vault_response_t *response);
/* Bounded public-message ingress. The verifier takes one immutable snapshot.
 * Only ED_SIGN accepts this call; no caller pointer reaches private crypto. */
bool vault_call_message(const vault_message_request_t *request,
                        const uint8_t *message, size_t length,
                        vault_response_t *response);
#if defined(KERNEL_MODE) || defined(VAULT_TEST)
/* Caller comes from trusted syscall context, never from a request field. */
bool vault_dispatch(uintptr_t caller, const vault_request_t *request,
                    vault_response_t *response, bool unlocked);
bool vault_dispatch_message(uintptr_t caller,
                            const vault_message_request_t *request,
                            const uint8_t *message, size_t length,
                            vault_response_t *response, bool unlocked);
/* Kernel-only ingress after the syscall's access probes. Snapshot and erase
 * bounded message storage; shared with the emulator and native tests. */
bool vault_message_snapshot(uintptr_t caller,
                            const vault_message_request_t *request,
                            const uint8_t *message, size_t length,
                            vault_response_t *response, bool unlocked);
void vault_revoke_caller(uintptr_t caller);
void vault_wipe(void);
bool vault_storage_key_allowed(uint16_t key);
#endif
