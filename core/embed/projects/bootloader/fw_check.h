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
 * @brief Firmware information collected by the bootloader when validating
 * images present in flash.
 *
 * This structure is filled by `fw_check()` and then used by the bootloader to
 * decide whether it can safely boot the firmware image.
 */
typedef struct {
  vendor_header vhdr; /**< Parsed vendor header copied from flash.
                           Contains vendor/product identifiers,
                           versioning and policy flags (e.g.,
                           lock, minimum versions). */

  const image_header *hdr; /**< Pointer to the validated image header of
                                the selected firmware (primary or
                                backup). NULL if no valid header was
                                found. */

  volatile secbool header_present; /**< True if a header structure was
                               found and passed basic checks. */

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
