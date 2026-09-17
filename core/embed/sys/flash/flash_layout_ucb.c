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

// Staging areas for images the boardloader installs from the UCB. Shared by
// all boot_ucb MCUs: placement follows the model's firmware region, the page
// size comes from the flash build script (needed on emulator builds too).

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

// Tail of the firmware area, so the firmware header is never touched. Sized
// independently of BOOTLOADER_MAXSIZE; each workflow bounds its own upload.
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

// nRF OTA scratch at the front of the firmware area. Must stay clear of
// STAGING_AREA (the upload engine erases to the end of its target area).
// 384 kB fits a debug PQ-native nRF image (~280 kB) with margin.
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
