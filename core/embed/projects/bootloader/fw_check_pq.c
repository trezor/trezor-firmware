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

#include <trezor_model.h>
#include <trezor_rtl.h>

// Must stay at top level: it #undefs the model's flash address constants.
#ifdef TREZOR_EMULATOR
#include "emulator.h"
#endif

#include <sec/boot_header.h>

#include "fw_check.h"
#include "version_check.h"

// Boot-warning logo for unofficial firmware, embedded by build.rs from this
// model's vendorheader/vendor_unsafe.toif.
extern const void rodata_vendor_unsafe_start;
extern const void rodata_vendor_unsafe_end;

// Vendor string for the tree layout (no vendor header). FIH: anything but a
// positive is_official maps to the UNSAFE string.
const char* tree_vendor_str(fw_variant_sec_t variant, secbool is_official,
                            size_t* out_len) {
  static const char VENDOR_UNSAFE[] = "UNSAFE, DO NOT USE!";
  static const char VENDOR_PRODTEST[] = "UNSAFE, FACTORY TEST ONLY";
  static const char VENDOR_UNIVERSAL[] = "Trezor";
  static const char VENDOR_BITCOIN_ONLY[] = "Trezor Bitcoin-only";
  const char* s;
  if (is_official != sectrue) {
    s = VENDOR_UNSAFE;
  } else if (variant == FW_VARIANT_SEC_PRODTEST) {
    s = VENDOR_PRODTEST;
  } else if (variant == FW_VARIANT_SEC_BITCOIN_ONLY) {
    s = VENDOR_BITCOIN_ONLY;
  } else if (variant == FW_VARIANT_SEC_UNIVERSAL) {
    s = VENDOR_UNIVERSAL;
  } else {
    // FIH: unknown / NONE variant -> unsafe.
    s = VENDOR_UNSAFE;
  }
  *out_len = strlen(s);
  return s;
}

secbool firmware_verify_tree(firmware_tree_info_t* info) {
  // firmware_root comes from our own boardloader-verified boot header.
  const boot_header_auth_t* bl = boot_header_auth_get(BOOTLOADER_START);
  if (bl == NULL) {
    return secfalse;
  }
  merkle_proof_node_t trusted_root;
  memcpy(trusted_root.bytes, bl->firmware_root.bytes,
         sizeof(trusted_root.bytes));

  // The manifest at the firmware region start is the variant leaf.
  const firmware_manifest_t* manifest =
      (const firmware_manifest_t*)(uintptr_t)FIRMWARE_START;
  if (manifest->magic != FW_MANIFEST_MAGIC) {
    return secfalse;
  }
  size_t manifest_len = firmware_manifest_size(manifest);
  if (manifest_len > FW_MANIFEST_REGION) {
    return secfalse;
  }

  // Per-variant proof embedded right after the manifest; 0 nodes is an
  // identity fold.
  const merkle_proof_node_t* fw_proof = NULL;
  size_t fw_proof_count = 0;
  if (sectrue != firmware_manifest_read_proof(manifest, FW_MANIFEST_REGION,
                                              &fw_proof, &fw_proof_count)) {
    return secfalse;
  }

  // Bound the module regions before hashing: the CUSTOM variant's app size is
  // not founder-authenticated. Same check as install phases 1 + 2.
  if (sectrue != firmware_manifest_layout_valid(manifest, FIRMWARE_MAXSIZE)) {
    return secfalse;
  }

  if (sectrue != firmware_verify_manifest(manifest, manifest_len,
                                          FIRMWARE_START, fw_proof,
                                          fw_proof_count, &trusted_root)) {
    return secfalse;
  }

  // Variant pin: the running variant must equal the write-protected boot
  // header firmware_type (the storage-domain identity), or a genuine image of
  // another variant could boot against this domain's seed. FIH: fail closed on
  // an unprovisioned (NONE / INVALID) or mismatched device.
  const boot_header_unauth_t* unauth = boot_header_unauth_get(bl);
  if (unauth == NULL ||
      fw_variant_is_provisioned(unauth->firmware_type) != sectrue ||
      manifest->firmware_variant != unauth->firmware_type) {
    return secfalse;
  }

  // Variant and version are authenticated manifest fields (the CUSTOM fold
  // zeroes only the app code_hash). FIH: official only on a positive check.
  info->variant = manifest->firmware_variant;
  info->is_official = fw_variant_is_official(info->variant);
  info->version = (uint32_t)manifest->firmware_version[0] |
                  ((uint32_t)manifest->firmware_version[1] << 8) |
                  ((uint32_t)manifest->firmware_version[2] << 16) |
                  ((uint32_t)manifest->firmware_version[3] << 24);
  // Exactly one entry must carry FW_MANIFEST_ENTRY_FLAG_BOOT.
  info->entry_address = 0;
  size_t boot_entries = 0;
  for (size_t i = 0; i < manifest->module_count; i++) {
    const firmware_manifest_entry_t* e = &manifest->entries[i];
    if ((e->flags & FW_MANIFEST_ENTRY_FLAG_BOOT) != 0) {
      info->entry_address = FIRMWARE_START + e->addr;
      boot_entries++;
    }
  }
  if (boot_entries != 1) {
    return secfalse;
  }
  return sectrue;
}

