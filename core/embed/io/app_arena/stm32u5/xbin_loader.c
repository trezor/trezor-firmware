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

#include <rtl/sizedefs.h>
#include <sys/applet.h>
#include <sys/coreapp.h>
#include <sys/mpu.h>

// #include "../app_arena.h"
#include "../xbin_loader.h"

// Alignment required for MPU regions
#define MPU_ALIGNMENT 32

typedef struct {
  // Size of the read-only segment
  // It starts after the header and has virtual address 0
  uint32_t ro_size;
  // Number of relocations after read-only data
  // Each relocation is a 4-byte virtual address in the app image
  uint32_t reloc_count;
  // Read-write segment size to reserve at load time
  uint32_t rw_size;
  // Virtual address of the read-write segment
  uint32_t rw_va;
  // Virtual address of RW init data
  // Copy init data from RO to RW at load time
  uint32_t rw_init_va;
  // Size of RW init data in bytes
  uint32_t rw_init_size;
  // Virtual address of the app stack
  uint32_t stack_va;
  // App stack size in bytes
  uint32_t stack_size;
  // Heap size in bytes. Unused now; set to 0
  uint32_t heap_size;
  // Virtual address of entry function (applet_main) in RO segment
  uint32_t entry_va;
  // Reserved for future use
  uint32_t _reserved[6];
} payload_header_t;

_Static_assert(sizeof(payload_header_t) == 64,
               "payload_header_t must be 64 bytes");

_Static_assert(sizeof(xbin_header_t) % MPU_ALIGNMENT == 0,
               "xbin_header_t must be 32-byte aligned");

typedef struct {
  // RO segment (from original elf)
  uint32_t ro_v_addr;
  uint32_t ro_p_addr;
  uint32_t ro_size;
  // RW segment (from original elf)
  uint32_t rw_v_addr;
  uint32_t rw_p_addr;
  uint32_t rw_size;
  // Stack address and size
  uint32_t stack_p_addr;
  uint32_t stack_size;
  // Heap address and size
  uint32_t heap_p_addr;
  uint32_t heap_size;
} va_map_t;

static uint8_t* map_va_size(const va_map_t* map, uint32_t va, size_t size) {
  if (va + size < va) {
    // Overflow
    return NULL;
  }

  if (va >= map->ro_v_addr && va + size <= map->ro_v_addr + map->ro_size) {
    // Address within RO segment
    return (uint8_t*)map->ro_p_addr + (va - map->ro_v_addr);
  } else if (va >= map->rw_v_addr &&
             va + size <= map->rw_v_addr + map->rw_size) {
    // Address within RW segment
    return (uint8_t*)map->rw_p_addr + (va - map->rw_v_addr);
  } else {
    // Address not within any mapped segment
    return NULL;
  }
}

static uint8_t* map_va(const va_map_t* map, uint32_t va) {
  return map_va_size(map, va, 0);
}

