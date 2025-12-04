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

#define FIRMWARE_START (0x0805E000)
#define FIRMWARE_START_S (0x0C05E000)
#define FIRMWARE_MAXSIZE (353 * 8 * 1024)  // 2824 kB
#define FIRMWARE_SECTOR_START 0x2F
#define FIRMWARE_SECTOR_END 0x18F

#define APPCODE_START (0x08320000)
#define APPCODE_MAXSIZE (64 * 8 * 1024)  // 512 kB
#define APPCODE_SECTOR_START 0x190
#define APPCODE_SECTOR_END 0x1CF

#define ASSETS_START (0x083A0000)
#define ASSETS_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define ASSETS_SECTOR_START 0x1D0
#define ASSETS_SECTOR_END 0x1DF

// overlaps with assets and storage
#define BOOTUPDATE_START (0x0C3A0000)
#define BOOTUPDATE_MAXSIZE (48 * 8 * 1024)  // 384 kB
#define BOOTUPDATE_SECTOR_START 0x1D0
#define BOOTUPDATE_SECTOR_END 0x1FF

#define STORAGE_1_START (0x0C3C0000)
#define STORAGE_1_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define STORAGE_1_SECTOR_START 0x1E0
#define STORAGE_1_SECTOR_END 0x1EF

#define STORAGE_2_START (0x0C3E0000)
#define STORAGE_2_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define STORAGE_2_SECTOR_START 0x1F0
#define STORAGE_2_SECTOR_END 0x1FF

// RAM layout
#define BOOTARGS_START (0x30000000)
#define BOOTARGS_SIZE 0x200

#define NONSECURE_RAM1_START (0x20000200)
#define NONSECURE_RAM1_SIZE (768 * 1024 - 512)

#define NONSECURE_RAM2_START (0x200D0000)
#define NONSECURE_RAM2_SIZE ((768 + 832 + 64) * 1024)

#define FB1_RAM_START (0x20000200)
#define FB1_RAM_SIZE (768 * 1024 - 512)

#define SECMON_RAM_START (0x300C0000)
#define SECMON_RAM_SIZE (64 * 1024)

#define FB2_RAM_START (0x200D0000)
#define FB2_RAM_SIZE (768 * 1024)

#define AUX1_RAM_START (0x20190000)
#define AUX1_RAM_SIZE (576 * 1024)

#define APPDATA_RAM_START (0x20220000)
#define APPDATA_RAM_SIZE (256 * 1024)

#define MAIN_RAM_START (0x20260000)
#define MAIN_RAM_SIZE (64 * 1024)

// misc
#define CODE_ALIGNMENT 0x400
#define COREAPP_ALIGNMENT 0x2000
