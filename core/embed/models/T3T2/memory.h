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
#define BOARDLOADER_MAXSIZE (8 * 8 * 1024)  // 64 kB
#define BOARDLOADER_SECTOR_START 0x2
#define BOARDLOADER_SECTOR_END 0x9

#define BOARDCAPS_START (0x0C013F00)
#define BOARDCAPS_MAXSIZE 0x100

// Update control block
#define BOOTUCB_START (0x0C014000)
#define BOOTUCB_MAXSIZE (1 * 8 * 1024)  // 8 kB
#define BOOTUCB_SECTOR_START 0xA
#define BOOTUCB_SECTOR_END 0xA

// Non-boardloader area (includes bootloader, firmware, assets and storage)
#define NONBOARDLOADER_START (0x0C016000)
#define NONBOARDLOADER_MAXSIZE (245 * 8 * 1024)  // 1960 kB
#define NONBOARDLOADER_SECTOR_START 0xB
#define NONBOARDLOADER_SECTOR_END 0xFF

#define BOOTLOADER_START (0x0C016000)
#define BOOTLOADER_MAXSIZE (24 * 8 * 1024)  // 192 kB
#define BOOTLOADER_SECTOR_START 0xB
#define BOOTLOADER_SECTOR_END 0x22

#define FIRMWARE_START (0x0C046000)
#define FIRMWARE_MAXSIZE (205 * 8 * 1024)  // 1640 kB
#define FIRMWARE_SECTOR_START 0x23
#define FIRMWARE_SECTOR_END 0xEF

// overlaps with assets and storage; sized to hold a full bootloader image
#define BOOTUPDATE_START (0x0C1E0000)
#define BOOTUPDATE_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define BOOTUPDATE_SECTOR_START 0xF0
#define BOOTUPDATE_SECTOR_END 0xFF

#define ASSETS_START (0x0C1E0000)
#define ASSETS_MAXSIZE (8 * 8 * 1024)  // 64 kB
#define ASSETS_SECTOR_START 0xF0
#define ASSETS_SECTOR_END 0xF7

#define STORAGE_1_START (0x0C1F0000)
#define STORAGE_1_MAXSIZE (4 * 8 * 1024)  // 32 kB
#define STORAGE_1_SECTOR_START 0xF8
#define STORAGE_1_SECTOR_END 0xFB

#define STORAGE_2_START (0x0C1F8000)
#define STORAGE_2_MAXSIZE (4 * 8 * 1024)  // 32 kB
#define STORAGE_2_SECTOR_START 0xFC
#define STORAGE_2_SECTOR_END 0xFF

// RAM layout
// BOOTARGS is placed at the very start of SRAM and kept at the same address
// across all boot stages (see memory_secmon.h) so the boot handoff is stable.
#define BOOTARGS_START 0x30000000
#define BOOTARGS_SIZE 0x200

#define FB1_RAM_START 0x30000200
#define FB1_RAM_SIZE (153600)  // 240 * 320 * 2

// Single framebuffer configuration: FB2 is unused (FRAME_BUFFER_COUNT == 1)
#define FB2_RAM_START 0x30025A00
#define FB2_RAM_SIZE (0)

#define MAIN_RAM_START 0x30025A00
#define MAIN_RAM_SIZE (48 * 1024)

#define AUX1_RAM_START 0x30031A00
#define AUX1_RAM_SIZE (172 * 1024 - 512)

#define AUX2_RAM_START 0x3005C800
#define AUX2_RAM_SIZE (398 * 1024)

// misc
#define CODE_ALIGNMENT 0x200
#define COREAPP_ALIGNMENT 0x2000
