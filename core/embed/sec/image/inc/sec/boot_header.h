/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once

#include <trezor_types.h>

#include <sec/image_hash_conf.h>

// Magic number at the start of the boot header
#define BOOT_HEADER_MAGIC_TRZQ 0x515A5254  // TRZQ
// Reserved space for boot header
#define BOOT_HEADER_MAXSIZE (2 * 8192)
/** Number of PQ/EC signatures */
#define BOOT_HEADER_SIGNATURE_COUNT 2
/** Length of PQ signature in bytes */
#define BOOT_HEADER_PQ_SIGNATURE_LEN (7856)
/** Length of EC signature in bytes */
#define BOOT_HEADER_EC_SIGNATURE_LEN (64)
/** Number of reserved slots for Merkle proof */
#define BOOT_HEADER_MERKLE_PROOF_MAXLEN (256)

/**
 * 4-byte version structure used in the boot header
 */
typedef struct __attribute__((packed)) {
  uint8_t major;
  uint8_t minor;
  uint8_t patch;
  uint8_t build;
} boot_header_version_t;

/**
 * Orders two boot header versions, most significant component first.
 *
 * @return <0 if `a` precedes `b`, 0 if they are equal, >0 if `a` follows `b`
 */
static inline int boot_header_version_compare(boot_header_version_t a,
                                              boot_header_version_t b) {
  if (a.major != b.major) return (int)a.major - (int)b.major;
  if (a.minor != b.minor) return (int)a.minor - (int)b.minor;
  if (a.patch != b.patch) return (int)a.patch - (int)b.patch;
  return (int)a.build - (int)b.build;
}

/** Whether a version field is set; 0.0.0.0 means "no constraint". */
static inline bool boot_header_version_is_set(boot_header_version_t v) {
  return (v.major | v.minor | v.patch | v.build) != 0;
}

/**
 * Merkle proof node (SHA-256 digest)
 */
typedef struct {
  uint8_t bytes[32];
} merkle_proof_node_t;

/**
 * Authenticated part of the boot header
 *
 * This structure can be extended in future versions if needed.
 * Just make sure to add new fields at the end of the structure.
 * Never remove or reorder existing fields.
 */
typedef struct __attribute__((packed)) {
  /** Magic constant 'TRZQ' */
  uint32_t magic;
  /** Hardware model, e.g. 'T3W1'. */
  uint32_t hw_model;
  /** Hardware revision, e.g. 1 */
  uint32_t hw_revision;
  /** Bootloader version */
  boot_header_version_t version;
  /** Minimum version that the device can be downgraded to without
   * erasing storage. */
  boot_header_version_t fix_version;
  /** Minimum previous version that the device can be updated from when
   * installing this header. */
  boot_header_version_t min_prev_version;
  /** An integer which must not decrease between updates. */
  uint8_t monotonic_version;
  /** Bitmask of keys used for signature verification.
   * Each bit corresponds to a public key in the BOOTLOADER_PQ_KEY and
   * BOOTLOADER_EC_KEY arrays. If the bit is set, the corresponding key
   * is used for signature verification. */
  uint8_t sigmask;
  /* Reserved bytes (alignment) */
  uint8_t reserved[2];
  /** Size of the entire header in bytes, including the Merkle proof
   * and signatures. It's calculated at link time and must be
   * aligned to 8K boundary. */
  uint32_t header_size;
  /** Size of the authenticated part of the header in bytes.
   * Final value is calculated in post-build step and includes
   * potential padding of the structure. */
  uint32_t auth_size;
  /** Size of the bootloader code in bytes */
  uint32_t code_size;
  /** Address of storage area for storage relocation purposes */
  uint32_t storage_address;
  /* Firmware Merkle tree root */
  merkle_proof_node_t firmware_root;
  /* Padding is automatically added by the post-build step to ensure that
   * the authenticated part of the header is maximized. */
  uint8_t padding[0];

} boot_header_auth_t;

/** Device-side bound on the untrusted manifest module_count. Not stored in
 *  any signed struct, so it can be raised freely. */
#define BOOT_HEADER_MAX_MODULES 8

/** Max firmware Merkle proof nodes in the manifest region (depth is
 *  ceil(log2(variants)); 4 covers 16 variants). Unauthenticated. */
