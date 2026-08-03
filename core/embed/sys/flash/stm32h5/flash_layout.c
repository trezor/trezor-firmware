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

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_model.h>

#include <sys/flash.h>

#include "../layout_helpers.h"

// Convert sector number to address
//
// This conversion is used in static assert in definitions below
#define FLASH_SECTOR_TO_ADDR(sector, nonsecure) \
  (((nonsecure) ? FLASH_BASE_NS : FLASH_BASE_S) + (sector) * FLASH_PAGE_SIZE)

// Define all flash areas as `const flash_area_t ID = { .. };`

#ifdef USE_SECMON_LAYOUT
#define ACCESS_APP ACCESS_NONSECURE
#else
#define ACCESS_APP ACCESS_DEFAULT
#endif

#ifdef SECURE_MODE
DEFINE_SINGLE_AREA(BOARDLOADER_AREA, BOARDLOADER, ACCESS_DEFAULT);
DEFINE_SINGLE_AREA(BOOTLOADER_AREA, BOOTLOADER, ACCESS_DEFAULT);
DEFINE_SINGLE_AREA(SECRET_AREA, SECRET, ACCESS_DEFAULT);
DEFINE_SINGLE_AREA(BHK_AREA, BHK, ACCESS_DEFAULT);
DEFINE_ARRAY2_AREA(STORAGE_AREAS, STORAGE_1, STORAGE_2, ACCESS_DEFAULT);
DEFINE_EMPTY_AREA(UNUSED_AREA);

#ifdef SECMON
// FIRMWARE_AREA is defined in flash.c driver because it depends on the
// SECMON size which is not known at compile time.
#else
DEFINE_SINGLE_AREA(FIRMWARE_AREA, FIRMWARE, ACCESS_DEFAULT);
#endif

#endif  // SECURE_MODE

#ifdef KERNEL_MODE
DEFINE_SINGLE_AREA(ASSETS_AREA, ASSETS, ACCESS_APP);
#endif

#ifdef USE_BOOT_UCB
// Area dedicated to the UCB (Update Control Block) used during
// boot-loader or boot-header updates.
DEFINE_SINGLE_AREA(BOOTUCB_AREA, BOOTUCB, ACCESS_DEFAULT);
// Area used during bootloader update in prodtest. It holds
// the downloaded bootloader image.
DEFINE_SINGLE_AREA(BOOTUPDATE_AREA, BOOTUPDATE, ACCESS_DEFAULT);
#ifdef BOARDLOADER
// Area used by the boardloader during bootloader update process.
// It includes the entire flash memory except the board-loader,
// the UCB, and the secrets area.
DEFINE_SINGLE_AREA(NONBOARDLOADER_AREA, NONBOARDLOADER, ACCESS_DEFAULT);
#endif
#endif

#endif  // KERNEL_MODE
