/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __MEMORY_H__
#define __MEMORY_H__

#include <stdint.h>

/*

 flash memory layout:

   name    |          range          |  size   |     function
-----------+-------------------------+---------+------------------
 Sector  0 | 0x08000000 - 0x08003FFF |  16 KiB | bootloader code
 Sector  1 | 0x08004000 - 0x08007FFF |  16 KiB | bootloader code
-----------+-------------------------+---------+------------------
 Sector  2 | 0x08008000 - 0x0800BFFF |  16 KiB | metadata area
 Sector  3 | 0x0800C000 - 0x0800FFFF |  16 KiB | metadata area
-----------+-------------------------+---------+------------------
 Sector  4 | 0x08010000 - 0x0801FFFF |  64 KiB | application code
 Sector  5 | 0x08020000 - 0x0803FFFF | 128 KiB | application code
 Sector  6 | 0x08040000 - 0x0805FFFF | 128 KiB | application code
 Sector  7 | 0x08060000 - 0x0807FFFF | 128 KiB | application code
===========+=========================+============================
 Sector  8 | 0x08080000 - 0x0809FFFF | 128 KiB | N/A
 Sector  9 | 0x080A0000 - 0x080BFFFF | 128 KiB | N/A
 Sector 10 | 0x080C0000 - 0x080DFFFF | 128 KiB | N/A
 Sector 11 | 0x080E0000 - 0x080FFFFF | 128 KiB | N/A

 metadata area:

 offset | type/length |  description
--------+-------------+-------------------------------
 0x0000 |  4 bytes    |  magic = 'TRZR'
 0x0004 |  uint32     |  length of the code (codelen)
 0x0008 |  uint8      |  signature index #1
 0x0009 |  uint8      |  signature index #2
 0x000A |  uint8      |  signature index #3
 0x000B |  uint8      |  flags
 0x000C |  52 bytes   |  reserved
 0x0040 |  64 bytes   |  signature #1
 0x0080 |  64 bytes   |  signature #2
 0x00C0 |  64 bytes   |  signature #3
 0x0100 |  32K-256 B  |  persistent storage

 flags & 0x01 -> restore storage after flashing (if signatures are ok)

 */

#define FLASH_ORIGIN		(0x08000000)

#if EMULATOR
extern uint8_t *emulator_flash_base;
#define FLASH_PTR(x)		(emulator_flash_base + (x - FLASH_ORIGIN))
#else
#define FLASH_PTR(x)		(const uint8_t*) (x)
#endif

#define FLASH_TOTAL_SIZE	(512 * 1024)

#define FLASH_BOOT_START	(FLASH_ORIGIN)
#define FLASH_BOOT_LEN		(0x8000)

#define FLASH_META_START	(FLASH_BOOT_START + FLASH_BOOT_LEN)
#define FLASH_META_LEN		(0x8000)

#define FLASH_APP_START		(FLASH_META_START + FLASH_META_LEN)

#define FLASH_META_MAGIC	(FLASH_META_START)
#define FLASH_META_CODELEN	(FLASH_META_START + 0x0004)
#define FLASH_META_SIGINDEX1	(FLASH_META_START + 0x0008)
#define FLASH_META_SIGINDEX2	(FLASH_META_START + 0x0009)
#define FLASH_META_SIGINDEX3	(FLASH_META_START + 0x000A)
#define FLASH_META_FLAGS	(FLASH_META_START + 0x000B)
#define FLASH_META_SIG1		(FLASH_META_START + 0x0040)
#define FLASH_META_SIG2		(FLASH_META_START + 0x0080)
#define FLASH_META_SIG3		(FLASH_META_START + 0x00C0)

#define FLASH_META_DESC_LEN		(0x100)

#define FLASH_STORAGE_START	(FLASH_META_START + FLASH_META_DESC_LEN)
#define FLASH_STORAGE_LEN	(FLASH_APP_START - FLASH_STORAGE_START)

#define FLASH_BOOT_SECTOR_FIRST	0
#define FLASH_BOOT_SECTOR_LAST	1

#define FLASH_META_SECTOR_FIRST	2
#define FLASH_META_SECTOR_LAST	3

#define FLASH_CODE_SECTOR_FIRST	4
#define FLASH_CODE_SECTOR_LAST	7

void memory_protect(void);
void memory_write_unlock(void);
int memory_bootloader_hash(uint8_t *hash);

inline void flash_write32(uint32_t addr, uint32_t word) {
	*(volatile uint32_t *) FLASH_PTR(addr) = word;
}
inline void flash_write8(uint32_t addr, uint8_t byte) {
	*(volatile uint8_t *) FLASH_PTR(addr) = byte;
}

#endif
