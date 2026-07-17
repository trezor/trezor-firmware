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

#ifdef KERNEL_MODE

// AT25SF161B geometry (2 MB NOR flash, 4 KB sectors, 64 KB blocks, 256 B pages)
#define EXT_FLASH_SIZE (2 * 1024 * 1024)
#define EXT_FLASH_SECTOR_SIZE (4 * 1024)
#define EXT_FLASH_BLOCK_SIZE (64 * 1024)
#define EXT_FLASH_PAGE_SIZE 256

// Base address of OCTOSPI1 memory-mapped window
#define EXT_FLASH_MMAP_BASE 0x90000000UL

// Initialize the external flash driver (GPIO, OCTOSPI1, OCTOSPIM).
// Enables Quad-SPI mode on the AT25SF161B by setting the QE bit.
// Returns true on success.
bool ext_flash_init(void);

// De-initialize the driver, release GPIOs and clocks.
void ext_flash_deinit(void);

// Read `len` bytes starting at flash byte address `addr` into `buf`.
// Indirect mode must be active (call ext_flash_mmap_disable() first if needed).
bool ext_flash_read(uint32_t addr, uint8_t *buf, uint32_t len);

// Write up to EXT_FLASH_PAGE_SIZE bytes to `addr`.
// `addr` must be page-aligned and the target area must already be erased.
// Indirect mode must be active.
bool ext_flash_write_page(uint32_t addr, const uint8_t *buf, uint32_t len);

// Erase the 4 KB sector that contains `addr`.
// `addr` is aligned down to a sector boundary internally.
// Indirect mode must be active.
bool ext_flash_erase_sector(uint32_t addr);

// Erase the 64 KB block that contains `addr`.
// `addr` is aligned down to a block boundary internally.
// Indirect mode must be active.
bool ext_flash_erase_block(uint32_t addr);

// Erase the entire chip.
// Indirect mode must be active.
bool ext_flash_erase_chip(void);

// Switch to memory-mapped (XIP) mode: the flash appears as read-only memory
// at EXT_FLASH_MMAP_BASE.  Write/erase operations are not possible while
// this mode is active.
bool ext_flash_mmap_enable(void);

// Return to indirect mode, allowing write/erase operations.
void ext_flash_mmap_disable(void);

// Returns true if memory-mapped (XIP) mode is currently active.
bool ext_flash_is_mmap_enabled(void);

// Diagnostic: reads SR1, SR2, SR3 into the provided pointers.
// Any pointer may be NULL if that register is not needed.
// Returns false if the driver is not initialized or a read fails.
bool ext_flash_read_status(uint8_t *sr1, uint8_t *sr2, uint8_t *sr3);

// Set IO drive strength via SR3 DRV[1:0] bits.
// Pass one of: SR3_DRV_AUTO (0x60, factory default, 7 pF) — safe for eval boards
//              SR3_DRV_50   (0x40, 15 pF)
//              SR3_DRV_75   (0x20, 22 pF)
//              SR3_DRV_100  (0x00, 30 pF) — requires series resistors on IO lines
// WARNING: increasing drive strength on unmatched PCB traces causes ringing
// and intermittent read corruption. Validate with a logic analyser first.
// ext_flash_init() sets DRV_100 (30 pF) for 100 MHz operation.
#define EXT_FLASH_SR3_DRV_AUTO  0x60u
#define EXT_FLASH_SR3_DRV_50    0x40u
#define EXT_FLASH_SR3_DRV_75    0x20u
#define EXT_FLASH_SR3_DRV_100   0x00u
bool ext_flash_set_drive_strength(uint8_t drv_bits);

// Debug-only: read using Standard Read (cmd 0x03, 1-1-1, no dummy cycles).
// Bypasses IO2/IO3 entirely — use to isolate whether quad-mode corruption
// is in the write path (call this; if data wrong → write broken) or the
// read path (call this; if data OK → only quad read broken).
bool ext_flash_read_slow_debug(uint32_t addr, uint8_t *buf, uint32_t len);

#endif  // KERNEL_MODE

#endif  // TREZORHAL_EXT_FLASH_H
