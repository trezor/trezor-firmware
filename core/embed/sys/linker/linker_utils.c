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

#include <trezor_rtl.h>

#include <sys/linker_utils.h>

void init_linker_sections(void) {
  extern uint32_t _bss_section_start;
  extern uint32_t _bss_section_end;
  extern uint32_t _data_section_start;
  extern uint32_t _data_section_end;
  extern uint32_t _data_section_loadaddr;
  extern uint32_t _confidential_section_start;
  extern uint32_t _confidential_section_end;
  extern uint32_t _confidential_section_loadaddr;

  // Pointer are intentionally volatile to prevent optimization
  // (otherwise the compiler may optimize loops to memset/memcpy)
  volatile uint32_t* dst;
  volatile uint32_t* src;

  dst = &_bss_section_start;
  while (dst < &_bss_section_end) {
    *dst++ = 0;
  }

  dst = &_data_section_start;
  src = &_data_section_loadaddr;
  while (dst < &_data_section_end) {
    *dst++ = *src++;
  }

  dst = &_confidential_section_start;
  src = &_confidential_section_loadaddr;
  while (dst < &_confidential_section_end) {
    *dst++ = *src++;
  }
}

static void memregion_remove_block(memregion_t* region, int idx) {
  if (idx < 0 || idx >= MEMREGION_MAX_BLOCKS) {
    return;
  }

  for (int i = idx; i < MEMREGION_MAX_BLOCKS - 1; i++) {
    region->block[i] = region->block[i + 1];
  }

  memregion_block_t* last = &region->block[MEMREGION_MAX_BLOCKS - 1];
  last->start = NULL;
  last->end = NULL;
}

static void memregion_insert_block(memregion_t* region, int idx, void* start,
                                   void* end) {
  if (idx < 0 || idx >= MEMREGION_MAX_BLOCKS) {
    return;
  }

  for (int i = MEMREGION_MAX_BLOCKS - 1; i > idx; i--) {
    region->block[i] = region->block[i - 1];
  }

  region->block[idx].start = start;
  region->block[idx].end = end;
}

void memregion_add_range(memregion_t* region, void* start, void* end) {
  int idx = 0;

  while ((start < end) && (idx < MEMREGION_MAX_BLOCKS)) {
    memregion_block_t* b = &region->block[idx];
    if (b->start >= b->end) {
      // The added range is completely after the last block
      // in the region. Just add it as a block at the end.
      b->start = start;
      b->end = end;
      break;
    } else if (end < b->start) {
      // The added range is completely before `b`.
      // Shift all blocks after the inserted block
      // Insert the new block
      memregion_insert_block(region, idx, start, end);
      break;
    } else if (start < b->end) {
      // The inserted range overlaps with `b`.
      // Extend the block 'b'.
      b->start = MIN(start, b->start);
      // Shorten the added range
      start = MAX(start, b->end);
    } else {
      // The added range is behind 'b'
      // Move to the next block
      idx += 1;
    }
  }
}

void memregion_del_range(memregion_t* region, void* start, void* end) {
  int idx = 0;

  while ((start < end) && (idx < MEMREGION_MAX_BLOCKS)) {
    memregion_block_t* b = &region->block[idx];
    if (b->start >= b->end) {
      // Deleted range is completely after the last block
      break;
    } else if (end < b->start) {
      // Deleted range is completely before `b`.
      break;
    } else if (start < b->end) {
      // Deleted range overlaps with `b`.

      if (start <= b->start) {
        // Deleted range overlaps beginning of 'b'.
        // Cut the beginning of the block 'b'.
        b->start = MIN(end, b->end);
        start = b->start;

        // If the block is empty, remove it
        if (b->start >= b->end) {
          memregion_remove_block(region, idx);
        }
      } else if (end >= b->end) {
        // Deleted range overlaps end of 'b'.
        // Cut the end of the block 'b'
        b->end = start;
      } else {
        // Deleted range is inside 'b'.
        // Split the block 'b' into two blocks.
        void* new_start = end;
        void* new_end = b->end;

        // Cut the end of the block 'b'
        b->end = start;

        // Insert a new block, if there is a free space
        memregion_insert_block(region, idx + 1, new_start, new_end);
        break;
      }
    } else {
      // The deleted range is behind 'b'
      // Move to the next block
      idx += 1;
    }
  }
}

__attribute((no_stack_protector)) void memregion_fill(memregion_t* region,
                                                      uint32_t value) {
  for (int i = 0; i < MEMREGION_MAX_BLOCKS; i++) {
    memregion_block_t* block = &region->block[i];
    if (block->start < block->end) {
      // Pointer is intentionally volatile to prevent optimization
      // (otherwise the compiler may optimize loop to memset)
      volatile uint32_t* ptr = block->start;
      while ((void*)ptr < block->end) {
        *ptr++ = value;
      }
    }
  }
}
