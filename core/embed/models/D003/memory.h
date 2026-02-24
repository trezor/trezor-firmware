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
// misc
#define FLASH_START 0x0C004000

// FLASH layout
#define SECRET_START 0x0C000000
#define SECRET_MAXSIZE (4 * 4 * 1024)  // 16 kB
#define SECRET_SECTOR_START 0x0
#define SECRET_SECTOR_END 0x3

// overlaps with secret
#define BHK_START 0x0C002000
#define BHK_MAXSIZE (2 * 4 * 1024)  // 8 kB
#define BHK_SECTOR_START 0x2
#define BHK_SECTOR_END 0x3

// overlaps with hdp close and boardloader code
#define BOARDLOADER_START 0x0C004000
#define BOARDLOADER_MAXSIZE (12 * 4 * 1024)  // 48 kB
#define BOARDLOADER_SECTOR_START 0x4
#define BOARDLOADER_SECTOR_END 0xF

#define HDP_START 0x0C004000
#define HDP_MAXSIZE (1 * 4 * 1024)  // 4 kB
#define HDP_SECTOR_START 0x4
#define HDP_SECTOR_END 0x4

#define BOARDLOADER_CODE_START 0x0C005000
#define BOARDLOADER_CODE_MAXSIZE (11 * 4 * 1024)  // 44 kB
#define BOARDLOADER_CODE_SECTOR_START 0x5
#define BOARDLOADER_CDE_SECTOR_END 0xF

#define BOARDCAPS_START 0x0C00FF00
#define BOARDCAPS_MAXSIZE 0x100

// Update control block
#define BOOTUCB_START (0x0C010000)
#define BOOTUCB_MAXSIZE (2 * 4 * 1024)  // 8 kB
#define BOOTUCB_SECTOR_START 0x10
#define BOOTUCB_SECTOR_END 0x11

// Non-boardloader area (includes bootloader, firmware, assets and storage)
#define NONBOARDLOADER_START (0x0C012000)
// #define NONBOARDLOADER_MAXSIZE (494 * 4 * 1024)  // 1984 kB
#define NONBOARDLOADER_MAXSIZE (238 * 4 * 1024)  // 952 kB
#define NONBOARDLOADER_SECTOR_START 0x12
#define NONBOARDLOADER_SECTOR_END 0xFF

#define BOOTLOADER_START 0x0C012000
#define BOOTLOADER_MAXSIZE (32 * 4 * 1024)  // 128 kB
#define BOOTLOADER_SECTOR_START 0x12
#define BOOTLOADER_SECTOR_END 0x31

// overlaps with assets and storage
#define BOOTUPDATE_START (0x0C032000)
#define BOOTUPDATE_MAXSIZE (48 * 4 * 1024)  // 192 kB
#define BOOTUPDATE_SECTOR_START 0x32
#define BOOTUPDATE_SECTOR_END 0x61

#define ASSETS_START 0x0C032000
#define ASSETS_MAXSIZE (16 * 4 * 1024)  // 64 kB
#define ASSETS_SECTOR_START 0x32
#define ASSETS_SECTOR_END 0x41

#define STORAGE_1_START 0x0C042000
#define STORAGE_1_MAXSIZE (16 * 4 * 1024)  // 64 kB
#define STORAGE_1_SECTOR_START 0x42
#define STORAGE_1_SECTOR_END 0x51

#define STORAGE_2_START 0x0C052000
#define STORAGE_2_MAXSIZE (16 * 4 * 1024)  // 64 kB
#define STORAGE_2_SECTOR_START 0x52
#define STORAGE_2_SECTOR_END 0x61

#define FIRMWARE_START 0x0C062000
// #define FIRMWARE_MAXSIZE (414 * 4 * 1024)  // 1656 kB
#define FIRMWARE_MAXSIZE (158 * 4 * 1024)  // 632 kB
#define FIRMWARE_SECTOR_START 0x62
#define FIRMWARE_SECTOR_END 0xFF

// RAM layout
#define AUX1_RAM_START 0x30000000
#define AUX1_RAM_SIZE (192 * 1024 - 512)

// 256 bytes skipped - trustzone alignment vs fixed bootargs position

#define BOOTARGS_START 0x3002FF00
#define BOOTARGS_SIZE 0x100

#define MAIN_RAM_START 0x30030000
#define MAIN_RAM_SIZE (64 * 1024)

// misc
#define CODE_ALIGNMENT 0x200
#define COREAPP_ALIGNMENT 0x2000
