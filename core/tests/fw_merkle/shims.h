/*
 * Shims shared by the fw_merkle harnesses.
 *
 * The harnesses compile the real device sources (boot_header_merkle.c,
 * nrf_image.c) against these stand-ins for the embedded include tree, with a
 * host SHA-256 as the hash backend. Delivered with -include (see run*.sh) so
 * the sources keep their normal #include block for the device build.
 */

#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "sha2.h"

#define BOOT_HEADER_MERKLE_SHIMMED

typedef uint32_t secbool;
#define sectrue 0xAAAAAAAAU
#define secfalse 0x00000000U

#define IMAGE_HASH_DIGEST_LENGTH 32
#define IMAGE_HASH_CTX SHA256_CTX
#define IMAGE_HASH_INIT(ctx) sha256_Init(ctx)
#define IMAGE_HASH_UPDATE(ctx, data, len) sha256_Update(ctx, data, len)
#define IMAGE_HASH_FINAL(ctx, out) sha256_Final(ctx, out)

typedef struct {
  uint8_t bytes[32];
} merkle_proof_node_t;

/* Boot header, mirroring sec/boot_header.h. Must match the real structs field
 * for field; consent_test.c derives every offset it pokes from these types. */
#define BOOT_HEADER_MAGIC_TRZQ 0x515A5254 /* 'TRZQ' */
#define BOOT_HEADER_MERKLE_PROOF_MAXLEN (256)
#define BOOT_HEADER_SIGNATURE_COUNT 2
#define BOOT_HEADER_PQ_SIGNATURE_LEN (7856)
#define BOOT_HEADER_EC_SIGNATURE_LEN (64)

typedef struct __attribute__((packed)) {
  uint8_t major;
  uint8_t minor;
  uint8_t patch;
  uint8_t build;
} boot_header_version_t;

typedef struct __attribute__((packed)) {
  uint32_t magic;
  uint32_t hw_model;
  uint32_t hw_revision;
  boot_header_version_t version;
  boot_header_version_t fix_version;
  boot_header_version_t min_prev_version;
  uint8_t monotonic_version;
  uint8_t sigmask;
  uint8_t reserved[2];
  uint32_t header_size;
  uint32_t auth_size;
  uint32_t code_size;
  uint32_t storage_address;
  merkle_proof_node_t firmware_root;
  uint8_t padding[0];
} boot_header_auth_t;

typedef struct __attribute__((packed)) {
  uint32_t node_count;
  merkle_proof_node_t nodes[0];
} boot_header_merkle_proof_t;

typedef struct __attribute__((packed)) {
  uint8_t slh_signature[BOOT_HEADER_SIGNATURE_COUNT]
                       [BOOT_HEADER_PQ_SIGNATURE_LEN];
  uint8_t ec_signature[BOOT_HEADER_SIGNATURE_COUNT]
                      [BOOT_HEADER_EC_SIGNATURE_LEN];
  /* fw_variant_sec_t on device: a 32-bit RM(1,5) codeword, not a byte */
  uint32_t firmware_type;
} boot_header_unauth_t;

static inline size_t boot_header_merkle_proof_size(
    const boot_header_merkle_proof_t* proof) {
  return sizeof(boot_header_merkle_proof_t) +
         (size_t)proof->node_count * sizeof(proof->nodes[0]);
}

#define BOOT_HEADER_MAX_MODULES 8
#define FW_MODULE_SECMON 1
#define FW_MODULE_APP 2
#define FW_MODULE_PRODTEST 3
#define FW_VARIANT_NONE 0
#define FW_VARIANT_CUSTOM 1
#define FW_VARIANT_UNIVERSAL 2
#define FW_VARIANT_BITCOIN_ONLY 3
#define FW_VARIANT_PRODTEST 4

/* Hardened variant codewords carried by the manifest field and the boot
 * header's firmware_type; mirrors FW_VARIANT_SEC_* in sec/boot_header.h. The
 * small values above are only the storage-KDF / legacy form. */
typedef uint32_t fw_variant_sec_t;
#define FW_VARIANT_SEC_INVALID 0x00000000U
#define FW_VARIANT_SEC_NONE 0xCCCCCCCCU
#define FW_VARIANT_SEC_CUSTOM 0x33333333U
#define FW_VARIANT_SEC_UNIVERSAL 0x5A5A5A5AU
#define FW_VARIANT_SEC_BITCOIN_ONLY 0xA5A5A5A5U
#define FW_VARIANT_SEC_PRODTEST 0x66666666U

#define FW_MANIFEST_MAGIC 0x445A5254 /* 'TRZD' */
#define FW_MANIFEST_REGION 0x400     /* mirrors sec/boot_header.h */

typedef struct __attribute__((packed)) {
  uint32_t module_type;
  uint32_t flags;
  uint32_t addr;
  uint32_t chunk_size; /* smart-hashing chunk size */
  uint32_t size;
  merkle_proof_node_t code_hash; /* smart-hashing chain over the module code */
} firmware_manifest_entry_t;

typedef struct __attribute__((packed)) {
  uint32_t magic;
  fw_variant_sec_t firmware_variant;
  uint8_t firmware_version[4];
  merkle_proof_node_t translations_root;
  uint32_t module_count;
  firmware_manifest_entry_t entries[];
} firmware_manifest_t;

/* Same arithmetic as sec/boot_header.h: module_count is untrusted there, so
 * keep the two identical. */
static inline size_t firmware_manifest_size(const firmware_manifest_t* m) {
  return sizeof(firmware_manifest_t) +
         (size_t)m->module_count * sizeof(firmware_manifest_entry_t);
}

/* Mirrors of the sec/boot_header.h API the harnesses link against, plus the
 * internal points they compare directly. */
secbool firmware_verify_manifest(const firmware_manifest_t* manifest,
                                 size_t manifest_len, uintptr_t firmware_base,
                                 const merkle_proof_node_t* proof,
                                 size_t proof_count,
                                 const merkle_proof_node_t* trusted_root);
secbool boot_header_prefix_extent(const uint8_t* data, size_t len,
                                  size_t* out_extent);
secbool boot_header_consent_digest(const uint8_t* prefix, size_t prefix_len,
                                   const uint8_t* manifest, size_t manifest_len,
                                   merkle_proof_node_t* out);
secbool firmware_manifest_authentic(const firmware_manifest_t* manifest,
                                    size_t manifest_len,
                                    const merkle_proof_node_t* proof,
                                    size_t proof_count,
                                    const merkle_proof_node_t* trusted_root);
uint8_t fw_variant_to_fw_type(fw_variant_sec_t variant);
secbool fw_variant_is_official(fw_variant_sec_t variant);
secbool fw_variant_is_custom(fw_variant_sec_t variant);
secbool fw_variant_is_provisioned(fw_variant_sec_t variant);

#include "boot_header_merkle_internal.h"
