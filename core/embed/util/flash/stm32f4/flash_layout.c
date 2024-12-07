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

#include <trezor_bsp.h>
#include <trezor_model.h>

#include <util/flash.h>

#include "../layout_helpers.h"

// Convert sector number to address
//
// This conversion is used in static assert in definitions below
#define FLASH_SECTOR_TO_ADDR(sector)         \
  (FLASH_BASE + ((sector) / 12) * 0x100000 + \
   (((sector) % 12) < 4                      \
        ? ((sector) % 12) * 0x4000           \
        : (((sector) % 12) < 5 ? 0x10000 : ((sector) % 12 - 4) * 0x20000)))

// Define all flash areas as `const flash_area_t ID = { .. };`

DEFINE_ARRAY2_AREA(STORAGE_AREAS, STORAGE_1, STORAGE_2);
DEFINE_SINGLE_AREA(BOARDLOADER_AREA, BOARDLOADER);
DEFINE_SINGLE_AREA(BOOTLOADER_AREA, BOOTLOADER);
DEFINE_SPLIT2_AREA(FIRMWARE_AREA, FIRMWARE_P1, FIRMWARE_P2);

#ifdef SECRET_SECTOR_START
DEFINE_SINGLE_AREA(SECRET_AREA, SECRET);
#else
DEFINE_EMPTY_AREA(SECRET_AREA);
#endif

DEFINE_SINGLE_AREA(ASSETS_AREA, ASSETS);
DEFINE_SPLIT2_AREA(UNUSED_AREA, UNUSED_1, UNUSED_2);
