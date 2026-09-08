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

// Flash areas used for STAGING an image the boardloader will install.
//
// These are not per-MCU. Where they sit is decided entirely by the model's
// firmware region (FIRMWARE_SECTOR_START/END) and by the update scheme, so the
// rule lives here once instead of being copied into each MCU's flash_layout.c
// -- the boot_ucb scheme already spans two MCU families.
//
// The one thing that does come from the MCU is the page size, supplied as
// FLASH_LAYOUT_PAGE_SIZE by the flash build script. The areas below need it at
// compile time (they are `const` and statically asserted), and the HAL's
// FLASH_PAGE_SIZE is not usable for that: trezor_bsp.h pulls the HAL in only
// for device builds, while these areas are needed on the emulator too, because
// a bootloader emulator stages a UCB exactly like the device does. Where the
// HAL IS present the two are cross-checked below.
//
// This file is compiled only for boot_ucb models, all of which have a uniform
// page size. An MCU with mixed sector sizes (STM32F4) could not express these
// areas as a page count at all -- but no such model uses the scheme.

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_model.h>

#include <sys/flash.h>

#ifndef FLASH_LAYOUT_PAGE_SIZE
#error "FLASH_LAYOUT_PAGE_SIZE must be set by the flash build script"
#endif

#ifdef FLASH_PAGE_SIZE
_Static_assert(FLASH_PAGE_SIZE == FLASH_LAYOUT_PAGE_SIZE,
               "FLASH_LAYOUT_PAGE_SIZE disagrees with the HAL page size");
#endif

#ifdef USE_BOOT_UCB

// Staging area for images installed by the boardloader (currently bootloader
// updates, possibly larger image types in the future). It is reserved at the
// tail of the firmware area, so the firmware header (at the start of the
// firmware area) is never touched; the firmware body may be overwritten while
// staging. Lies in the (non-secure) kernel region, well past the secmon.
//
// The reservation is sized independently of, and larger than,
// BOOTLOADER_MAXSIZE so bigger images can be staged later. Individual workflows
// still bound their own uploads: the bootloader update is limited to
// BOOTLOADER_MAXSIZE. Reserving more does not reduce FIRMWARE_MAXSIZE (the
// descriptor overlaps the firmware tail); it only widens the region clobbered
// during an actual staging op.
#ifndef STAGING_MAXSIZE
#define STAGING_MAXSIZE (64 * 8 * 1024)  // 512 kB
#endif
#define STAGING_SECTOR_COUNT (STAGING_MAXSIZE / FLASH_LAYOUT_PAGE_SIZE)
_Static_assert(STAGING_MAXSIZE % FLASH_LAYOUT_PAGE_SIZE == 0,
               "STAGING_MAXSIZE must be a multiple of the flash sector size");
_Static_assert(STAGING_SECTOR_COUNT <
                   (FIRMWARE_SECTOR_END - FIRMWARE_SECTOR_START + 1),
               "Staging area would reach the firmware header");
const flash_area_t STAGING_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = FIRMWARE_SECTOR_END - STAGING_SECTOR_COUNT + 1,
            .num_sectors = STAGING_SECTOR_COUNT,
        },
};

// nRF OTA staging scratch, at the FRONT of the firmware
// region (compile-time const -- unlike FIRMWARE_AREA there is no secmon split
// at this layer). Capped to NRF_STAGING_MAXSIZE so it sits far below
// STAGING_AREA (the firmware tail): the upload engine erases to the END of its
// target area, and STAGING_AREA overlaps that tail, so a full-FIRMWARE_AREA
// scratch would erase the pending bootloader. The static_assert proves
// NRF_STAGING_AREA and STAGING_AREA cannot overlap. The region holds old
// firmware (secmon+kernel) that the coupled update reinstalls in phase 2, so
// clobbering it is expected. Sized for the largest nRF image we actually stage,
// with margin:
//   ~174 kB  classic release image (Ed25519 only)
//   ~191 kB  + founder material (2x SLH-DSA 7856 B + 2x Ed25519 + co-path)
//   ~280 kB  DEBUG build of the same (RTT console + logging) + founder material
// A debug PQ-native image at 279 kB overflowed the previous 256 kB cap (which
// left only 248 kB usable, one sector going to the staging descriptor) and
// phase 1 rejected it as "nRF image size invalid". 384 kB keeps headroom for
// debug builds. There is room: the static_assert below allows ~345 sectors
// before the bootloader staging tail. The extra cost is only that a few more
// sectors of the old firmware get erased -- which phase 2 reinstalls anyway.
#ifndef NRF_STAGING_MAXSIZE
#define NRF_STAGING_MAXSIZE (48 * 8 * 1024)  // 384 kB
#endif
#define NRF_STAGING_SECTOR_COUNT (NRF_STAGING_MAXSIZE / FLASH_LAYOUT_PAGE_SIZE)
_Static_assert(
    NRF_STAGING_MAXSIZE % FLASH_LAYOUT_PAGE_SIZE == 0,
    "NRF_STAGING_MAXSIZE must be a multiple of the flash sector size");
_Static_assert(FIRMWARE_SECTOR_START + NRF_STAGING_SECTOR_COUNT <=
                   FIRMWARE_SECTOR_END - STAGING_SECTOR_COUNT + 1,
               "nRF staging scratch would overlap the bootloader staging tail");
const flash_area_t NRF_STAGING_AREA = {
    .num_subareas = 1,
    .subarea[0] =
        {
            .first_sector = FIRMWARE_SECTOR_START,
            .num_sectors = NRF_STAGING_SECTOR_COUNT,
        },
};

#endif  // USE_BOOT_UCB

#endif  // KERNEL_MODE