#define FW_MANIFEST_PROOF_MAX_NODES 4

/** Reserved region at the start of the firmware image holding the manifest
 *  and its proof; the first module starts after it. Must match the
 *  `.manifest` reserve in the *_pq.ld scripts and the signer. */
#define FW_MANIFEST_REGION 0x400

/** Smart-hashing chunk size (== COREAPP_ALIGNMENT). Modules are not padded to
 *  it. Must match FW_CHUNK_SIZE in the *_pq.ld scripts / manifest_header.S and
 *  DEFAULT_CHUNK_SIZE in tools/trezor_core_tools/firmware_module.py. */
#define FW_CHUNK_SIZE 0x2000

/** Firmware module role, authenticated in the manifest entry. Only APP may
 *  deviate from the founder manifest in a CUSTOM install. */
typedef enum {
  FW_MODULE_SECMON = 1,
  FW_MODULE_APP = 2,  // non-secure application (kernel+coreapp)
  FW_MODULE_PRODTEST = 3,
} fw_module_type_t;

/**
 * Firmware variant, narrow form. Only ever the OUTPUT of fw_variant_to_fw_type
 * (the storage-salt byte); everything stored or compared uses the hardened
 * fw_variant_sec_t codewords below. Values must match vendor_fw_type_t
 * (sec/image.h); static-asserted in boot_header.c.
 */
typedef enum {
  FW_VARIANT_NONE = 0,       // == VENDOR_FW_TYPE_RESERVED
  FW_VARIANT_CUSTOM = 1,     // == VENDOR_FW_TYPE_CUSTOM (unofficial app slot)
  FW_VARIANT_UNIVERSAL = 2,  // == VENDOR_FW_TYPE_UNIVERSAL
  FW_VARIANT_BITCOIN_ONLY = 3,  // == VENDOR_FW_TYPE_BTC_ONLY
  FW_VARIANT_PRODTEST = 4,      // == VENDOR_FW_TYPE_PRODTEST
} fw_variant_t;

/**
 * Hardened firmware variant, stored as-is in both the authenticated manifest
 * and boot_header_unauth_t.firmware_type. fw_variant_t values are one bit flip
 * apart (CUSTOM(1) -> BITCOIN_ONLY(3), NONE(0) -> PRODTEST(4)); these RM(1,5)
 * codewords are >= 16 flips apart and from 0x00000000 / 0xFFFFFFFF, so
 * zeroed, erased or torn memory decodes to INVALID. FIH: never compare a
 * codeword against a narrow FW_VARIANT_* value (compiles, always false).
 */
typedef uint32_t fw_variant_sec_t;
#define FW_VARIANT_SEC_INVALID 0x00000000U /**< not a variant */
#define FW_VARIANT_SEC_NONE 0xCCCCCCCCU    /**< unprovisioned */
#define FW_VARIANT_SEC_CUSTOM 0x33333333U
#define FW_VARIANT_SEC_UNIVERSAL 0x5A5A5A5AU
#define FW_VARIANT_SEC_BITCOIN_ONLY 0xA5A5A5A5U
#define FW_VARIANT_SEC_PRODTEST 0x66666666U

/** Magic at the start of a firmware manifest ('TRZD', little-endian u32). */
#define FW_MANIFEST_MAGIC 0x445A5254

/** Manifest entry `flags` bits. */
// The module the bootloader jumps to in secure mode; exactly one entry per
// manifest must set it (authenticated).
#define FW_MANIFEST_ENTRY_FLAG_BOOT 0x1

/**
 * One entry of a firmware manifest's module directory. `code_hash` is the
 * smart-hashing chain over `size` bytes at `addr` (offset from the firmware
 * region start), chunked by `chunk_size`. `chunk_size` precedes `size` so the
 * CUSTOM variant's zeroed tail (`size` + `code_hash`) leaves it authenticated.
 */
typedef struct __attribute__((packed)) {
  uint32_t module_type; /**< fw_module_type_t (role) */
  uint32_t flags;       /**< FW_MANIFEST_ENTRY_FLAG_* */
  uint32_t addr;       /**< module code offset from the firmware region start */
  uint32_t chunk_size; /**< smart-hashing chunk size; bounded only at install */
  uint32_t size;       /**< module code size */
  merkle_proof_node_t
      code_hash; /**< smart-hashing chain over the module code */
} firmware_manifest_entry_t;

