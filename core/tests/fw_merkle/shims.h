/*
 * Shims shared by the fw_merkle harnesses.
 *
 * The harnesses compile the REAL device sources (boot_header_merkle.c,
 * nrf_image.c) against these instead of the embedded include tree, so what
 * is tested is the shipping implementation rather than a copy of it. That is
 * why the types and IMAGE_HASH_* macros are minimal stand-ins and the hash is a
 * host SHA-256: only the backend changes, never the logic.
 *
 * Delivered to those sources with -include on the command line (see run.sh /
 * run_nrf.sh), which is what lets them keep their normal #include block for the
 * device build. Defining BOOT_HEADER_MERKLE_SHIMMED here rather than passing -D
 * keeps the two in one place.
 *
 * Previously duplicated verbatim in both harnesses; the manifest structs had
 * drifted apart in comments only, but there was nothing stopping them drifting
 * in layout.
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

/* --- boot header, mirroring sec/boot_header.h -----------------------------
 * Needed because boot_header_prefix_extent walks the auth part and the Merkle
 * proof. LAYOUT-CRITICAL: these must match the real structs field for field, or
 * the consent-digest cross-validation proves the wrong thing. consent_test.c
 * derives every offset it pokes from these types (offsetof/sizeof) rather than
 * hardcoding, so a change here follows through to the test automatically. */
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
  uint8_t firmware_type;
  uint8_t padding[3];
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

#define FW_MANIFEST_MAGIC 0x445A5254 /* 'TRZD' */
#define FW_MANIFEST_REGION 0x400     /* mirrors sec/boot_header.h */
#ifndef BOOT_HEADER_MAX_MODULES
#define BOOT_HEADER_MAX_MODULES 8
#endif

typedef struct __attribute__((packed)) {
  uint32_t module_type;
  uint32_t flags;
  uint32_t addr;
  uint32_t chunk_size; /* per-module smart-hashing chunk size (before size) */
  uint32_t size;
  merkle_proof_node_t code_hash; /* smart-hashing chain over the module code */
} firmware_manifest_entry_t;

typedef struct __attribute__((packed)) {
  uint32_t magic;
  uint32_t firmware_variant;
  uint8_t firmware_version[4];
  merkle_proof_node_t translations_root;
  uint32_t module_count;
  firmware_manifest_entry_t entries[];
} firmware_manifest_t;

static inline size_t firmware_manifest_size(const firmware_manifest_t* m) {
  return sizeof(firmware_manifest_t) +
         (size_t)m->module_count * sizeof(firmware_manifest_entry_t);
}

/* the real on-device algorithm, verbatim (we supply the shims above) */
#define BOOT_HEADER_MERKLE_SHIMMED

/* Declarations for the sources the harness links instead of textually
 * including. The public API normally comes from sec/boot_header.h, which cannot
 * be included here; these mirror it, plus the internal points the harness
 * compares directly. */
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
uint8_t firmware_type_compose(uint32_t variant);
uint32_t firmware_type_variant(uint8_t firmware_type);
secbool firmware_type_is_custom(uint8_t firmware_type);
secbool firmware_type_is_official(uint8_t firmware_type);

#include "boot_header_merkle_internal.h"
