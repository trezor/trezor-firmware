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

#ifdef KERNEL_MODE

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/applet.h>
#include <sys/coreapp.h>
#include <sys/mpu.h>
#include <util/image.h>

#include "../app_arena.h"

#include "tapp_loader.h"

// TAPP file header is padded to this size
#define TAPP_HEADER_SIZE 1024
// TAPP file header magic number
#define TAPP_HEADER_MAGIC 0x50504154  // "TAPP"
// Limits for application stack
#define TAPP_STACK_LIMIT (128 * 1024)
// Limits for application RW data segment
#define TAPP_RW_DATA_LIMIT (256 * 1024)

// Alignment required for MPU regions
#define MPU_ALIGNMENT 32

// Application image header structure
typedef struct {
  // Applet header magic number (TAP_HEADER_MAGIC)
  uint32_t magic;
  // Total size of the TAPP image including header
  uint32_t image_size;
  // Virtual address of code and rodata segment (for relocation purposes)
  uint32_t code_va;
  // Offset of code and rodata segment within the image
  uint32_t code_offset;
  // Size of code and rodata segment
  uint32_t code_size;
  // Virtual address of rw data segment (for relocation purposes)
  uint32_t data_va;
  // Size of rw data segment
  uint32_t data_size;
  // Offset of initialization data segment within the image
  uint32_t idata_offset;
  // Size of initialization data segment
  // (must be less or equal to data_size field)
  uint32_t idata_size;
  // Relocation table offset
  uint32_t reloc_offset;
  // Relocation table size (in bytes)
  uint32_t reloc_size;
  // Size of the stack
  uint32_t stack_size;
  // App entrypoint offset within code segment (relative to code_offset)
  uint32_t entrypoint;
  // Padding to make the header size equal to TAPP_HEADER_SIZE
  uint8_t _padding[TAPP_HEADER_SIZE - 13 * 4];
} tapp_header_t;

_Static_assert(sizeof(tapp_header_t) == TAPP_HEADER_SIZE,
               "Invalid TAPP header size");

static void tapp_unload_cb(applet_t* applet) {
  void* ram_start = (void*)applet->layout.data1.start;
  size_t ram_size = applet->layout.data1.size;

  if (ram_start != NULL && ram_size > 0) {
    // Clear applet data segment
    mpu_set_active_applet(&applet->layout);
    memset(ram_start, 0, ram_size);
    mpu_set_active_applet(NULL);

    // Free applet RAM
    app_arena_free(ram_start);
  }
}

static tapp_header_t* validate_tapp_image(const void* img_ptr, size_t img_size) {
  if (img_size < TAPP_HEADER_SIZE) {
    return NULL;
  }

  tapp_header_t* img = (tapp_header_t*)img_ptr;

  if (img->magic != TAPP_HEADER_MAGIC) {
    return NULL;
  }

  if (img->image_size != img_size) {
    return NULL;
  }

  // Check whether code and rodata segment is within bounds
  if (img->code_offset > img_size || img->code_size > img_size - img->code_offset) {
    return NULL;
  }

  // Check whether rw segment is within bounds
  if (img->idata_offset > img_size ||
      img->idata_size > img_size - img->idata_offset) {
    return NULL;
  }

  // Check whether relocation data is within bounds
  if (img->reloc_offset > img_size ||
      img->reloc_size > img_size - img->reloc_offset) {
    return NULL;
  }

  // Limit stack size to reasonable value
  if (img->stack_size > TAPP_STACK_LIMIT) {
    return NULL;
  }

  // Limit rw data size to reasonable value
  if (img->data_size > TAPP_RW_DATA_LIMIT) {
    return NULL;
  }

  // Check whether entrypoint is within code segment
  if (img->entrypoint < img->code_offset ||
      img->entrypoint >= img->code_offset + img->code_size) {
    return NULL;
  }

  return img;
}

// Map virtual address to physical address within the
// TAPP image or rw data segment
uint32_t map_va(tapp_header_t* img, uint32_t va, uint32_t sb_addr) {
  if (va >= img->code_va &&
      va < img->code_va + img->code_size) {
    return (uintptr_t)img + img->code_offset + (va - img->code_va);
  } else if (va >= img->data_va &&
             va < img->data_va + img->data_size) {
    return sb_addr + (va - img->data_va);
  } else {
    return 0;
  }
}