const xbin_header_t* xbin_verify_image(const void* image, size_t image_size) {
  TSH_DECLARE;
  const xbin_header_t* retval = NULL;

  TSH_CHECK(image != NULL, TS_EINVAL);
  TSH_CHECK(image_size >= sizeof(xbin_header_t), TS_EINVAL);
  TSH_CHECK(IS_ALIGNED((uintptr_t)image, MPU_ALIGNMENT), TS_EINVAL);
  TSH_CHECK(IS_ALIGNED(image_size, MPU_ALIGNMENT), TS_EINVAL);

  const xbin_header_t* header = (const xbin_header_t*)image;

  // Make the image header accessible for verification
  mpu_set_active_applet(&(applet_layout_t){
      .data1 =
          {
              .start = (uintptr_t)image,
              .size = sizeof(xbin_header_t),
          },
  });

  TSH_CHECK(header->magic == XBIN_HEADER_MAGIC, TS_EINVAL);
  TSH_CHECK(header->header_size >= sizeof(xbin_header_t), TS_EINVAL);
  TSH_CHECK(IS_ALIGNED(header->header_size, MPU_ALIGNMENT), TS_EINVAL);
  TSH_CHECK(header->header_size <= image_size, TS_EINVAL);
  TSH_CHECK(header->abi_version == 1, TS_EINVAL);
  TSH_CHECK(header->payload_type == XBIN_TARGET_ARMV8M, TS_EINVAL);
  TSH_CHECK(header->payload_size >= sizeof(payload_header_t), TS_EINVAL);
  TSH_CHECK(IS_ALIGNED(header->payload_size, MPU_ALIGNMENT), TS_EINVAL);
  TSH_CHECK(header->payload_size + header->header_size == image_size,
            TS_EINVAL);

  // Make the payload header accessible
  mpu_set_active_applet(&(applet_layout_t){
      .data1 =
          {
              .start = (uintptr_t)image,
              .size = header->header_size + sizeof(payload_header_t),
          },
  });

  const payload_header_t* p =
      (const payload_header_t*)((const uint8_t*)header + header->header_size);

  uint32_t raw_data_size = header->payload_size - sizeof(payload_header_t);

  // Check that ro segment size and relocations fit within the image
  TSH_CHECK(p->ro_size <= raw_data_size, TS_EINVAL);
  TSH_CHECK(p->reloc_count <= (raw_data_size - p->ro_size) / 4, TS_EINVAL);

  // Check whether the total image size (including RO segment and relocations)
  // fits within the provided image size
  TSH_CHECK(header->header_size + header->payload_size <= image_size,
            TS_EINVAL);

  // Check that RW segment size and address are valid
  TSH_CHECK(p->rw_va >= p->ro_size, TS_EINVAL);
  TSH_CHECK(p->rw_va + p->rw_size >= p->rw_va, TS_EINVAL);
  TSH_CHECK(p->rw_size < APPDATA_RAM_SIZE, TS_ENOMEM);

  // Check that the RW init data is within the RO segment
  TSH_CHECK(p->rw_init_va + p->rw_init_size >= p->rw_init_va, TS_EINVAL);
  TSH_CHECK(p->rw_init_va + p->rw_init_size <= p->ro_size, TS_EINVAL);

  // Check that the stack size is within rw_data
  TSH_CHECK(p->stack_va + p->stack_size >= p->stack_va, TS_EINVAL);
  TSH_CHECK(p->stack_va >= p->rw_va, TS_EINVAL);
  TSH_CHECK(p->stack_va + p->stack_size <= p->rw_va + p->rw_size, TS_EINVAL);

  // Check that the heap size is reasonable
  TSH_CHECK(p->heap_size < APPDATA_RAM_SIZE, TS_ENOMEM);

  // Check that the entrypoint is within the RO segment
  TSH_CHECK(p->entry_va < p->ro_size, TS_EINVAL);

  retval = header;

cleanup:
  systask_set_mpu(systask_active());
  return retval;
}

ts_t xbin_verify_signature(const xbin_header_t* header, const void* proof,
                           size_t proof_size) {
  TSH_DECLARE;

  // Make the header accessible
  mpu_set_active_applet(&(applet_layout_t){
      .data1 =
          {
              .start = (uintptr_t)header,
              .size = sizeof(xbin_header_t),
          },
  });

  // Make the entire image accessible for signature verification
  mpu_set_active_applet(&(applet_layout_t){
      .data1 =
          {
              .start = (uintptr_t)header,
              .size = header->header_size + header->payload_size,
          },
  });

  // TODO !@# verify signature as soons as the signing scheme is defined

  // cleanup:
  systask_set_mpu(systask_active());
  TSH_RETURN;
}

#define STACK_ALIGNMENT 8

static ts_t xbin_fit_in_memory(const payload_header_t* p, void* rwmem,
                               size_t rwmem_size, va_map_t* map) {
  TSH_DECLARE;

  TSH_CHECK(rwmem_size >= p->rw_size + p->stack_size + p->heap_size, TS_EINVAL);

  map->ro_v_addr = 0;
  map->ro_p_addr = (uint32_t)p + sizeof(payload_header_t);
  map->ro_size = p->ro_size;

  map->rw_v_addr = p->rw_va;
  map->rw_p_addr = (uint32_t)rwmem;
  map->rw_size = ALIGN_UP(p->rw_size, STACK_ALIGNMENT);

  map->stack_p_addr = map->rw_p_addr + (p->stack_va - p->rw_va);
  // map->stack_p_addr = map->rw_p_addr + map->rw_size;  (stack above RW data)
  map->stack_size = ALIGN_UP(p->stack_size, STACK_ALIGNMENT);

  map->heap_p_addr = map->stack_p_addr + map->stack_size;
  map->heap_size = ALIGN_UP(p->heap_size, MPU_ALIGNMENT);

  TSH_CHECK(map->heap_p_addr + map->heap_size <= (uint32_t)rwmem + rwmem_size,
            TS_ENOMEM);

cleanup:
  TSH_RETURN;
}

// Callback invoked when applet is unloaded
static void xbin_unload_cb(applet_t* applet) {
  mpu_set_active_applet(&applet->layout);

  // Clear RW segment, stack and the heap to remove any sensitive information
  // before freeing the memory

  void* rwmem = (void*)applet->layout.data1.start;
  size_t rwmem_size = applet->layout.data1.size;
  memset(rwmem, 0, rwmem_size);

  systask_set_mpu(systask_active());
}

