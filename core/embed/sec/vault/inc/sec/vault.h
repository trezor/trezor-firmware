/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Versioned, bounded, pointer-free wire messages. Private wallet values stay
 * sealed, except the explicit backup and protocol export operations. */
#include <sec/vault_mode.h>
#define VAULT_ABI (35 + VAULT_SEAL_MODE)
#define VAULT_DATA_SIZE 256
/* Covers FIDO self-attestation and Solana packets without enlarging normal
 * RPCs. */
#define VAULT_ED25519_MAX_MESSAGE 4096
#define VAULT_SECRET_SIZE 160
/* Encode depth/child, chain code, private scalar, cached public key,
 * cache flag, curve ID and the Cardano private-key extension.
 */
#define VAULT_NODE_SIZE 139
#define VAULT_NODE_CIPHERTEXT_SIZE VAULT_NODE_SIZE
#define VAULT_NODE_BLOB_SIZE \
  (VAULT_HEADER_SIZE + VAULT_NODE_CIPHERTEXT_SIZE + VAULT_TAG_SIZE)
#define VAULT_CURVE_SIZE 32
typedef enum { SECRET_BYTES = 1, SECRET_NODE = 2 } secret_kind_t;
/* Kernel-sealed, client-held records start with owner, kind, length and type.
 * GCM adds a nonce u64, actual-length ciphertext and a 16-byte tag.
 * The complete header is authenticated. Nodes encode VAULT_NODE_SIZE bytes;
 * wire padding is zero. Records are opaque; an all-zero blob is empty. */
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
  VAULT_SLIP21,
  VAULT_CARDANO = 30,
  VAULT_ED_SIGN_EXT,
  VAULT_CHACHA_BLOCK,
  VAULT_CHACHA_TAG,
  VAULT_MNEMONIC,
  VAULT_AUTHORIZE_LOCKED,
  VAULT_MONERO_PUBLIC,
  VAULT_ECDH,
  VAULT_KEYVALUE_DERIVE,
  VAULT_AES_CBC,
  VAULT_OPEN_NATIVE = 128
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
  vault_blob_t extension;
} vault_message_request_t;
typedef struct {
  union {
    struct {
      vault_blob_t blob;
      uint32_t value, parent, depth, child_num;
      uint8_t chain_code[32], public_key[33];
    };
    uint8_t signature[65];
    uint8_t data[VAULT_DATA_SIZE];
    uint8_t opened[VAULT_SECRET_SIZE];
  };
} vault_response_t;
/* Owner bookkeeping is bounded and safe inside a storage UI callback. */
static inline bool vault_is_lifecycle(uint32_t op) {
  return op >= VAULT_OWNER_CREATE && op <= VAULT_RESET;
}
typedef struct {
  uint32_t abi, op, owner;
} vault_lifecycle_request_t;
typedef struct {
  uint32_t value, parent;
} vault_lifecycle_response_t;
/* Client entrypoint: syscall on hardware, same dispatcher in emulator. */
bool vault_call(const vault_request_t *request, vault_response_t *response);
/* Bounded public-message ingress for signing, credential tags and key-value
 * derivation. Private crypto reads one immutable native snapshot. */
bool vault_call_message(const vault_message_request_t *request,
                        const uint8_t *message, size_t length,
                        vault_response_t *response);
#if defined(KERNEL_MODE) || defined(VAULT_TEST)
/* Caller comes from trusted syscall context, never from a request field. */
bool vault_lifecycle_dispatch(uintptr_t caller,
                              const vault_lifecycle_request_t *request,
                              vault_lifecycle_response_t *response);
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
