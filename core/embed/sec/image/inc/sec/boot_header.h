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

/** Maximum number of on-device modules combined into a firmware Merkle root.
 *
 * Purely a device-side capacity bound: it bounds-checks the untrusted
 * manifest module_count before iterating the directory in
 * firmware_verify_manifest. It is NOT stored in any signed/persisted struct, so
 * it can be raised freely -- a larger cap only lets the device accept more
 * modules and
 * never invalidates existing images (the device's cap must be >= the module
 * count of any image it loads). Sized for the largest anticipated set (secmon +
 * kernel + coreapp + nRF) with headroom to spare. */
#define BOOT_HEADER_MAX_MODULES 8

/** Maximum firmware Merkle proof nodes stored in the boot header (the co-path
 *  from the installed variant_root up to firmware_root; depth is
 *  ceil(log2(number of variants)), so 4 covers up to 16 variants).
 *
 *  This is a fixed reservation in the (unauthenticated) boot header: the
 * founder signs one header per model that all its variants share, and the
 * bootloader writes the device's actual proof into this slot at install time,
 * so the slot must hold the deepest variant proof. Raising it only costs 32
 * bytes/node of unauth space; it is NOT authenticated, so changing it never
 * invalidates signatures. Sized for up to 16 firmware variants. */
#define BOOT_HEADER_FW_PROOF_MAX_NODES 4

/**
 * Reserved region at the very start of the firmware image (before the first
 * module), holding the firmware manifest (see firmware_manifest_t). The first
 * module's code begins this many bytes after the firmware region start. Fixed
 * layout constant -- matches the `.manifest` reserve in the *_pq.ld linker
 * scripts, the post-build manifest writer, and the signer.
 */
#define FW_MANIFEST_REGION 0x400

/** Firmware module type / role (bound into the leaf via the header).
 *
 * SECMON is the secure monitor; APP is the non-secure application (kernel +
 * coreapp) that the secmon launches; PRODTEST is a standalone secure
 * factory-test image (its own single-module variant, no non-secure app). Only
 * APP may deviate from the founder manifest in a custom install -- SECMON and
 * PRODTEST are always founder-bound (see firmware_verify_manifest). */
typedef enum {
  FW_MODULE_SECMON = 1,
  FW_MODULE_APP = 2,  // non-secure application (kernel+coreapp)
  FW_MODULE_PRODTEST = 3,
} fw_module_type_t;

/**
 * Firmware variant, authenticated in the module header.
 *
 * This is the founder-committed btc-only/universal/... axis (storage
 * separation). The official-vs-custom axis is NOT stored here -- it is derived
 * from the verification outcome (founder tree = official; delegation/unhashed =
 * custom). Variant-agnostic modules that are shared across variants (e.g. the
 * secmon) use FW_VARIANT_NONE so their header/leaf stays identical everywhere.
 *
 * Values MUST match `vendor_fw_type_t` (sec/image.h) -- the same vocabulary the
 * legacy vendor-header `fw_type` and the model vendorheader JSONs use -- so a
 * given variant maps to the same firmware_type byte in both schemes. The custom
 * value (1) is intentionally absent: "custom" is the FW_TYPE_CUSTOM_FLAG bit,
 * not a variant. (Static-asserted against vendor_fw_type_t in boot_header.c.)
 */
typedef enum {
  FW_VARIANT_NONE = 0,          // == VENDOR_FW_TYPE_RESERVED
  FW_VARIANT_UNIVERSAL = 2,     // == VENDOR_FW_TYPE_UNIVERSAL
  FW_VARIANT_BITCOIN_ONLY = 3,  // == VENDOR_FW_TYPE_BTC_ONLY
  FW_VARIANT_PRODTEST = 4,      // == VENDOR_FW_TYPE_PRODTEST
} fw_variant_t;

/*
 * Layout of the resolved firmware_type byte (the storage-domain identity the
 * bootloader persists to boot_header_unauth_t.firmware_type). It combines BOTH
 * storage-separation axes:
 *   low 7 bits : variant (fw_variant_t) -- authenticated in the module header
 *   high bit   : custom flag            -- derived from the verification tier
 * Per-vendor isolation (tier 2) folds into the storage entropy, not this byte.
 */
#define FW_TYPE_VARIANT_MASK 0x7F
#define FW_TYPE_CUSTOM_FLAG 0x80

/** Magic at the start of a firmware manifest ('TRZD', little-endian u32). */
#define FW_MANIFEST_MAGIC 0x445A5254

/** Manifest entry `flags` bits. */
// The secure boot/entry module -- the one the bootloader jumps to in secure
// mode (the secmon for firmware variants, the prodtest module for prodtest).
// Exactly one entry per manifest must set it; the device rejects a manifest
// otherwise. This is authenticated (in the variant leaf) and decouples entry
// selection from the module type and from the entry ordering.
#define FW_MANIFEST_ENTRY_FLAG_BOOT 0x1