static bool initialize_rw_data(tapp_header_t* img, uint32_t sb_addr) {
  // Copy initialization data to the beginning of rw segment
  const uint8_t* idata_start = (const uint8_t*)img + img->idata_offset;
  memcpy((void*)sb_addr, idata_start, img->idata_size);

  // Apply relocations in RW segment
  const uint32_t* rel = (const uint32_t*)((uintptr_t)img + img->reloc_offset);
  const uint32_t* rel_end = (const uint32_t*)((uintptr_t)rel + img->reloc_size);

  while (rel < rel_end) {
    // Get virtual address of word in memory to update
    uint32_t addr = *rel;

    if (addr < img->data_va || img->data_size < 4 ||
        addr > img->data_va + img->data_size - 4) {
      // Invalid virtual address (not within rw data segment)
      return false;
    }

    // Get pointer to the relocated 32-bit word
    uint32_t* mem_ptr = (uint32_t*)map_va(img, *rel, sb_addr);
    if (mem_ptr == NULL) {
      return false;
    }

    // Relocate the 32-bit word
    *mem_ptr = map_va(img, *mem_ptr, sb_addr);

    ++rel;
  }

  return true;
}

bool tapp_load(applet_t* applet, const void* img_ptr, size_t img_size) {
  applet_init(applet, NULL, NULL);

  // Make sure the entire image is accessible so we can validate it
  const applet_layout_t temp_layout_1 = {
      .code1 = {.start = (uintptr_t)img_ptr, .size = img_size},
  };
  mpu_set_active_applet(&temp_layout_1);

  tapp_header_t* img = validate_tapp_image(img_ptr, img_size);

  // Allocate RAM for stack and rw segment
  size_t ram_size = ALIGN_UP(img->stack_size + img->data_size, MPU_ALIGNMENT);
  void* ram_ptr = app_arena_alloc(ram_size, APP_ALLOC_DATA);
  if (ram_ptr == NULL) {
    goto cleanup;
  }

  // Make sure we have access to the image as well as allocated ram
  const applet_layout_t temp_layout_2 = {
      .code1 = {.start = (uintptr_t)img_ptr, .size = img_size},
      .data1 = {.start = (uintptr_t)ram_ptr, .size = ram_size},
  };
  mpu_set_active_applet(&temp_layout_2);

  // Clear all allocated ram
  memset(ram_ptr, 0, ram_size);

  // Calculate static base address (pointing to the beginning of rw data
  // segment, just after the stack)
  uint32_t sb_addr = (uintptr_t)ram_ptr + img->stack_size;

  applet_privileges_t app_privileges = {0};
  applet_init(applet, &app_privileges, tapp_unload_cb);
  applet->privileges = app_privileges;

  // Prepare applet memory layout
  applet->layout.code1.start = (uintptr_t)img + img->code_offset;
  applet->layout.code1.size = ALIGN_UP(img->code_size, MPU_ALIGNMENT);
  applet->layout.data1.start = (uintptr_t)ram_ptr;
  applet->layout.data1.size = ram_size;

  // It's intended to call coreapp functions directly so we have to make
  // coreapp code and TLS areas accessible when the applet is running.
  applet->layout.code2 = coreapp_get_code_area();
  applet->layout.tls = coreapp_get_tls_area();

  // Initialize RW segment
  if (!initialize_rw_data(img, sb_addr)) {
    goto cleanup;
  }

  uint32_t stack_base = (uint32_t)ram_ptr;
  uint32_t stack_size = img->stack_size;

  // Initialize the applet task
  if (!systask_init(&applet->task, stack_base, stack_size, sb_addr, applet)) {
    goto cleanup;
  }

  // Enable coreapp TLS area swapping
  systask_enable_tls(&applet->task, coreapp_get_tls_area());

  uint32_t entrypoint = (uint32_t)img + img->code_offset + img->entrypoint;
  uint32_t api_getter = (uint32_t)coreapp_get_api_getter();

  // Prepare the applet to run - push exception frame on the stack
  // with the entrypoint address
  if (!systask_push_call(&applet->task, (void*)entrypoint, api_getter, 0, 0)) {
    goto cleanup;
  }

  return true;

cleanup:
  applet_unload(applet);
  return false;
}

#endif  // KERNEL_MODE
