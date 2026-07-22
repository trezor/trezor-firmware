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

/** Maximum firmware Merkle proof nodes reserved in the manifest region (the
 *  co-path from this variant's leaf up to firmware_root; depth is
 *  ceil(log2(number of variants)), so 4 covers up to 16 variants).
 *
 *  The proof lives in the firmware image's manifest region, right after the
 *  manifest (firmware_manifest_proof_t), OUTSIDE the variant leaf -- so the
 *  firmware image carries its own proof and NONE is stored in the boot header.
 *  It is unauthenticated (verified by folding the variant leaf to the signed
 *  firmware_root at boot), so raising this never invalidates signatures; it only
 *  costs 32 bytes/node of the FW_MANIFEST_REGION budget. Sized for up to 16
 *  firmware variants. */
#define FW_MANIFEST_PROOF_MAX_NODES 4

/**
 * Reserved region at the very start of the firmware image (before the first
 * module), holding the firmware manifest (see firmware_manifest_t) followed by
 * the firmware Merkle proof (see firmware_manifest_proof_t). The first module's
 * code begins this many bytes after the firmware region start. Fixed layout
 * constant -- matches the `.manifest` reserve in the *_pq.ld linker scripts, the
 * post-build manifest writer, and the signer. Must fit the largest manifest plus
 * the proof: sizeof(firmware_manifest_t) + BOOT_HEADER_MAX_MODULES entries +
 * sizeof(firmware_manifest_proof_t) with FW_MANIFEST_PROOF_MAX_NODES nodes.
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
 * Firmware variant, authenticated in the manifest (firmware_manifest_t.
 * firmware_variant, part of the variant leaf).
 *
 * The founder-committed storage-separation axis: btc-only / universal /
 * prodtest / ... AND custom. `FW_VARIANT_CUSTOM` is a FIRST-CLASS variant, not a
 * flag: the founder signs a custom slot into the tree whose kernel+coreapp
 * (FW_MODULE_APP) code_hash is ZERO, so any creator's app folds to the same
 * authenticated leaf (the app is founder-UNauthenticated by design -- only
 * integrity-checked against the on-flash creator hash; see
 * firmware_verify_manifest). Variant-agnostic modules shared across variants
 * (e.g. the secmon) use FW_VARIANT_NONE so their leaf stays identical everywhere.
 *
 * Values MUST match `vendor_fw_type_t` (sec/image.h) -- the same vocabulary the
 * legacy vendor-header `fw_type` and the model vendorheader JSONs use -- so a
 * given variant maps to the same firmware_type byte in both schemes.
 * (Static-asserted against vendor_fw_type_t in boot_header.c.)
 */
typedef enum {
  FW_VARIANT_NONE = 0,          // == VENDOR_FW_TYPE_RESERVED
  FW_VARIANT_CUSTOM = 1,        // == VENDOR_FW_TYPE_CUSTOM (unofficial app slot)
  FW_VARIANT_UNIVERSAL = 2,     // == VENDOR_FW_TYPE_UNIVERSAL
  FW_VARIANT_BITCOIN_ONLY = 3,  // == VENDOR_FW_TYPE_BTC_ONLY
  FW_VARIANT_PRODTEST = 4,      // == VENDOR_FW_TYPE_PRODTEST
} fw_variant_t;

/*
 * The resolved firmware_type byte (the storage-domain identity the bootloader
 * persists to boot_header_unauth_t.firmware_type) IS the authenticated variant
 * (fw_variant_t). Custom-ness is the variant value (FW_VARIANT_CUSTOM), not a
 * separate flag: official and custom therefore occupy distinct storage domains,
 * and custom<->custom stays a single shared domain. Per-vendor isolation (tier 2)
 * folds into the storage entropy, not this byte.
 */

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
 * signed `firmware_root`. It carries the authenticated variant identity plus the
 * translations subtree root and a directory of the variant's modules. The
 * firmware Merkle proof (firmware_manifest_proof_t) follows immediately after
 * (at firmware_manifest_size), OUTSIDE the leaf. Layout matches
 * tools/trezor_core_tools/firmware_module.py byte-for-byte.
 */