/**
 * One entry of a firmware manifest's module directory.
 *
 * Commits directly to the module's code: `code_hash` is the SHA-256 of the
 * whole module (`size` bytes at `addr`). There is no separate per-module header
 * -- the manifest entry IS the module's authenticated descriptor, so the
 * commitment is a single hop (variant leaf -> manifest -> code_hash -> code).
 * `addr` is the module code's offset from the firmware region start;
 * `module_type`/`size`/`code_hash` are all authenticated via the manifest leaf.
 */
typedef struct __attribute__((packed)) {
  uint32_t module_type; /**< fw_module_type_t (role) */
  uint32_t flags;       /**< FW_MANIFEST_ENTRY_FLAG_* (e.g. _FLAG_BOOT) */
  uint32_t addr;        /**< module code offset from the firmware region start */
  uint32_t size;        /**< module code size */
  merkle_proof_node_t code_hash; /**< SHA-256 over the whole module code */
} firmware_manifest_entry_t;

/**
 * Firmware manifest ("firmware directory") -- the variant leaf.
 *
 * Placed at the start of the firmware image, before the modules. It is
 * the per-variant node of the firmware Merkle tree: the variant leaf is
 * `H(0x00 || manifest)` and folds (via the firmware Merkle proof) up to the
 * signed `firmware_root`. It carries the authenticated variant identity plus
 * the roots of the app and translation subtrees, and a directory of the
 * variant's modules. Layout matches tools/trezor_core_tools/firmware_module.py
 * byte-for-byte.
 */
typedef struct __attribute__((packed)) {
  uint32_t magic;            /**< FW_MANIFEST_MAGIC */
  uint32_t firmware_variant; /**< fw_variant_t (authenticated) */
  uint8_t
      firmware_version[4];      /**< major, minor, patch, build (authenticated);
                                     mirrors the kernel+coreapp module header so
                                     the install confirm can show it in phase 1 */
  merkle_proof_node_t app_root; /**< root of the app tree (0 if none) */
  merkle_proof_node_t
      translations_root; /**< root of translations (0 if none) */
  uint32_t module_count;
  firmware_manifest_entry_t entries[]; /**< module_count directory entries */
} firmware_manifest_t;

/** Total size in bytes of a firmware manifest (fixed part + entries). */
static inline size_t firmware_manifest_size(const firmware_manifest_t* m) {
  return sizeof(firmware_manifest_t) +
         (size_t)m->module_count * sizeof(firmware_manifest_entry_t);
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
   */
  uint8_t firmware_type;
  uint8_t padding[3];
  //todo - rozsirit na 32 bit - FIH

  /* Firmware Merkle proof: the co-path from the installed firmware's
   * variant_root up to the founder-signed firmware_root (boot_header_auth_t.
   * firmware_root). It authenticates that this device's single installed
   * variant is a member of the multi-variant firmware tree. Written by the
   * bootloader at install time (from the update message / factory
   * provisioning), like firmware_type. Unauthenticated: it is verified by
   * recomputation at boot (firmware_verify_manifest recomputes the root and
   * compares to the signed firmware_root), so a wrong proof simply fails
   * verification.
   * A count of 0 means a single-variant tree where variant_root ==
   * firmware_root (no fold), which is the backward-compatible default.
   *
   * NOTE: this is the FIRMWARE tree proof; do not confuse it with
   * boot_header_merkle_proof_t, which is the BOOTLOADER's own co-path in the
   * founder bootloader tree.
   *
   * Appended at the END of the unauth part (per the warning above) so older
   * boardloaders -- which locate the signatures at the start of the unauth part
   * via the self-describing auth_size -- are unaffected.
   *
   * Present ONLY in PQ_SECURE_BOOT builds: it is meaningful only for the
   * Merkle-tree firmware scheme. Non-pq boot_ucb models (which have no firmware
   * tree) keep the shorter unauth part, so their existing signed bootloaders
   * stay byte-compatible. The parser (trezorlib BootHeaderUnauth) treats it as
   * optional and locates the code via header_size, so it reads both layouts;
   * new unauth fields are appended after this one (see boot-header budget). */
#ifdef PQ_SECURE_BOOT
  uint32_t firmware_proof_count;
  merkle_proof_node_t firmware_proof_nodes[BOOT_HEADER_FW_PROOF_MAX_NODES];
#endif

} boot_header_unauth_t;

/**
 * Verifies the integrity of the boot header.
 *
 * Checks the magic number, header size, code size, hardware model and revision
 *
 * @param address Address of the boot header in flash memory
 * @return Pointer to the boot header if valid, NULL otherwise.
 */
const boot_header_auth_t* boot_header_auth_get(uint32_t address);

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
 * @param code_address Address of the bootloader code in flash memory
 * @param root Pointer to the output Merkle root node
 */