/**
 * Firmware manifest -- the variant leaf H(0x00 || manifest), placed at the
 * start of the firmware image. The firmware Merkle proof follows it at
 * firmware_manifest_size, OUTSIDE the leaf. Layout must match
 * tools/trezor_core_tools/firmware_module.py byte-for-byte.
 */
typedef struct __attribute__((packed)) {
  uint32_t magic;                    /**< FW_MANIFEST_MAGIC */
  fw_variant_sec_t firmware_variant; /**< hardened variant codeword */
  uint8_t firmware_version[4];       /**< major, minor, patch, build */
  merkle_proof_node_t
      translations_root;               /**< root of translations (0 if none) */
  uint32_t module_count;               /**< number of directory entries */
  firmware_manifest_entry_t entries[]; /**< module_count directory entries */
} firmware_manifest_t;

/** Total size of a manifest (fixed part + entries) -- the span the variant
 *  leaf covers. `module_count` must be bounded first (firmware_manifest_
 *  layout_valid / _authentic / _read_proof): the product wraps in 32 bits. */
static inline size_t firmware_manifest_size(const firmware_manifest_t* m) {
  return sizeof(firmware_manifest_t) +
         (size_t)m->module_count * sizeof(firmware_manifest_entry_t);
}

/**
 * Firmware Merkle proof: co-path from the variant leaf to firmware_root, placed
 * right after the manifest within FW_MANIFEST_REGION (outside the leaf).
 * Unauthenticated -- verified by folding. node_count 0 means the variant leaf
 * is firmware_root. Layout must match firmware_module.py.
 */
typedef struct __attribute__((packed)) {
  uint32_t node_count; /**< proof nodes (<= FW_MANIFEST_PROOF_MAX_NODES) */
  merkle_proof_node_t nodes[]; /**< node_count co-path nodes */
} firmware_manifest_proof_t;

/** Pointer to the embedded proof. No bounds check -- use
 *  firmware_manifest_read_proof for untrusted input. */
static inline const firmware_manifest_proof_t* firmware_manifest_proof(
    const firmware_manifest_t* m) {
  return (const firmware_manifest_proof_t*)((const uint8_t*)m +
                                            firmware_manifest_size(m));
}

/**
 * Bounds-checked read of the embedded proof; `avail` is the number of bytes
 * available from the manifest start. Fails closed with cleared outputs;
 * *out_nodes is NULL when node_count == 0.
 */
static inline secbool firmware_manifest_read_proof(
    const firmware_manifest_t* m, size_t avail,
    const merkle_proof_node_t** out_nodes, size_t* out_count) {
  *out_nodes = NULL;
  *out_count = 0;
  // Bound module_count before firmware_manifest_size can wrap.
  if (m->module_count == 0 || m->module_count > BOOT_HEADER_MAX_MODULES) {
    return secfalse;
  }
  size_t manifest_len = firmware_manifest_size(m);
  if (avail < manifest_len + sizeof(uint32_t)) {
    return secfalse;
  }
  const firmware_manifest_proof_t* p = firmware_manifest_proof(m);
  uint32_t count = p->node_count;
  if (count > FW_MANIFEST_PROOF_MAX_NODES) {
    return secfalse;
  }
  if (avail < manifest_len + sizeof(uint32_t) +
                  (size_t)count * sizeof(merkle_proof_node_t)) {
    return secfalse;
  }
  *out_count = count;
  *out_nodes = (count > 0) ? p->nodes : NULL;
  return sectrue;
}

/**
 * Merkle proof structure used in the boot header to calculate the root
 * of the Merkle tree. It is placed just after the authenticated part
 * of the boot header.
 *
 * WARNING: This struct must not change, otherwise old boardloaders will
 * not interpret the header correctly. Any new unauthenticated fields
 * must be added at the end of `boot_header_unauth_t`.
 */
typedef struct __attribute__((packed)) {
  /** Number of nodes in the array below */
  uint32_t node_count;
  /** Merkle proof used for root calculation */
  merkle_proof_node_t nodes[0];

} boot_header_merkle_proof_t;

