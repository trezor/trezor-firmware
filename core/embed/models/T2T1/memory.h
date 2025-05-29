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

// SHARED WITH MAKEFILE
// common

#define FLASH_START 0x08000000
#define NORCOW_SECTOR_SIZE (1 * 64 * 1024)  // 64 kB

// FLASH layout
#define BOARDLOADER_START 0x08000000
#define BOARDLOADER_MAXSIZE (3 * 16 * 1024)  // 48 kB
#define BOARDLOADER_SECTOR_START 0
#define BOARDLOADER_SECTOR_END 2

#define BOARDCAPS_START 0x0800BF00
#define BOARDCAPS_MAXSIZE 0x100

#define UNUSED_1_START 0x0800C000
#define UNUSED_1_MAXSIZE (1 * 16 * 1024)  // 16 kB
#define UNUSED_1_SECTOR_START 3
#define UNUSED_1_SECTOR_END 3

#define STORAGE_1_START 0x08010000
#define STORAGE_1_MAXSIZE (1 * 64 * 1024)  // 64 kB
#define STORAGE_1_SECTOR_START 4
#define STORAGE_1_SECTOR_END 4

#define BOOTLOADER_START 0x08020000
#define BOOTLOADER_MAXSIZE (1 * 128 * 1024)  // 128 kB
#define BOOTLOADER_SECTOR_START 5
#define BOOTLOADER_SECTOR_END 5

#define FIRMWARE_START 0x08040000
#define FIRMWARE_MAXSIZE (13 * 128 * 1024)  // 1664 kB
#define FIRMWARE_P1_START 0x08040000
#define FIRMWARE_P1_MAXSIZE (6 * 128 * 1024)
#define FIRMWARE_P1_SECTOR_START 6
#define FIRMWARE_P1_SECTOR_END 11

#define ASSETS_START 0x08100000
#define ASSETS_MAXSIZE (3 * 16 * 1024)  // 48 kB
#define ASSETS_SECTOR_START 12
#define ASSETS_SECTOR_END 14

#define UNUSED_2_START 0x0810C000
#define UNUSED_2_MAXSIZE (1 * 16 * 1024)  // 16 kB
#define UNUSED_2_SECTOR_START 15
#define UNUSED_2_SECTOR_END 15

#define STORAGE_2_START 0x08110000
#define STORAGE_2_MAXSIZE (1 * 64 * 1024)  // 64 kB
#define STORAGE_2_SECTOR_START 16
#define STORAGE_2_SECTOR_END 16

#define FIRMWARE_P2_START 0x08120000
#define FIRMWARE_P2_MAXSIZE (7 * 128 * 1024)
#define FIRMWARE_P2_SECTOR_START 17
#define FIRMWARE_P2_SECTOR_END 23

// Ram layout - shared boardloader, bootloader, prodtest
#define S_MAIN_STACK_START 0x10000000
#define S_MAIN_STACK_SIZE (16 * 1024)

#define S_FB1_RAM_START 0x10004000
#define S_FB1_RAM_SIZE (0)

#define S_MAIN_RAM_START 0x10004000
#define S_MAIN_RAM_SIZE (48 * 1024 - 0x100)

// RAM layout - kernel
#define K_MAIN_STACK_START 0x10000000
#define K_MAIN_STACK_SIZE (8 * 1024)

#define K_FB1_RAM_START 0x1000C000
#define K_FB1_RAM_SIZE (0)

#define K_MAIN_RAM_START 0x1000C000
#define K_MAIN_RAM_SIZE (16 * 1024 - 0x100)

// RAM layout - common
#define BOOTARGS_START 0x1000FF00
#define BOOTARGS_SIZE 0x100

#define DMABUF_RAM_START 0x20000000
#define DMABUF_RAM_SIZE (1 * 1024)

#define AUX1_RAM_START (0x20000400)
#define AUX1_RAM_SIZE (191 * 1024)

#define AUX2_RAM_START 0x10002000
#define AUX2_RAM_SIZE (40 * 1024)

// misc
#define CODE_ALIGNMENT 0x200
#define COREAPP_ALIGNMENT 0x200
