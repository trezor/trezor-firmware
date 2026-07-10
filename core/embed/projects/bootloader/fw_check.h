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
 * @brief Layout-agnostic firmware information for the screens that show it.
 *
 * Filled from whatever the installed firmware layout provides (the vendor +
 * image headers). Keeps the `ui_*` layer (the vendor warning shown before
 * running the firmware, and the bootloader intro) independent of the header
 * format, so it never touches a scheme-specific header.
 */
typedef struct {
  uint32_t version;          /**< firmware version (major|minor<<8|...) */
  const char *vendor_str;    /**< vendor name; NULL to hide it */
  size_t vendor_str_len;     /**< length of vendor_str */
  const uint8_t *vendor_img; /**< vendor logo (TOIF); NULL for none */
  uint32_t vendor_img_len;   /**< length of vendor_img, validated at parse */
  secbool no_red;            /**< sectrue = black background, not the red
                                  warning one (untrusted vendor) */
} fw_ui_info_t;

/**
 * @brief Firmware information collected by the bootloader when validating
 * images present in flash.
 *
 * This structure is filled by `fw_check()` and then used by the bootloader to
 * decide whether it can safely run the installed firmware, or must stay in the
 * bootloader instead.
 */
typedef struct {
  fw_ui_info_t ui; /**< Layout-agnostic display info (version, vendor). */

  volatile secbool header_present; /**< True if the device is provisioned, i.e.
                               a firmware is present with valid metadata to show
                               (vendor/version) -- even if its body is corrupt.
                               Drives menu-vs-empty-device routing, the Features
                               reply, and the storage-wipe decision. (A valid
                               signed firmware header.) */

  volatile secbool firmware_present; /**< True if a valid, bootable
firmware image is present. */

  volatile secbool firmware_present_backup; /**< True if a valid, bootable
                                        firmware image is present - backup for
                                      glitch protection. */
} fw_check_info_t;

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
void fw_check(fw_check_info_t *fw_info);

/**
 * @brief Everything `real_jump_to_firmware()` needs to hand control to the
 * installed firmware, resolved by the layout-specific verification/policy code.
 */
typedef struct {
  uint32_t entry_address;      /**< vector table to jump to */
  secbool secret_run_access;   /**< grant the firmware secret access */
  secbool provisioning_access; /**< grant device-provisioning access */
  secbool allow_unlimited_run; /**< if not sectrue, IWDG limits runtime */
  secbool no_warning;          /**< sectrue = skip the boot warning */
  int warn_delay;              /**< seconds to wait on the warning screen */
  secbool no_click;            /**< sectrue = no click to leave the warning */
  fw_ui_info_t ui;             /**< layout-agnostic info for the warning */
} fw_run_info_t;

/**
 * @brief Verify the installed firmware and resolve the policy for running it.
 *
 * Performs the full image verification and downgrade check, then fills `info`
 * with the entry point, secret/provisioning access, runtime-limit and warning
 * decisions. Fatal-errors (via `ensure`) on any verification or downgrade
 * failure, so on return the firmware is authentic and bootable.
 *
 * Implemented by the layout-specific verification code (fw_check.c).
 */
void fw_run_prepare(fw_run_info_t *info);