/**
 * Unauthenticated part of the boot header containing signatures and
 * other information that need not (or must not) be authenticated.
 * It is placed right after the Merkle proof.
 */
typedef struct __attribute__((packed)) {
  /** PQ signatures */
  uint8_t slh_signature[BOOT_HEADER_SIGNATURE_COUNT]
                       [BOOT_HEADER_PQ_SIGNATURE_LEN];
  /** EC signatures */
  uint8_t ec_signature[BOOT_HEADER_SIGNATURE_COUNT]
                      [BOOT_HEADER_EC_SIGNATURE_LEN];

  /* Firmware type
   * This field is modified by the bootloader during the
   * update process). It indicates the current firmware type (custom,
   * universal, bitcoin-only, etc.) and is used to determine whether
   * the storage should be erased before the update.
   * Copied from the authenticated manifest variant; trusted only because the
   * bootloader is the sole writer of this write-protected region.
   */
  fw_variant_sec_t firmware_type;

  /* The firmware Merkle proof is NOT stored here; it lives in the firmware
   * image (firmware_manifest_proof_t). New unauth fields go at the END. */

} boot_header_unauth_t;

/**
 * Verifies the integrity of the boot header.
 *
 * Checks the magic number, header size, code size, hardware model and revision
 *
 * @param header Address of the boot header (any readable buffer)
 * @return Pointer to the boot header if valid, NULL otherwise.
 */
const boot_header_auth_t* boot_header_auth_get(uintptr_t header);

/**
 * Gets pointer to the unauthenticated part of the boot header.
 *
 * @param hdr Pointer to the authenticated part of the boot header
 * @return Pointer to the unauthenticated part of the boot header or NULL if the
 *         header is invalid.
 */
const boot_header_unauth_t* boot_header_unauth_get(
    const boot_header_auth_t* hdr);

/**
 *  Calculates the Merkle root for signature verification.
 *
 * The result includes the bootloader code, authenticated part of the
 * boot header and the Merkle tree path.
 *
 * @param hdr Pointer to the boot header
 * @param code Address of the bootloader code
 * @param root Pointer to the output Merkle root node
 */
void boot_header_calc_merkle_root(const boot_header_auth_t* hdr, uintptr_t code,
                                  merkle_proof_node_t* root);

/**
 * As boot_header_calc_merkle_root, but takes H(code) instead of the code, so
 * the signature can be checked before the code arrives. The caller must still
 * recompute the digest over the real bytes once they land.
 *
 * @param hdr Pointer to the boot header
 * @param code_hash IMAGE_HASH_DIGEST_LENGTH bytes, the digest of the code
 * @param root Pointer to the output Merkle root node
 */
void boot_header_calc_merkle_root_from_hash(
    const boot_header_auth_t* hdr,
    const uint8_t code_hash[IMAGE_HASH_DIGEST_LENGTH],
    merkle_proof_node_t* root);

/** Size in bytes of a boot header Merkle proof (fixed part + nodes). */
static inline size_t boot_header_merkle_proof_size(
    const boot_header_merkle_proof_t* proof) {
  return sizeof(boot_header_merkle_proof_t) +
         (size_t)proof->node_count * sizeof(proof->nodes[0]);
}

/**
 * @brief Extent of the boot header PREFIX: authenticated part + Merkle proof,
 *        excluding the unauthenticated part (which need not be present).
 *
 * @param data Start of a boot header, or of a prefix of one
 * @param len Bytes available at `data`
 * @param out_extent Receives auth_size + proof size
 * @return sectrue iff the prefix is well-formed within `len`
 */
secbool boot_header_prefix_extent(const uint8_t* data, size_t len,
                                  size_t* out_extent);

/**
 * @brief Consent digest of an interaction-less upgrade:
 *        H(header prefix || firmware manifest). Firmware and bootloader must
 *        both use this. The unauth part is excluded on purpose (signatures,
 *        and firmware_type, which the bootloader rewrites). Known gap: the
 *        bootloader CODE is not pinned, only its auth part.
 *
 * @param prefix Boot header prefix (auth part + Merkle proof)
 * @param prefix_len Its length, from `boot_header_prefix_extent`
 * @param manifest Firmware manifest bytes as received
 * @param manifest_len Manifest length (`firmware_manifest_size`)
 * @param out Receives the digest
 * @return sectrue on success
 */
