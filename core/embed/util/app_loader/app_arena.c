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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include "app_arena.h"

#include <stdlib.h>

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

// Simple arena allocator that can allocate up to two blocks:
//  - one "image" block from the front of the arena
//  - one "data" block from the back of the arena
//
// The image block always starts at mem_ptr (offset 0).
// The data block always grows from the end of the arena backwards.
//
// At most one image block and one data block can exist at the same time.
// This allocator does NOT support general-purpose malloc/free patterns.
//

typedef struct {
  // Indicates whether the arena is initialized
  bool initialized;

  // Base pointer to the arena memoru
  uint8_t* mem_ptr;
  // Total size of the arena memory
  size_t mem_size;

  // Size of the image block at the fron (0 if none)
  size_t front_used;
  // Size of the data block at the back (0 if none)
  size_t back_used;

} app_arena_t;

// Global app arena instance
static app_arena_t g_app_arena = {0};

bool app_arena_init() {
  app_arena_t* arena = &g_app_arena;

  if (arena->initialized) {
    return true;
  }

  memset(arena, 0, sizeof(app_arena_t));

#ifdef TREZOR_EMULATOR
  arena->mem_size = 64 * 1024 * 1024;
  arena->mem_ptr = malloc(arena->mem_size);
  if (arena->mem_ptr == NULL) {
    return false;
  }
#else
  arena->mem_size = APPDATA_RAM_SIZE;
  arena->mem_ptr = (uint8_t*)APPDATA_RAM_START;

#ifdef USE_TRUSTZONE
  // Allow unprivileged access to app arena memory
  tz_set_sram_unpriv(APPDATA_RAM_START, APPDATA_RAM_SIZE, true);
  // Allow unprivileged access to app code area
  tz_set_flash_unpriv(APPCODE_START, APPCODE_MAXSIZE, true);
#endif

#endif

  arena->initialized = true;
  return true;
}

void* app_arena_alloc(size_t block_size, app_alloc_type_t type) {
  app_arena_t* arena = &g_app_arena;

  if (!arena->initialized) {
    return NULL;
  }

  switch (type) {
    case APP_ALLOC_IMAGE:
      // Only one image block allowed
      if (arena->front_used > 0) {
        return NULL;
      }

      // Check for available space
      if (arena->back_used + block_size > arena->mem_size) {
        return NULL;
      }

      arena->front_used = block_size;

      // Image block always starts at the beginning of the arena
      return arena->mem_ptr;

    case APP_ALLOC_DATA:
      // Only one data block allowed
      if (arena->back_used) {
        return NULL;
      }

      // Check for available space
      if (arena->front_used + block_size > arena->mem_size) {
        return NULL;
      }

      arena->back_used = block_size;

      // Data block grows from the end of the arena backwards
      return arena->mem_ptr + (arena->mem_size - arena->back_used);
  }

  return NULL;
}

void app_arena_free(void* ptr) {
  app_arena_t* arena = &g_app_arena;

  if (!arena->initialized) {
    return;
  }

  if (ptr == arena->mem_ptr && arena->front_used > 0) {
    arena->front_used = 0;
    return;
  }

  if (ptr == arena->mem_ptr + (arena->mem_size - arena->back_used) &&
      arena->back_used > 0) {
    arena->back_used = 0;
    return;
  }
}
