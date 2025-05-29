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
#define SECRET_MAXSIZE (2 * 8 * 1024)  // 8 kB
#define SECRET_SECTOR_START 0x0
#define SECRET_SECTOR_END 0x1

// overlaps with secret
#define BHK_START 0x0C002000
#define BHK_MAXSIZE (1 * 8 * 1024)  // 8 kB
#define BHK_SECTOR_START 0x1
#define BHK_SECTOR_END 0x1

#define BOARDLOADER_START 0x0C004000
#define BOARDLOADER_MAXSIZE (6 * 8 * 1024)  // 48 kB
#define BOARDLOADER_SECTOR_START 0x2
#define BOARDLOADER_SECTOR_END 0x7

#define BOARDCAPS_START 0x0C00FF00
#define BOARDCAPS_MAXSIZE 0x100

#define BOOTLOADER_START 0x0C010000
#define BOOTLOADER_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define BOOTLOADER_SECTOR_START 0x8
#define BOOTLOADER_SECTOR_END 0x17

#define STORAGE_1_START 0x0C030000
#define STORAGE_1_MAXSIZE (8 * 8 * 1024)  // 64 kB
#define STORAGE_1_SECTOR_START 0x18
#define STORAGE_1_SECTOR_END 0x1F

#define STORAGE_2_START 0x0C040000
#define STORAGE_2_MAXSIZE (8 * 8 * 1024)  // 64 kB
#define STORAGE_2_SECTOR_START 0x20
#define STORAGE_2_SECTOR_END 0x27

#define FIRMWARE_START 0x0C050000
#define FIRMWARE_MAXSIZE (208 * 8 * 1024)  // 1664 kB
#define FIRMWARE_SECTOR_START 0x28
#define FIRMWARE_SECTOR_END 0xF7

#define ASSETS_START 0x0C1F0000
#define ASSETS_MAXSIZE (8 * 8 * 1024)  // 64 kB
#define ASSETS_SECTOR_START 0xF8
#define ASSETS_SECTOR_END 0xFF

// RAM layout
#define AUX1_RAM_START 0x30000000
#define AUX1_RAM_SIZE (192 * 1024 - 512)

// 256 bytes skipped - trustzone alignment vs fixed bootargs position

#define BOOTARGS_START 0x3002FF00
#define BOOTARGS_SIZE 0x100

#define MAIN_RAM_START 0x30030000
#define MAIN_RAM_SIZE (24 * 1024 - 512)

#define SAES_RAM_START 0x30035E00
#define SAES_RAM_SIZE 512

#define AUX2_RAM_START 0x30036000
#define AUX2_RAM_SIZE (327 * 1024)

#define FB1_RAM_START 0x30087C00
#define FB1_RAM_SIZE (115200)

#define FB2_RAM_START 0x300A3E00
#define FB2_RAM_SIZE (115200)

// misc
#define CODE_ALIGNMENT 0x200
#define COREAPP_ALIGNMENT 0x2000