secbool boot_header_consent_digest(const uint8_t* prefix, size_t prefix_len,
                                   const uint8_t* manifest, size_t manifest_len,
                                   merkle_proof_node_t* out);

/**
 * Header-only manifest authenticity: variant leaf folded through `proof` must
 * equal `trusted_root`. Reads no module code. For CUSTOM the leaf hashes
 * firmware_version and the APP entry's size + code_hash as zero.
 *
 * @param manifest Manifest bytes
 * @param manifest_len Manifest length (firmware_manifest_size)
 * @param proof Firmware Merkle proof (variant leaf -> firmware_root); may be
 * NULL
 * @param proof_count Number of proof nodes
 * @param trusted_root The signed firmware_root to check against
 * @return sectrue iff the manifest authenticates against the root
 */
secbool firmware_manifest_authentic(const firmware_manifest_t* manifest,
                                    size_t manifest_len,
                                    const merkle_proof_node_t* proof,
                                    size_t proof_count,
                                    const merkle_proof_node_t* trusted_root);

/**
 * @brief Checks the module layout: >= 1 module; non-zero chunk_size and size;
 *        ascending, non-overlapping, at/after FW_MANIFEST_REGION, inside
 *        `capacity`. FLASH_BLOCK_SIZE alignment is NOT checked here (sec/
 *        cannot see it); the bootloader enforces it alongside.
 *
 * @param manifest  Manifest at the start of the firmware image
 * @param capacity  Size of the firmware area the modules must fit inside
 * @return sectrue iff the layout is well-formed and within capacity
 */
secbool firmware_manifest_layout_valid(const firmware_manifest_t* manifest,
                                       uint32_t capacity);

/**
 * @brief Full firmware verification: firmware_manifest_authentic, then every
 *        module's code must hash to its entry's code_hash (for the CUSTOM app
 *        that is the creator's hash -- integrity only).
 *
 * @param manifest Manifest at the start of the firmware image
 * @param manifest_len Manifest length in bytes (firmware_manifest_size)
 * @param firmware_base Base address the manifest `addr` offsets are relative to
 * @param proof Firmware Merkle proof (variant leaf -> firmware_root)
 * @param proof_count Number of proof nodes
 * @param trusted_root The signed firmware_root to check against
 * @return sectrue iff authenticity and integrity all hold
 */
secbool firmware_verify_manifest(const firmware_manifest_t* manifest,
                                 size_t manifest_len, uintptr_t firmware_base,
                                 const merkle_proof_node_t* proof,
                                 size_t proof_count,
                                 const merkle_proof_node_t* trusted_root);

/**
 * Integrity check of ONE manifest entry: `size` bytes at `firmware_base +
 * addr` must hash to `code_hash`. The manifest must already be authenticated.
 *
 * @param entry One (authenticated) manifest directory entry
 * @param firmware_base Base address the entry `addr` offset is relative to
 * @return sectrue iff the module code matches the entry's code_hash
 */
secbool firmware_verify_manifest_entry(const firmware_manifest_entry_t* entry,
                                       uintptr_t firmware_base);

/** Upper bound on a model-tree co-path (MODEL_TREE_DEPTH is 4 today). Bounds
 *  an UNTRUSTED proof_count before size arithmetic; the single definition. */
#define MODEL_TREE_MAX_PROOF_NODES 32U

/**
 * Co-processor slot value: what a co-processor's model-tree leaf commits to.
 * The fold sorts pairs (no position), so the role lives in the leaf value.
 * `kind`/`index` come from the verifier's build config, never from the image
 * or the wire; `digest` must exclude the region holding the founder material.
 */
#define COPROC_SLOT_TAG "TRZP"
#define COPROC_SLOT_MODEL_LEN 4
/* SHA-256 width; literal because this header depends only on trezor_types.h */
#define COPROC_SLOT_DIGEST_LEN 32

/** Co-processor kind (a field, not part of the tag). */
typedef enum {
  COPROC_KIND_NRF = 1,
} coproc_kind_t;

