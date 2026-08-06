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

#include <sec/image.h>

/**
 * @brief Layout-agnostic firmware information for display / boot screens.
 *
 * Filled from whatever the installed firmware layout provides: the legacy
 * vendor + image headers, or the Merkle-tree module headers. This lets the UI
 * (boot warning, bootloader intro) work the same way for both, so callers never
 * touch a scheme-specific header.
 */
typedef struct {
  uint32_t version;          /**< firmware version (major|minor<<8|...) */
  const char *vendor_str;    /**< vendor name; NULL to hide it */
  size_t vendor_str_len;     /**< length of vendor_str */
  const uint8_t *vendor_img; /**< vendor logo (TOIF); NULL for none */
  bool red_screen;           /**< warning-screen styling (untrusted vendor) */
} fw_ui_info_t;

/**
 * @brief Firmware information collected by the bootloader when validating
 * images present in flash.
 *
 * This structure is filled by `fw_check()` and then used by the bootloader to
 * decide whether it can safely boot the firmware image.
 */
typedef struct {
  fw_ui_info_t ui; /**< Layout-agnostic display info (version, vendor). */

  volatile secbool
      header_present; /**< True if the device is provisioned, i.e.
                  a firmware is present with valid metadata to show
                  (vendor/version) -- even if its body is corrupt.
                  Drives menu-vs-empty-device routing, the Features
                  reply, and the storage-wipe decision. (legacy: a
                  valid signed firmware header; tree: a valid boot
                  header). TODO: rename to reflect "provisioned". */

  volatile secbool firmware_present; /**< True if a valid, bootable
firmware image is present. */

  volatile secbool firmware_present_backup; /**< True if a valid, bootable
                                        firmware image is present - backup for
                                      glitch protection. */
} fw_info_t;

/**
 * @brief Verify whether the vendor header is the same as the locked version.
 *
 * @param vhdr Pointer to the vendor header to validate.
 * @return sectrue when the vendor header is the same or there is no lock;
 *         secfalse otherwise.
 */
secbool check_vendor_header_lock(const vendor_header *vhdr);

/**
 * @brief Perform comprehensive verification of the firmware image available
 * in flash (both primary and backup).
 *
 * Populates `fw_info` with details about discovered headers and whether the
 * image is valid and bootable.
 *
 * @param fw_info Output structure to be filled by this function; must be
 *                provided by the caller and remain valid for subsequent boot
 *                decisions.
 */
void fw_check(fw_info_t *fw_info);

/**
 * @brief Everything `real_jump_to_firmware()` needs to boot the firmware,
 * resolved by the layout-specific verification/policy code.
 */
typedef struct {
  uint32_t entry_address;      /**< vector table to jump to */
  secbool secret_run_access;   /**< grant the firmware secret access */
  secbool provisioning_access; /**< grant device-provisioning access */
  secbool allow_unlimited_run; /**< if not sectrue, IWDG limits runtime */
  secbool show_warning;        /**< show a boot warning before jumping */
  int warn_delay;              /**< seconds to wait on the warning screen */
  secbool warn_click;          /**< require a click to continue past warning */
  fw_ui_info_t ui;             /**< layout-agnostic info for the warning */
} firmware_boot_info_t;

/**
 * @brief Verify the installed firmware and resolve the boot policy.
 *
 * Performs the full image verification and downgrade check, then fills `info`
 * with the entry point, secret/provisioning access, runtime-limit and warning
 * decisions. Fatal-errors (via `ensure`) on any verification or downgrade
 * failure, so on return the firmware is authentic and bootable.
 *
 * Implemented by exactly one of fw_check.c (legacy vendor/image/secmon headers)
 * or fw_check_pq.c (Merkle-tree layout); the build selects which.
 */
void firmware_prepare_boot(firmware_boot_info_t *info);

#ifdef PQ_SECURE_BOOT
/** Result of a successful firmware-tree verification. */
typedef struct {
  uint32_t variant;        /**< fw_variant_t of the installed firmware */
  uint32_t version;        /**< firmware version (from kernel+coreapp module) */
  uintptr_t entry_address; /**< secmon code entry point (jump target) */
  secbool is_official;     /**< sectrue ONLY if the kernel+coreapp matched the
                                founder manifest. FIH: the field carries the safe
                                default -- a zeroed/glitched struct reads secfalse
                                (unofficial), never a spurious official. */
} firmware_tree_info_t;

/**
 * @brief Merkle-tree firmware verification (tree layout).
 *
 * Enumerates the fixed on-device module set (secmon + kernel+coreapp) at their
 * flash locations, then verifies role-binding, authenticity (recomputed root ==
 * the firmware_root signed into this bootloader's own boot header) and
 * integrity (each module's code vs its chunk hashes). Replaces the legacy
 * vendor/image/ secmon-header verification. On success, fills `info` with the
 * firmware variant and the entry address (secmon code) to jump to.
 *
 * @return secbool -- sectrue iff the installed firmware tree is authentic.
 */
secbool firmware_verify_tree(firmware_tree_info_t *info);

/**
 * @brief Vendor identity string for the tree layout (no vendor header).
 *
 * Returns "UNSAFE, DO NOT USE!" for a custom/unofficial image (is_official not
 * a positive sectrue), "UNSAFE, FACTORY TEST ONLY" for the founder-signed
 * prodtest variant, otherwise the official name for the variant ("Trezor" or
 * "Trezor Bitcoin-only"); an unknown variant also maps to UNSAFE. Shared by the
 * boot warning, intro, install confirm and Features vendor so all surfaces
 * agree. The returned pointer has static storage duration; `*out_len` receives
 * its length.
 */
const char *tree_vendor_str(uint32_t variant, secbool is_official,
                            size_t *out_len);
#endif
