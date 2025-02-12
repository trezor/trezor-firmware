
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

// symbols defined in the linker script
extern uint8_t _stack_section_start;
extern uint8_t _stack_section_end;

// Initialize linker script-defined sections (.bss, .data, etc.)
//
// This function must be called only during the startup sequence,
// before executing any other code. In special cases, it can be used
// to reinitialize these sections if necessary.
void init_linker_sections(void);

// Maximum number of memory blocks in a memory region
#define MEMREGION_MAX_BLOCKS 8

typedef struct {
  // block start address (inclusive)
  void* start;
  // block end address (exclusive)
  void* end;
} memregion_block_t;

typedef struct {
  // non-overlapping memory blocks ordered by start address
  memregion_block_t block[MEMREGION_MAX_BLOCKS];
} memregion_t;

#define MEMREGION_ALL_ACCESSIBLE_RAM                                      \
  ({                                                                      \
    extern uint8_t _accessible_ram_0_start;                               \
    extern uint8_t _accessible_ram_0_end;                                 \
    extern uint8_t _accessible_ram_1_start;                               \
    extern uint8_t _accessible_ram_1_end;                                 \
    (memregion_t){.block = {                                              \
                      {&_accessible_ram_0_start, &_accessible_ram_0_end}, \
                      {&_accessible_ram_1_start, &_accessible_ram_1_end}, \
                  }};                                                     \
  })

// Adds a new address range to the memory region.
//
// The start and end pointers must be aligned to 4-byte boundaries.
//
// The current implementation does not merge overlapping or adjacent blocks.
// This behavior is not required for the current use case and, in the
//  worst case, will result in a few additional blocks in the region.
void memregion_add_range(memregion_t* region, void* start, void* end);

// Deletes an address range from the memory region
//
// The range start and end pointers must be aligned to the 4 bytes.
void memregion_del_range(memregion_t* region, void* start, void* end);

// Fill memory region with a value 32-bit value
void memregion_fill(memregion_t* region, uint32_t value);

#define MEMREGION_ADD_SECTION(region, section_name)                          \
  {                                                                          \
    extern uint8_t section_name##_start;                                     \
    extern uint8_t section_name##_end;                                       \
    memregion_add_range(region, &section_name##_start, &section_name##_end); \
  }

#define MEMREGION_DEL_SECTION(region, section_name)                          \
  {                                                                          \
    extern uint8_t section_name##_start;                                     \
    extern uint8_t section_name##_end;                                       \
    memregion_del_range(region, &section_name##_start, &section_name##_end); \
  }
