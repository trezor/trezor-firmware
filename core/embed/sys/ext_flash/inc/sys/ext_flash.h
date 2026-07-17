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

#ifndef TREZORHAL_EXT_FLASH_H
#define TREZORHAL_EXT_FLASH_H

#include <trezor_types.h>

// AT25SF161B geometry (2 MB NOR flash, 4 KB sectors, 32/64 KB blocks, 256 B pages)
#define EXT_FLASH_SIZE (2 * 1024 * 1024)
#define EXT_FLASH_SECTOR_SIZE (4 * 1024)
#define EXT_FLASH_HALFBLOCK_SIZE (32 * 1024)
#define EXT_FLASH_BLOCK_SIZE (64 * 1024)
#define EXT_FLASH_PAGE_SIZE 256

// Base address of OCTOSPI1 memory-mapped window
#define EXT_FLASH_MMAP_BASE 0x90000000UL

// Erase granularity for ext_flash_erase()
typedef enum {
  EXT_FLASH_ERASE_SECTOR    = 0,  // 4 KB sector containing addr
  EXT_FLASH_ERASE_HALFBLOCK = 1,  // 32 KB half-block containing addr
  EXT_FLASH_ERASE_BLOCK     = 2,  // 64 KB block containing addr
  EXT_FLASH_ERASE_CHIP      = 3,  // entire chip (addr ignored)
} ext_flash_erase_t;

// Initialize the external flash driver (GPIO, OCTOSPI1, OCTOSPIM) and enable
// memory-mapped mode. After a successful call the flash is readable at
// EXT_FLASH_MMAP_BASE from unprivileged code.
bool ext_flash_init(void);

// Disable memory-mapped mode, de-initialize the driver, release GPIOs/clocks.
void ext_flash_deinit(void);

// Write `len` bytes starting at flash byte address `addr`, automatically
// splitting across page boundaries. Temporarily switches to indirect mode
// internally; memory-mapped mode is restored on return.
// The target area must already be erased.
bool ext_flash_write(uint32_t addr, const uint8_t *buf, uint32_t len);

// Erase a sector, block, or the whole chip according to `entity`.
// `addr` is ignored for EXT_FLASH_ERASE_CHIP. Temporarily switches to
// indirect mode internally; memory-mapped mode is restored on return.
bool ext_flash_erase(uint32_t addr, ext_flash_erase_t entity);

#ifdef KERNEL_MODE

// Read `len` bytes from flash byte address `addr` into `buf` (indirect mode).
// Requires memory-mapped mode to be disabled first.
bool ext_flash_read(uint32_t addr, uint8_t *buf, uint32_t len);

// Memory-mapped (XIP) mode control — managed automatically by ext_flash_init/
// ext_flash_write/ext_flash_erase/ext_flash_deinit; exposed here for prodtest.
bool ext_flash_mmap_enable(void);
void ext_flash_mmap_disable(void);
bool ext_flash_is_mmap_enabled(void);

// Fine-grained write/erase helpers — prefer ext_flash_write() / ext_flash_erase().
bool ext_flash_write_page(uint32_t addr, const uint8_t *buf, uint32_t len);
bool ext_flash_erase_sector(uint32_t addr);
bool ext_flash_erase_halfblock(uint32_t addr);
bool ext_flash_erase_block(uint32_t addr);
bool ext_flash_erase_chip(void);

// Diagnostic: reads SR1, SR2, SR3 (any pointer may be NULL).
// Memory-mapped mode must be disabled before calling.
bool ext_flash_read_status(uint8_t *sr1, uint8_t *sr2, uint8_t *sr3);

// SR3 DRV[1:0] values for ext_flash_set_drive_strength()
// WARNING: increasing drive strength on unmatched PCB traces causes ringing
// and intermittent read corruption. Validate with a logic analyser first.
// ext_flash_init() sets DRV_75 (22 pF) for bring-up; raise to DRV_100 once series resistors are fitted.
#define EXT_FLASH_SR3_DRV_AUTO 0x60u  // factory default, 7 pF
#define EXT_FLASH_SR3_DRV_50   0x40u  // 15 pF
#define EXT_FLASH_SR3_DRV_75   0x20u  // 22 pF
#define EXT_FLASH_SR3_DRV_100  0x00u  // 30 pF, requires series resistors on IO lines
bool ext_flash_set_drive_strength(uint8_t drv_bits);

// Debug-only: read using Standard Read (cmd 0x03, 1-1-1, no dummy cycles).
// Max clock 55 MHz (DS fCLK2) — caller must reduce OSPI clock before calling.
// Bypasses IO2/IO3 entirely — use to isolate whether quad-mode corruption
// is in the write path (call this; if data wrong → write broken) or the
// read path (call this; if data OK → only quad read broken).
bool ext_flash_read_slow_debug(uint32_t addr, uint8_t *buf, uint32_t len);

#endif  // KERNEL_MODE

#endif  // TREZORHAL_EXT_FLASH_H