typedef struct __attribute__((packed)) {
  uint32_t magic;            /**< FW_MANIFEST_MAGIC */
  uint32_t firmware_variant; /**< fw_variant_t (authenticated) */
  uint8_t
      firmware_version[4];      /**< major, minor, patch, build (authenticated);
                                     mirrors the kernel+coreapp module header so
                                     the install confirm can show it in phase 1 */
  merkle_proof_node_t
      translations_root; /**< root of translations (0 if none) */
  uint32_t module_count;
  firmware_manifest_entry_t entries[]; /**< module_count directory entries */
} firmware_manifest_t;

/** Total size in bytes of a firmware manifest (fixed part + entries). This is
 *  exactly the span the variant leaf H(0x00 || manifest) covers; the firmware
 *  Merkle proof begins right after it (see firmware_manifest_proof_t). */
static inline size_t firmware_manifest_size(const firmware_manifest_t* m) {
  return sizeof(firmware_manifest_t) +
         (size_t)m->module_count * sizeof(firmware_manifest_entry_t);
}

/**
 * Firmware Merkle proof embedded in the manifest region.
 *
 * Placed immediately after the manifest (at offset firmware_manifest_size),
 * within FW_MANIFEST_REGION and OUTSIDE the variant leaf -- the leaf is
 * H(0x00 || manifest), covering only firmware_manifest_size bytes, so the proof
 * is excluded by construction (no circularity: a proof cannot be inside the
 * bytes it proves). The firmware image thus carries its own co-path
 * (variant leaf -> firmware_root); NO proof is stored in the boot header.
 *
 * Unauthenticated: verified by folding the variant leaf through it to the
 * (signed) firmware_root at boot, so a wrong proof simply fails verification. A
 * node_count of 0 means a single-variant tree (variant leaf == firmware_root, an
 * identity fold) -- the backward-compatible default. Layout matches
 * tools/trezor_core_tools/firmware_module.py byte-for-byte.
 */
typedef struct __attribute__((packed)) {
  uint32_t node_count; /**< proof nodes (<= FW_MANIFEST_PROOF_MAX_NODES) */
  merkle_proof_node_t nodes[]; /**< node_count co-path nodes */
} firmware_manifest_proof_t;

/** Pointer to the embedded proof (immediately after the manifest). Bounds are
 *  NOT checked here -- use firmware_manifest_read_proof for untrusted input. */
static inline const firmware_manifest_proof_t* firmware_manifest_proof(
    const firmware_manifest_t* m) {
  return (const firmware_manifest_proof_t*)((const uint8_t*)m +
                                            firmware_manifest_size(m));
}

/**
 * Bounds-checked read of the embedded firmware proof.
 *
 * `avail` is the number of bytes available from the manifest start -- the flash
 * region size FW_MANIFEST_REGION at boot / phase-2 install, or the received blob
 * length in the FirmwareBegin preamble. Verifies the node_count field and all
 * its nodes fit within `avail` and node_count <= FW_MANIFEST_PROOF_MAX_NODES.
 *
 * On success returns sectrue and sets *out_nodes (NULL when node_count == 0) and
 * *out_count. On any bound/cap violation returns secfalse (fail-closed) and
 * leaves the outputs cleared.
 */
