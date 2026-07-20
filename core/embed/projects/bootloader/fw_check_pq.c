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

#include <sec/boot_header.h>

#include "fw_check.h"
#include "version_check.h"

// Vendor identity string for the tree layout (which has no vendor header). Used
// by every place the bootloader surfaces a vendor name: the boot warning, the
// intro screen, the install confirm and the Features `fw_vendor`. A custom
// (unofficial) image gets a loud UNSAFE marker; an official image is named by
// its variant. FIH: the caller passes is_official, and anything that is not a
// POSITIVE `sectrue` maps to the UNSAFE string -- a glitched/zeroed verdict can
// only ever over-warn, never present unofficial firmware as a trusted vendor.
const char* tree_vendor_str(uint32_t variant, secbool is_official,
                            size_t* out_len) {
  static const char VENDOR_UNSAFE[] = "UNSAFE, DO NOT USE!";
  static const char VENDOR_PRODTEST[] = "UNSAFE, FACTORY TEST ONLY";
  static const char VENDOR_UNIVERSAL[] = "Trezor";
  static const char VENDOR_BITCOIN_ONLY[] = "Trezor Bitcoin-only";
  const char* s;
  if (is_official != sectrue) {
    // Custom/unofficial -- loud warning, never a trusted name.
    s = VENDOR_UNSAFE;
  } else if (variant == FW_VARIANT_PRODTEST) {
    // Founder-signed but factory-only -- must never be used in the field.
    s = VENDOR_PRODTEST;
  } else if (variant == FW_VARIANT_BITCOIN_ONLY) {
    s = VENDOR_BITCOIN_ONLY;
  } else if (variant == FW_VARIANT_UNIVERSAL) {
    s = VENDOR_UNIVERSAL;
  } else {
    // FIH: unknown / NONE variant -> unsafe, never a silent "Trezor".
    s = VENDOR_UNSAFE;
  }
  *out_len = strlen(s);
  return s;
}

secbool firmware_verify_tree(firmware_tree_info_t* info) {
  // The trusted firmware_root comes from our own boot header, which the
  // boardloader has already verified. It commits to the firmware tree.
  const boot_header_auth_t* bl = boot_header_auth_get(BOOTLOADER_START);
  if (bl == NULL) {
    return secfalse;
  }
  merkle_proof_node_t trusted_root;
  memcpy(trusted_root.bytes, bl->firmware_root.bytes,
         sizeof(trusted_root.bytes));

  // Firmware Merkle proof: the co-path folding this device's installed variant
  // leaf up to the signed firmware_root. It lives in our boot header's unauth
  // part, written at install time. A count of 0 (single-variant tree, or a
  // legacy header) means variant leaf == firmware_root -- an identity fold, so
  // this stays backward-compatible. Bounded by BOOT_HEADER_FW_PROOF_MAX_NODES.
  const merkle_proof_node_t* fw_proof = NULL;
  size_t fw_proof_count = 0;
  // Custom (unofficial) firmware: the boot header's firmware_type custom flag
  // (write-protected from firmware, set at install) tells us to expect the
  // kernel+coreapp to deviate from the founder manifest. secmon stays bound.
  secbool custom = secfalse;
  const boot_header_unauth_t* unauth = boot_header_unauth_get(bl);
  if (unauth != NULL) {
    if (unauth->firmware_proof_count > BOOT_HEADER_FW_PROOF_MAX_NODES) {
      return secfalse;
    }
    fw_proof_count = unauth->firmware_proof_count;
    fw_proof = fw_proof_count > 0 ? unauth->firmware_proof_nodes : NULL;
    custom = firmware_type_is_custom(unauth->firmware_type);
  }

  // The manifest ("firmware directory") is at the firmware region start. It is
  // the variant leaf (H(0x00 || manifest)); firmware_verify_manifest folds it
  // up to firmware_root, then verifies each module's code against its code_hash.
  // The module set/roles/layout come from the (authenticated) manifest, so this
  // does not hardcode a module table.
  const firmware_manifest_t* manifest =
      (const firmware_manifest_t*)(uintptr_t)FIRMWARE_START;
  if (manifest->magic != FW_MANIFEST_MAGIC) {
    return secfalse;
  }
  size_t manifest_len = firmware_manifest_size(manifest);
  if (manifest_len > FW_MANIFEST_REGION) {
    return secfalse;
  }

  if (sectrue !=
      firmware_verify_manifest(manifest, manifest_len, FIRMWARE_START, fw_proof,
                               fw_proof_count, &trusted_root, custom)) {
    return secfalse;
  }
  // Official ONLY on a positive custom == secfalse (the manifest verified in
  // strict mode). A glitched `custom` cannot fabricate an official verdict.
  info->is_official = (custom == secfalse) ? sectrue : secfalse;

  // Variant, version and entry point from the (now-verified) manifest. Both the
  // variant and the firmware version are authenticated manifest fields (part of
  // the variant leaf); the entry point is the secmon module's code. The version
  // is read from the manifest's authenticated firmware_version field -- so it
  // is a single authenticated source shared with the phase-1 install confirm
  // (they can only diverge for a spliced custom image, which is UNSAFE anyway).
  info->variant = manifest->firmware_variant;
  info->version = (uint32_t)manifest->firmware_version[0] |
                  ((uint32_t)manifest->firmware_version[1] << 8) |
                  ((uint32_t)manifest->firmware_version[2] << 16) |
                  ((uint32_t)manifest->firmware_version[3] << 24);
  // The secure entry point is the module the (authenticated) manifest flags
  // with FW_MANIFEST_ENTRY_FLAG_BOOT -- the secmon for firmware variants, the
  // prodtest module for prodtest. Selecting it by an explicit flag (not by
  // module type or array position) keeps entry selection decoupled from the
  // type enum. Exactly one entry must be flagged; anything else is a malformed
  // manifest -> reject.
  info->entry_address = 0;
  size_t boot_entries = 0;
  for (size_t i = 0; i < manifest->module_count; i++) {
    const firmware_manifest_entry_t* e = &manifest->entries[i];
    if ((e->flags & FW_MANIFEST_ENTRY_FLAG_BOOT) != 0) {
      // entry->addr points directly at the module code (no per-module header).
      info->entry_address = FIRMWARE_START + e->addr;
      boot_entries++;
    }
  }
  if (boot_entries != 1) {
    return secfalse;
  }
  return sectrue;
}