void boot_header_calc_merkle_root(const boot_header_auth_t* hdr,
                                  uint32_t code_address,
                                  merkle_proof_node_t* root);

/**
 * Header-only manifest authenticity: variant leaf == firmware_root (via proof).
 *
 * Computes the variant leaf H(0x00 || manifest) and folds `proof` up to the
 * root, requiring it equals `trusted_root`. Does NOT read any module code (the
 * bodies need not be present), so the update preamble can authenticate the
 * manifest -- and trust its `firmware_variant` / directory -- before streaming.
 * `firmware_verify_manifest` is the full check (this + per-module integrity).
 *
 * @param manifest Manifest bytes
 * @param manifest_len Manifest length (firmware_manifest_size)
 * @param proof Firmware Merkle proof (variant leaf -> firmware_root); may be
 * NULL
 * @param proof_count Number of proof nodes
 * @param trusted_root The signed firmware_root to check against
 * @return secbool -- sectrue iff the manifest authenticates against the root
 */
secbool firmware_manifest_authentic(const firmware_manifest_t* manifest,
                                    size_t manifest_len,
                                    const merkle_proof_node_t* proof,
                                    size_t proof_count,
                                    const merkle_proof_node_t* trusted_root);

/**
 * Full firmware verification against firmware_root, driven by the manifest.
 *
 * The module set, roles and layout come from the (authenticated) manifest
 * rather than a hardcoded table.
 *  1. Authenticity: variant leaf = H(0x00 || manifest); fold `proof` up to
 *     the root and require it equals `trusted_root` (the signed firmware_root).
 *  2. Integrity: for each directory entry, the module code at
 *     `firmware_base + addr` (`size` bytes) must hash to the entry's
 *     `code_hash`. Because the entry is authenticated by step 1, this is both
 *     the authenticity and the integrity check for the code, in one hop.
 *
 * @param manifest Manifest at the start of the firmware image
 * @param manifest_len Manifest length in bytes (firmware_manifest_size)
 * @param firmware_base Base address the manifest `addr` offsets are relative to
 *                      (the firmware region start)
 * @param proof Firmware Merkle proof (variant leaf -> firmware_root)
 * @param proof_count Number of proof nodes
 * @param trusted_root The signed firmware_root to check against
 * @param custom If sectrue, allow a CUSTOM (unofficial) install: the non-secmon
 *               module (kernel+coreapp) code_hash is not enforced, so the app
 *               may be any build; the manifest and secmon still bind to the
 *               founder root. If secfalse, every module must match.
 * @return secbool -- sectrue iff authenticity and integrity all hold
 */
secbool firmware_verify_manifest(const firmware_manifest_t* manifest,
                                 size_t manifest_len, uintptr_t firmware_base,
                                 const merkle_proof_node_t* proof,
                                 size_t proof_count,
                                 const merkle_proof_node_t* trusted_root,
                                 secbool custom);

/**
 * Integrity check for ONE manifest directory entry (step 2 of
 * firmware_verify_manifest, for a single module): the module code at
 * `firmware_base + entry->addr` (`entry->size` bytes) must hash to
 * `entry->code_hash`.
 *
 * The manifest carrying `entry` must already be authenticated
 * (firmware_manifest_authentic) so `code_hash` is trusted. Lets a streaming
 * install verify each module the moment its bytes are on flash, instead of
 * waiting for the whole image.
 *
 * @param entry One (authenticated) manifest directory entry
 * @param firmware_base Base address the entry `addr` offset is relative to
 * @param allow_custom If sectrue, skip the code_hash check entirely, so the
 *                     module code may be any (unofficial) build. Must never be
 *                     set for the secmon.
 * @return secbool -- sectrue iff the module code matches the entry's code_hash
 */
secbool firmware_verify_manifest_entry(const firmware_manifest_entry_t* entry,
                                       uintptr_t firmware_base,
                                       secbool allow_custom);

/**
 * Composes the persisted firmware_type byte from the two storage-separation
 * axes: the authenticated `variant` (fw_variant_t) and the derived trust class
 * (`is_custom` -- sectrue for delegated/unhashed, secfalse for official).
 *
 * The result is only trustworthy because the bootloader is the sole writer of
 * the write-protected boot header region; it must be *derived* from the
 * authenticated variant + verification outcome, never taken from an untrusted
 * input. Storage entropy / wipe-on-change key off this value.
 */
uint8_t firmware_type_compose(uint32_t variant, secbool is_custom);

/** Extracts the variant (fw_variant_t) from a firmware_type byte. */
uint32_t firmware_type_variant(uint8_t firmware_type);

/** Returns sectrue if the firmware_type byte marks custom (vs official). */
secbool firmware_type_is_custom(uint8_t firmware_type);

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
 * @param code_address Address of the new bootloader code in flash memory
 * @return secbool indicating whether the boot header and code need update
 */
secbool bootloader_area_needs_update(const boot_header_auth_t* hdr,
                                     uint32_t code_address);