typedef struct __attribute__((packed)) {
  uint8_t tag[4];                         /**< COPROC_SLOT_TAG */
  uint8_t model[COPROC_SLOT_MODEL_LEN];   /**< MODEL_INTERNAL_NAME, 4 ASCII */
  uint8_t kind;                           /**< coproc_kind_t (build config) */
  uint8_t index;                          /**< instance of that kind (build
                                               config), 0 today */
  uint8_t reserved[2];                    /**< zero */
  uint8_t digest[COPROC_SLOT_DIGEST_LEN]; /**< per-kind image digest */
} coproc_slot_t;

_Static_assert(sizeof(coproc_slot_t) == 44,
               "coproc_slot_t must be 44 bytes -- it is a leaf preimage shared "
               "with the signer and the nRF's MCUboot");

/**
 * @brief Fold a MODEL-tree slot value (e.g. a coproc_slot_t) up to
 *        `trusted_model_root`. Proves commitment only; identity must be
 *        inside the value.
 *
 * @param slot_value   the committed value (coproc_slot_t for a co-processor)
 * @param slot_len     its length in bytes
 * @param proof        co-path from the slot up to modelRoot
 * @param proof_count  number of co-path nodes (<= MODEL_TREE_MAX_PROOF_NODES)
 * @param trusted_model_root modelRoot recomputed from the verified boot header
 * @return sectrue iff the fold reaches `trusted_model_root`
 */
secbool boot_header_verify_slot(const uint8_t* slot_value, size_t slot_len,
                                const merkle_proof_node_t* proof,
                                size_t proof_count,
                                const merkle_proof_node_t* trusted_model_root);

/** Smart-hashing chain primitives (whole-module recompute + streaming
 *  installer): seed = H(0x01 || size_le32), step = H(0x02 || h || chunk),
 *  folded last chunk -> first (docs/core/embed-arch/firmware-merkle-tree.md).
 */
void firmware_module_chain_seed(uint32_t size, uint8_t* out);
void firmware_module_chain_step(const uint8_t* h_prev, const uint8_t* data,
                                size_t len, uint8_t* out);

/** Display name for a hardened variant ("Trezor", "Trezor Bitcoin-only", or
 *  an UNSAFE marker). Must agree with the bootloader's tree_vendor_str. Never
 *  returns NULL. */
const char* firmware_vendor_str(fw_variant_sec_t variant);

/** The ONLY narrowing to the fw_variant_t byte, for the storage KDF
 *  (secret_key_storage_salt). Returns FW_VARIANT_NONE for INVALID. */
uint8_t fw_variant_to_fw_type(fw_variant_sec_t variant);

/** Positive allow-list: sectrue only for a recognized official variant. */
secbool fw_variant_is_official(fw_variant_sec_t variant);

/** sectrue only for FW_VARIANT_SEC_CUSTOM. To grant privileges use
 *  fw_variant_is_official(), never !is_custom. */
secbool fw_variant_is_custom(fw_variant_sec_t variant);

/** sectrue only for one of the four real image variants; NONE and INVALID
 *  both return secfalse. */
secbool fw_variant_is_provisioned(fw_variant_sec_t variant);

/**
 * Checks the signature in the boot header against the public keys.
 *
 * This function checks the signatures of the boot header using the
 * bootloader public keys. It uses the Merkle root calculated from
 * the boot header and bootloader code to perform the verification.
 *
 * @param hdr Pointer to the boot header
 * @param merkle_root Pointer to the Merkle root
 * @return secbool indicating whether the signature verification was successful.
 */
secbool boot_header_check_signature(const boot_header_auth_t* hdr,
                                    const merkle_proof_node_t* merkle_root);

/**
 * This function compares the boot header and the bootloader code
 * with the installed bootloader header and code. If they are different,
 * it returns sectrue, otherwise secfalse.
 *
 * @param hdr Pointer to the new boot header
 * @param code Address of the new bootloader code
 * @param prev_header Address of the installed boot header; the installed code
 *        is taken to follow it, at its own `header_size`
 * @return secbool indicating whether the boot header and code need update
 */
secbool bootloader_area_needs_update(const boot_header_auth_t* hdr,
                                     uintptr_t code, uintptr_t prev_header);