void fw_check(fw_info_t* info) {
  memset(info, 0, sizeof(*info));

  // header_present == the device is provisioned. Decided from the boot header's
  // firmware_type (the provisioning marker), NOT the firmware image: a fresh /
  // bare bootloader carries firmware_type 0 (FW_VARIANT_NONE) and reads as
  // unprovisioned -> empty-device (wipe-on-setup). Once OTA installs a firmware
  // it stamps the real variant into firmware_type, so a subsequently absent or
  // mid-update (e.g. power loss) firmware still reads as provisioned ->
  // bootloader menu / reinstall, keeping storage. firmware_type lives in the
  // write-protected boot header unauth region (only the bootloader writes it)
  // and is carried across a bootloader update by the UCB hash.
  const boot_header_auth_t* bh = boot_header_auth_get(BOOTLOADER_START);
  const boot_header_unauth_t* unauth =
      (bh != NULL) ? boot_header_unauth_get(bh) : NULL;
  info->header_present =
      (bh != NULL && unauth != NULL && unauth->firmware_type != 0) ? sectrue
                                                                   : secfalse;

  // A provisioned device has a vendor identity for the UI / Features even when
  // its firmware is absent or invalid. Derive it from the (write-protected,
  // trusted) firmware_type byte: its variant names an official image, its
  // custom flag flips the vendor to the UNSAFE marker.
  if (info->header_present == sectrue) {
    uint32_t variant = firmware_type_variant(unauth->firmware_type);
    secbool is_official =
        (firmware_type_is_custom(unauth->firmware_type) == secfalse) ? sectrue
                                                                     : secfalse;
    info->ui.vendor_str =
        tree_vendor_str(variant, is_official, &info->ui.vendor_str_len);
  }

  // Full verification (role-binding + authenticity + per-module code integrity)
  // -> bootable. Only a verified firmware contributes its (trusted) version.
  firmware_tree_info_t tree = {0};
  if (sectrue == firmware_verify_tree(&tree)) {
    info->firmware_present = sectrue;
    info->firmware_present_backup = sectrue;
    info->ui.version = tree.version;
  }
}

void firmware_prepare_boot(firmware_boot_info_t* info) {
  memset(info, 0, sizeof(*info));

  // Verify the module tree (secmon + kernel+coreapp) against the firmware_root
  // signed into our own boot header.
  firmware_tree_info_t fw_tree = {0};
  ensure(firmware_verify_tree(&fw_tree), "Firmware is corrupted");

  // Single downgrade counter (bootloader monotonic) vs the signed boot header.
  const boot_header_auth_t* bl = boot_header_auth_get(BOOTLOADER_START);
  ensure((bl != NULL) * sectrue, "Invalid boot header");
  ensure(check_bootloader_min_version(bl->monotonic_version),
         "Firmware downgrade protection");

  // Official iff the kernel+coreapp matched the founder manifest. A custom
  // (unofficial) firmware -- installed only on an unlocked bootloader -- runs
  // unprivileged with a boot warning. (The custom flag is authenticated via the
  // write-protected boot header firmware_type; see firmware_verify_tree.)
  // fw_tree.is_official already carries the safe default (secfalse unless the
  // manifest verified strictly); the `== sectrue` gates below reject any
  // glitch.
  const secbool is_official = fw_tree.is_official;

  // FIH: assume UNOFFICIAL and boot in the fully-restricted, fully-warned
  // state. No secret/provisioning access, runtime-limited, and the
  // untrusted-image warning (red styling, a visible countdown, a required
  // click) -- the legacy path derives the warning fields from the vendor
  // header's vtrust flags; the tree layout has no vendor header, so set them
  // explicitly. Only a POSITIVE determination that the kernel+coreapp matched
  // the founder manifest clears any of this, so a skipped or glitched check
  // leaves the safe path -- never a silent official boot, and never a warning
  // drawn-and-dismissed in one frame.
  info->secret_run_access = secfalse;
  info->provisioning_access = secfalse;
  info->allow_unlimited_run = secfalse;
  info->show_warning = sectrue;
  info->ui.red_screen = true;
  info->warn_delay = 3;
  info->warn_click = sectrue;

  info->ui.version = fw_tree.version;
  info->ui.vendor_str =
      tree_vendor_str(fw_tree.variant, is_official, &info->ui.vendor_str_len);

  // Positively official -> grant privileges and clear the warning.
  if (is_official == sectrue) {
    info->secret_run_access = sectrue;
    // Ternary (not `* sectrue`): a glitched comparison can make multiplication
    // yield GARBAGE (neither sectrue nor secfalse); the ternary always emits a
    // clean secbool, so this privilege gate can't leak a value a `!= secfalse`
    // consumer would read as granted.
    info->provisioning_access =
        (fw_tree.variant == FW_VARIANT_PRODTEST) ? sectrue : secfalse;
    info->allow_unlimited_run = sectrue;
    info->show_warning = secfalse;
    info->ui.red_screen = false;
    info->warn_delay = 0;
    info->warn_click = secfalse;
  }

  info->entry_address = (uint32_t)fw_tree.entry_address;
}