void fw_check(fw_check_info_t* info) {
  memset(info, 0, sizeof(*info));

  // header_present == provisioned, decided solely by the boot header's
  // firmware_type (NONE and INVALID both read as unprovisioned), never by
  // whether a firmware image is present.
  const boot_header_auth_t* bh = boot_header_auth_get(BOOTLOADER_START);
  const boot_header_unauth_t* unauth =
      (bh != NULL) ? boot_header_unauth_get(bh) : NULL;
  info->header_present =
      (bh != NULL && unauth != NULL &&
       fw_variant_is_provisioned(unauth->firmware_type) == sectrue)
          ? sectrue
          : secfalse;

  // Vendor identity from the trusted firmware_type, even without a valid
  // firmware.
  if (info->header_present == sectrue) {
    const fw_variant_sec_t variant = unauth->firmware_type;
    secbool is_official = fw_variant_is_official(variant);
    info->ui.vendor_str =
        tree_vendor_str(variant, is_official, &info->ui.vendor_str_len);
  }

  // Only a verified firmware contributes its version.
  firmware_tree_info_t tree = {0};
  if (sectrue == firmware_verify_tree(&tree)) {
    info->firmware_present = sectrue;
    info->firmware_present_backup = sectrue;
    info->ui.version = tree.version;
  }
}

void fw_run_prepare(fw_run_info_t* info) {
  memset(info, 0, sizeof(*info));

  firmware_tree_info_t fw_tree = {0};
  ensure(firmware_verify_tree(&fw_tree), "Firmware is corrupted");

  const boot_header_auth_t* bl = boot_header_auth_get(BOOTLOADER_START);
  ensure((bl != NULL) * sectrue, "Invalid boot header");
  ensure(check_bootloader_min_version(bl->monotonic_version),
         "Firmware downgrade protection");

  const secbool is_official = fw_tree.is_official;

  // FIH: start fully restricted and fully warned (the tree layout has no
  // vtrust flags); only a positive official verdict raises anything.
  info->secret_run_access = secfalse;
  info->provisioning_access = secfalse;
  info->allow_unlimited_run = secfalse;
  info->no_warning = secfalse;
  info->ui.no_red = secfalse;
  info->warn_delay = 3;
  info->no_click = secfalse;

  info->ui.version = fw_tree.version;
  info->ui.vendor_str =
      tree_vendor_str(fw_tree.variant, is_official, &info->ui.vendor_str_len);
  // UNSAFE logo is the default; a glitched verdict can only over-warn.
  info->ui.vendor_img = (const uint8_t*)&rodata_vendor_unsafe_start;
  info->ui.vendor_img_len = (const uint8_t*)&rodata_vendor_unsafe_end -
                            (const uint8_t*)&rodata_vendor_unsafe_start;

  if (is_official == sectrue) {
    info->secret_run_access = sectrue;
    // FIH: ternary, not `* sectrue`, so a glitched compare cannot yield a
    // garbage non-secfalse value.
    info->provisioning_access =
        (fw_tree.variant == FW_VARIANT_SEC_PRODTEST) ? sectrue : secfalse;
    info->allow_unlimited_run = sectrue;
    info->no_warning = sectrue;
    info->ui.no_red = sectrue;
    info->ui.vendor_img = NULL;
    info->ui.vendor_img_len = 0;
    info->warn_delay = 0;
    info->no_click = sectrue;
  }

  info->entry_address = (uint32_t)fw_tree.entry_address;
}