static inline secbool firmware_manifest_read_proof(
    const firmware_manifest_t* m, size_t avail,
    const merkle_proof_node_t** out_nodes, size_t* out_count) {
  *out_nodes = NULL;
  *out_count = 0;
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
   */
  uint8_t firmware_type;
  uint8_t padding[3];
  //todo - rozsirit na 32 bit - FIH

  /* NOTE: the FIRMWARE Merkle proof is NOT stored here. In the PQ_SECURE_BOOT
   * scheme it lives in the firmware image's manifest region
   * (firmware_manifest_proof_t, right after the manifest), so the firmware
   * carries its own co-path to firmware_root and this (write-protected) header
   * only holds the storage-domain identity (firmware_type). New unauth fields
   * are appended at the END of this struct (per the warning above); the parser
   * locates the code via header_size, so older boardloaders/bins stay
   * compatible (see boot-header budget). */

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
 * Computes the variant leaf and folds `proof` up to the root, requiring it
 * equals `trusted_root`. Does NOT read any module code (the bodies need not be
 * present), so the update preamble can authenticate the manifest -- and trust
 * its `firmware_variant` / directory -- before streaming. `firmware_verify_
 * manifest` is the full check (this + per-module integrity).
 *
 * The variant leaf is `H(0x00 || manifest)`, EXCEPT for the CUSTOM variant
 * (`firmware_variant == FW_VARIANT_CUSTOM`) where the kernel+coreapp
 * (FW_MODULE_APP) entry's `code_hash` is substituted with ZERO before hashing.
 * The founder signs the custom slot with a zeroed app hash, so any creator's
 * app authenticates to the same leaf -- the app is founder-UNauthenticated (it
 * is integrity-checked separately, in firmware_verify_manifest). This zero-for-
 * fold substitution is centralized here (and in the leaf helper) so no path can
 * fold with the wrong app-hash treatment.
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
 *  1. Authenticity: the variant leaf (see firmware_manifest_authentic, incl. the
 *     CUSTOM app-hash zeroing) folds via `proof` to `trusted_root` (the signed
 *     firmware_root).
 *  2. Integrity: for each directory entry, the module code at
 *     `firmware_base + addr` (`size` bytes) must hash to the entry's
 *     `code_hash`. For official variants that `code_hash` is founder-signed
 *     (step 1 authenticates it). For the CUSTOM variant the kernel+coreapp
 *     `code_hash` is the creator's (NOT founder-signed -- zeroed in step 1), so
 *     this is a corruption/integrity check only; the secmon stays founder-bound.
 *
 * Custom-ness is derived from the (now-authenticated) `manifest->firmware_
 * variant`; there is no caller flag -- an official image cannot be verified as
 * custom or vice versa (either mismatches the signed leaf and is rejected).
 *
 * @param manifest Manifest at the start of the firmware image
 * @param manifest_len Manifest length in bytes (firmware_manifest_size)
 * @param firmware_base Base address the manifest `addr` offsets are relative to
 *                      (the firmware region start)
 * @param proof Firmware Merkle proof (variant leaf -> firmware_root)
 * @param proof_count Number of proof nodes
 * @param trusted_root The signed firmware_root to check against
 * @return secbool -- sectrue iff authenticity and integrity all hold
 */
secbool firmware_verify_manifest(const firmware_manifest_t* manifest,
                                 size_t manifest_len, uintptr_t firmware_base,
                                 const merkle_proof_node_t* proof,
                                 size_t proof_count,
                                 const merkle_proof_node_t* trusted_root);

/**
 * Integrity check for ONE manifest directory entry (step 2 of
 * firmware_verify_manifest, for a single module): the module code at
 * `firmware_base + entry->addr` (`entry->size` bytes) must hash to
 * `entry->code_hash`.
 *
 * The manifest carrying `entry` must already be authenticated
 * (firmware_manifest_authentic) so `code_hash` is trusted (for the CUSTOM app,
 * `code_hash` is the creator's -- this is then a corruption check only). Lets a
 * streaming install verify each module the moment its bytes are on flash,
 * instead of waiting for the whole image. The custom app carries its creator's
 * real code_hash in the manifest, so it is verified here like any other module
 * (no skip); only the founder-authenticity treats the custom app hash as zero.
 *
 * @param entry One (authenticated) manifest directory entry
 * @param firmware_base Base address the entry `addr` offset is relative to
 * @return secbool -- sectrue iff the module code matches the entry's code_hash
 */
secbool firmware_verify_manifest_entry(const firmware_manifest_entry_t* entry,
                                       uintptr_t firmware_base);

/**
 * Composes the persisted firmware_type byte from the authenticated `variant`
 * (fw_variant_t). firmware_type IS the variant: custom-ness is the variant value
 * (FW_VARIANT_CUSTOM), not a separate flag.
 *
 * The result is only trustworthy because the bootloader is the sole writer of
 * the write-protected boot header region; it must be *derived* from the
 * authenticated manifest variant, never taken from an untrusted input. Storage
 * entropy / wipe-on-change key off this value.
 */
uint8_t firmware_type_compose(uint32_t variant);

/** Extracts the variant (fw_variant_t) from a firmware_type byte. */
uint32_t firmware_type_variant(uint8_t firmware_type);

/** Returns sectrue if the firmware_type byte marks custom (the custom variant).
 *  FIH note: for granting official privileges use firmware_type_is_official()
 *  (a positive check that fails toward restricted), NOT !is_custom. */
secbool firmware_type_is_custom(uint8_t firmware_type);

/** Returns sectrue ONLY on a positive determination that firmware_type is a
 *  recognized OFFICIAL (founder-authenticated, non-custom) variant. Anything
 *  else -- custom, none, or an unknown value -- returns secfalse, so a glitched
 *  or unexpected byte fails toward restricted (never a silent official grant). */
secbool firmware_type_is_official(uint8_t firmware_type);

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