static ts_t xbin_apply_relocations(const payload_header_t* p,
                                   const va_map_t* map) {
  TSH_DECLARE;

  uint32_t* reloc_table =
      (uint32_t*)((uint8_t*)p + sizeof(payload_header_t) + p->ro_size);

  // Check reloc table first (so we don't modify anything if the table is
  // invalid)
  for (uint32_t i = 0; i < p->reloc_count; i++) {
    uint32_t reloc_va = reloc_table[i];
    uint32_t* reloc_ptr =
        (uint32_t*)map_va_size(map, reloc_va, sizeof(uint32_t));
    TSH_CHECK(reloc_ptr != NULL, TS_EINVAL);
    TSH_CHECK(map_va(map, *reloc_ptr) != NULL, TS_EINVAL);
  }

  // Apply relocations
  for (uint32_t i = 0; i < p->reloc_count; i++) {
    uint32_t reloc_va = reloc_table[i];
    uint32_t* reloc_ptr = (uint32_t*)map_va(map, reloc_va);
    *reloc_ptr = (uint32_t)map_va(map, *reloc_ptr);
  }

cleanup:
  TSH_RETURN;
}

ts_t xbin_prepare_applet(const xbin_header_t* header, void* rwmem,
                         size_t rwmem_size, applet_t* applet) {
  TSH_DECLARE;
  ts_t status;

  va_map_t map = {0};

  TSH_CHECK_ARG(IS_ALIGNED((uintptr_t)rwmem, MPU_ALIGNMENT));
  TSH_CHECK_ARG(IS_ALIGNED((uintptr_t)rwmem_size, MPU_ALIGNMENT));

  // Make the header accessible
  mpu_set_active_applet(&(applet_layout_t){
      .data1 =
          {
              .start = (uintptr_t)header,
              .size = sizeof(xbin_header_t),
          },
  });

  // Make the entire image accessible for preparation (relocations, etc.)
  mpu_set_active_applet(&(applet_layout_t){
      .data1 =
          {
              .start = (uintptr_t)header,
              .size = header->header_size + header->payload_size,
          },
      .data2 =
          {
              .start = (uintptr_t)rwmem,
              .size = rwmem_size,
          },
  });

  payload_header_t* p =
      (payload_header_t*)((const uint8_t*)header + header->header_size);

  status = xbin_fit_in_memory(p, rwmem, rwmem_size, &map);
  TSH_CHECK_OK(status);

  // Copy initialized data from RO to RW segment
  const uint8_t* src = map_va(&map, p->rw_init_va);
  TSH_CHECK(src != NULL, TS_EINVAL);
  void* dst = map_va(&map, p->rw_va);
  TSH_CHECK(dst != NULL, TS_EINVAL);
  memcpy(dst, src, p->rw_init_size);

  // Apply relocations
  status = xbin_apply_relocations(p, &map);
  TSH_CHECK_OK(status);

  // Get stack address and size
  uint32_t stack_base = (uint32_t)map_va(&map, p->stack_va);
  uint32_t stack_size = p->stack_size;
  TSH_CHECK(stack_base != 0 && stack_size > 0, TS_EINVAL);

  // Get entrypoint address
  void* entrypoint = map_va(&map, p->entry_va);
  TSH_CHECK(entrypoint != NULL, TS_EINVAL);

  // Initialize applet privileges
  applet_privileges_t privileges = {0};

  // Get static base address
  uint32_t sb_addr = map.rw_p_addr;

  applet_init(applet, &privileges, xbin_unload_cb);

  applet->layout = (applet_layout_t){
      .code1.start = map.ro_p_addr,
      .code1.size = map.ro_size,
      .data1.start = map.rw_p_addr,
      .data1.size = map.rw_size,
      .code2 = coreapp_get_code_area(),  // app needs access to coreapp code
      .tls = coreapp_get_tls_area(),     // app needs access to coreapp TLS
  };

  // Enable access to applet memory regions
  mpu_set_active_applet(&applet->layout);

  // Initialize the applet task
  bool ok =
      systask_init(&applet->task, stack_base, stack_size, sb_addr, applet);
  TSH_CHECK(ok, TS_ENOMEM);

  // Enable coreapp TLS area swapping
  systask_enable_tls(&applet->task, coreapp_get_tls_area());

  uint32_t api_getter = (uint32_t)coreapp_get_api_getter();

  // Prepare the applet to run - push exception frame on the stack
  // with the entrypoint address
  ok = systask_push_call(&applet->task, entrypoint, api_getter, 0, 0);
  TSH_CHECK(ok, TS_ENOMEM);

cleanup:
  systask_set_mpu(systask_active());
  TSH_RETURN;
}

#endif  // KERNEL_MODE
