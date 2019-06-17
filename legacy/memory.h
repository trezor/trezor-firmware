/*
 * This file is part of the Trezor project, https://trezor.io/
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

 Flash memory layout:

   name    |          range          |  size   |     function
-----------+-------------------------+---------+------------------
 Sector  0 | 0x08000000 - 0x08003FFF |  16 KiB | bootloader
 Sector  1 | 0x08004000 - 0x08007FFF |  16 KiB | bootloader
-----------+-------------------------+---------+------------------
 Sector  2 | 0x08008000 - 0x0800BFFF |  16 KiB | storage area
 Sector  3 | 0x0800C000 - 0x0800FFFF |  16 KiB | storage area
-----------+-------------------------+---------+------------------
 Sector  4 | 0x08010000 - 0x0801FFFF |  64 KiB | firmware
 Sector  5 | 0x08020000 - 0x0803FFFF | 128 KiB | firmware
 Sector  6 | 0x08040000 - 0x0805FFFF | 128 KiB | firmware
 Sector  7 | 0x08060000 - 0x0807FFFF | 128 KiB | firmware
 Sector  8 | 0x08080000 - 0x0809FFFF | 128 KiB | firmware
 Sector  9 | 0x080A0000 - 0x080BFFFF | 128 KiB | firmware
 Sector 10 | 0x080C0000 - 0x080DFFFF | 128 KiB | firmware
 Sector 11 | 0x080E0000 - 0x080FFFFF | 128 KiB | firmware

 firmware header (occupies first 1 KB of the firmware)
 - very similar to trezor-core firmware header described in:
   https://github.com/trezor/trezor-core/blob/master/docs/bootloader.md#firmware-header
 - differences:
   * we don't use sigmask or sig field (these are reserved and set to zero)
   * we introduce new fields immediately following the hash16 field:
     - sig1[64], sig2[64], sig3[64]
     - sigindex1[1], sigindex2[1], sigindex3[1]
   * reserved[415] area is reduced to reserved[220]
 - see signatures.c for more details

 We pad the firmware chunks with zeroes if they are shorted.

 */

#define FLASH_ORIGIN (0x08000000)

#if EMULATOR
extern uint8_t *emulator_flash_base;
#define FLASH_PTR(x) (emulator_flash_base + (x - FLASH_ORIGIN))
#else
#define FLASH_PTR(x) (const uint8_t *)(x)
#endif

#define FLASH_TOTAL_SIZE (1024 * 1024)

#define FLASH_BOOT_START (FLASH_ORIGIN)
#define FLASH_BOOT_LEN (0x8000)

#define FLASH_STORAGE_START (FLASH_BOOT_START + FLASH_BOOT_LEN)
#define FLASH_STORAGE_LEN (0x8000)

#define FLASH_FWHEADER_START (FLASH_STORAGE_START + FLASH_STORAGE_LEN)
#define FLASH_FWHEADER_LEN (0x400)

#define FLASH_APP_START (FLASH_FWHEADER_START + FLASH_FWHEADER_LEN)
#define FLASH_APP_LEN (FLASH_TOTAL_SIZE - (FLASH_APP_START - FLASH_ORIGIN))

#define FLASH_BOOT_SECTOR_FIRST 0
#define FLASH_BOOT_SECTOR_LAST 1

#define FLASH_STORAGE_SECTOR_FIRST 2
#define FLASH_STORAGE_SECTOR_LAST 3

#define FLASH_CODE_SECTOR_FIRST 4
#define FLASH_CODE_SECTOR_LAST 11

void memory_protect(void);
void memory_write_unlock(void);
int memory_bootloader_hash(uint8_t *hash);

static inline void flash_write32(uint32_t addr, uint32_t word) {
  *(volatile uint32_t *)FLASH_PTR(addr) = word;
}
static inline void flash_write8(uint32_t addr, uint8_t byte) {
  *(volatile uint8_t *)FLASH_PTR(addr) = byte;
}

#endif
