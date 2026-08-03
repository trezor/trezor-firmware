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

// SHARED WITH MAKEFILE, LINKER SCRIPT etc.
//
// PRELIMINARY H5F5 memory map (D004 / STM32H5F5J-DK bring-up).
// The FLASH layout is cloned from the 4 MB / 8 KB-sector D002 (U5G9J-DK): the
// STM32H5 uses the same secure-alias base (0x0C000000) and 8 KB sectors, so it
// is expected to carry over, but must still be confirmed against RM0517
// (dual-bank boundary at 2 MB, EDATA high-cycle area).
// The RAM layout below is still the U5G9 map and MUST be replaced with the
// H5F5 SRAM bank map (total 1.5 MB) from RM0517 / DS before this model links.

// misc
#define FLASH_START (0x0C004000)

// FLASH layout
#define SECRET_START (0x0C000000)
#define SECRET_MAXSIZE (2 * 8 * 1024)  // 16 kB
#define SECRET_SECTOR_START 0x0
#define SECRET_SECTOR_END 0x1

// overlaps with secret
#define BHK_START (0x0C002000)
#define BHK_MAXSIZE (1 * 8 * 1024)  // 8 kB
#define BHK_SECTOR_START 0x1
#define BHK_SECTOR_END 0x1

#define BOARDLOADER_START (0x0C004000)
#define BOARDLOADER_MAXSIZE (12 * 8 * 1024)  // 96 kB
#define BOARDLOADER_SECTOR_START 0x2
#define BOARDLOADER_SECTOR_END 0xD

#define BOARDCAPS_START (0x0C01BF00)
#define BOARDCAPS_MAXSIZE 0x100

// Update control block
#define BOOTUCB_START (0x0C01C000)
#define BOOTUCB_MAXSIZE (1 * 8 * 1024)  // 8 kB
#define BOOTUCB_SECTOR_START 0xE
#define BOOTUCB_SECTOR_END 0xE

// Non-boardloader area (includes bootloader, firmware, assets and storage)
#define NONBOARDLOADER_START (0x0C01E000)
#define NONBOARDLOADER_MAXSIZE (497 * 8 * 1024)  // 3976 kB
#define NONBOARDLOADER_SECTOR_START 0xF
#define NONBOARDLOADER_SECTOR_END 0x1FF

#define BOOTLOADER_START (0x0C01E000)
#define BOOTLOADER_MAXSIZE (32 * 8 * 1024)  // 256 kB
#define BOOTLOADER_SECTOR_START 0xF
#define BOOTLOADER_SECTOR_END 0x2E

#define FIRMWARE_START (0x0C05E000)
#define FIRMWARE_MAXSIZE (417 * 8 * 1024)  // 3336 kB
#define FIRMWARE_SECTOR_START 0x2F
#define FIRMWARE_SECTOR_END 0x1CF

// overlaps with assets and storage
#define BOOTUPDATE_START (0x0C3A0000)
#define BOOTUPDATE_MAXSIZE (48 * 8 * 1024)  // 384 kB
#define BOOTUPDATE_SECTOR_START 0x1D0
#define BOOTUPDATE_SECTOR_END 0x1FF

#define ASSETS_START (0x0C3A0000)
#define ASSETS_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define ASSETS_SECTOR_START 0x1D0
#define ASSETS_SECTOR_END 0x1DF

#define STORAGE_1_START (0x0C3C0000)
#define STORAGE_1_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define STORAGE_1_SECTOR_START 0x1E0
#define STORAGE_1_SECTOR_END 0x1EF

#define STORAGE_2_START (0x0C3E0000)
#define STORAGE_2_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define STORAGE_2_SECTOR_START 0x1F0
#define STORAGE_2_SECTOR_END 0x1FF

// RAM layout -- STM32H5F5xx: SRAM1..SRAM5 are contiguous, 1.5 MB total, at the
// secure alias 0x30000000..0x30180000. D004 is headless (display_none), so the
// framebuffer regions are small placeholders and the bulk of the SRAM is given
// to AUX1 / MAIN.
#define BOOTARGS_START (0x30000000)
#define BOOTARGS_SIZE 0x200

#define FB1_RAM_START (0x30000200)
#define FB1_RAM_SIZE (16 * 1024 - 512)  // headless placeholder

#define FB2_RAM_START (0x30010000)
#define FB2_RAM_SIZE (16 * 1024)  // headless placeholder

#define MAIN_RAM_START (0x30020000)
#define MAIN_RAM_SIZE (64 * 1024)

#define AUX1_RAM_START (0x30030000)
#define AUX1_RAM_SIZE (1344 * 1024)  // remainder up to 0x30180000 (SRAM end)

// misc
#define CODE_ALIGNMENT 0x400
#define COREAPP_ALIGNMENT 0x2000
