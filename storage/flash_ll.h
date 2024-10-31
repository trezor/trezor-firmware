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

#ifndef FLASH_LL_H_
#define FLASH_LL_H_

#include <secbool.h>
#include <stdint.h>

// Flash memory low-level API, providing abstraction for
// various flash archictures found on STM32 MCUs

// The 'sector' parameter in this API can represent
//    1. Non-uniform sector number on STM32F4
//    2. Uniform page number on STM32U5

#define FLASH_QUADWORD_WORDS (4)
#define FLASH_QUADWORD_SIZE (FLASH_QUADWORD_WORDS * sizeof(uint32_t))

#define FLASH_BURST_WORDS (8 * FLASH_QUADWORD_WORDS)
#define FLASH_BURST_SIZE (FLASH_BURST_WORDS * sizeof(uint32_t))

#define FLASH_BLOCK_SIZE (sizeof(uint32_t) * FLASH_BLOCK_WORDS)

typedef uint32_t flash_block_t[FLASH_BLOCK_WORDS];

#if FLASH_BLOCK_WORDS == 1
#define FLASH_ALIGN(X) (((X) + 3) & ~3)
#define FLASH_IS_ALIGNED(X) (((X) & 3) == 0)
#elif FLASH_BLOCK_WORDS == 4
#define FLASH_ALIGN(X) (((X) + 0xF) & ~0xF)
#define FLASH_IS_ALIGNED(X) (((X) & 0xF) == 0)
#else
#error Unsupported number of FLASH_BLOCK_WORDS.
#endif

// Returns the size of the a continuous area of sectors
// Returns 0 if any of the sectors is out of range
uint32_t flash_sector_size(uint16_t first_sector, uint16_t sector_count);

// Returns number of the sector/page at specified byte 'offset'
// from the beginning of the 'first_sector'
uint16_t flash_sector_find(uint16_t first_sector, uint32_t offset);

// Returns the physical address of a byte on specified 'offset' in the specified
// 'sector'. Checks if it's possible to access continues space of 'size' bytes
// Returns NULL i [offset, offset + size] is of out of the specified sector
const void *flash_get_address(uint16_t sector, uint32_t offset, uint32_t size);

// Unlocks the flash memory for writes/erase operations
// Flash must be locked again as soon as possible
secbool __wur flash_unlock_write(void);

// Locks the flash memory for writes/erase operations
secbool __wur flash_lock_write(void);

#if defined FLASH_BIT_ACCESS

// Writes a single byte to the specified 'offset' inside a flash 'sector'
secbool __wur flash_write_byte(uint16_t sector, uint32_t offset, uint8_t data);

// Writes a single 32-bit word to the specified 'offset' inside a flash 'sector'
secbool __wur flash_write_word(uint16_t sector, uint32_t offset, uint32_t data);

#endif

// Writes a 16-byte block to specified 'offset' inside a flash 'sector'
secbool __wur flash_write_quadword(uint16_t sector, uint32_t offset,
                                   const uint32_t *data);

// Writes a 128-byte burst to specified 'offset' inside a flash 'sector'
secbool __wur flash_write_burst(uint16_t sector, uint32_t offset,
                                const uint32_t *data);

// Erases a single sector/page of flash memory
secbool __wur flash_sector_erase(uint16_t sector);

// Writes a block to specified 'offset' inside a flash 'sector'
// Block represents a natural unit of the given flash memory
secbool flash_write_block(uint16_t sector, uint32_t offset,
                          const flash_block_t block);

#endif  // FLASH_LL_H
