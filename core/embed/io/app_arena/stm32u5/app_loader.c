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
#include <sys/logging.h>
#include <sys/mpu.h>

#include "../app_loader.h"

LOG_DECLARE(app_loader)

#define MPU_ALIGNMENT 32   // Required alignment for MPU regions
#define STACK_ALIGNMENT 8  // Required alignment for stack end

// RO segment has been relocated to RW segment
#define RUNTIME_FLAG_RO_SEGMENT_RELOCATED (1 << 0)

typedef struct {
  // Header version. Currently only 0 is supported
  uint32_t version;
  // Offset of the read-only segment from the end of the header
  uint32_t ro_offset;
  // Virtual address of the read-only segment
  uint32_t ro_va;
  // Size of the read-only segment
  uint32_t ro_size;
  // Offset of the relocation table
  uint32_t ro_rel_offset;
  // Size of the relocation table in bytes
  // Each relocation is a 4-byte virtual address in the app image
  uint32_t ro_rel_size;
  // Virtual address of the read-write segment
  uint32_t rw_va;
  // Read-write segment size to reserve at load time
  uint32_t rw_size;
  // Offset of the relocation table for the RW segment
  uint32_t rw_rel_offset;
  // Size of the relocation table for the RW segment in bytes
  uint32_t rw_rel_size;
  // Offset of the RW init data
  uint32_t rw_init_offset;
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
  // Flags for future use
  uint32_t runtime_flags;
  // Reserved for future use
  uint32_t reserved[15];
} app_payload_header_t;

_Static_assert(sizeof(app_payload_header_t) == 128,
               "app_payload_header_t must be 128 bytes");

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

static const uint8_t* offset_to_ptr(const app_payload_header_t* p,
                                    uint32_t offset) {
  return (const uint8_t*)p + sizeof(app_payload_header_t) + offset;
}

static uint8_t* map_va_size(const va_map_t* map, uint32_t va, size_t size) {
  if (va + size < va) {
    // Overflow
    return NULL;
  }

  if (va >= map->rw_v_addr && va + size <= map->rw_v_addr + map->rw_size) {
    // Address within RW segment
    return (uint8_t*)map->rw_p_addr + (va - map->rw_v_addr);
  }

  if (va >= map->ro_v_addr && va + size <= map->ro_v_addr + map->ro_size) {
    // Address within RO segment
    return (uint8_t*)map->ro_p_addr + (va - map->ro_v_addr);
  }

  // Address not within any mapped segment
  return NULL;
}

static uint8_t* map_va(const va_map_t* map, uint32_t va) {
  return map_va_size(map, va, 0);
}

ts_t app_loader_verify_payload(const app_header_t* header, const void* payload,
                               size_t payload_size) {
  TSH_DECLARE;

  TSH_CHECK_ARG(header != NULL);
  TSH_CHECK_ARG(payload != NULL);
  TSH_CHECK_ARG(payload_size >= sizeof(app_payload_header_t));

  TSH_CHECK(payload_size == header->payload_size, TS_EBADMSG);

  TSH_CHECK(header->payload_type == APP_TARGET_ARMV8M, TS_EBADMSG);

  const app_payload_header_t* p = (const app_payload_header_t*)payload;

  uint32_t raw_data_size = header->payload_size - sizeof(app_payload_header_t);

  TSH_CHECK(p->version == 0, TS_EBADMSG);

  // Check that ro segment size and relocations fit within the image
  TSH_CHECK(p->ro_offset <= raw_data_size, TS_EBADMSG);
  TSH_CHECK(p->ro_offset + p->ro_size >= p->ro_offset, TS_EBADMSG);
  TSH_CHECK(p->ro_offset + p->ro_size <= raw_data_size, TS_EBADMSG);
  TSH_CHECK(p->ro_va + p->ro_size >= p->ro_va, TS_EBADMSG);

  // Check that relocation table fits within the image
  TSH_CHECK(p->ro_rel_offset <= raw_data_size, TS_EBADMSG);
  TSH_CHECK(p->ro_rel_offset + p->ro_rel_size >= p->ro_rel_offset, TS_EBADMSG);
  TSH_CHECK(p->ro_rel_size + p->ro_rel_offset <= raw_data_size, TS_EBADMSG);

  // Check that RW segment size and address are valid
  TSH_CHECK(p->rw_va >= p->ro_va + p->ro_size, TS_EBADMSG);
  TSH_CHECK(p->rw_va + p->rw_size >= p->rw_va, TS_EBADMSG);
  TSH_CHECK(p->rw_size < APPDATA_RAM_SIZE, TS_ENOMEM);

  /// Check that RW relocation table fits within the image
  TSH_CHECK(p->rw_rel_offset <= raw_data_size, TS_EBADMSG);
  TSH_CHECK(p->rw_rel_offset + p->rw_rel_size >= p->rw_rel_offset, TS_EBADMSG);
  TSH_CHECK(p->rw_rel_offset + p->rw_rel_size <= raw_data_size, TS_EBADMSG);

  // Check that the RW init data is within the RO segment
  TSH_CHECK(p->rw_init_offset <= raw_data_size, TS_EBADMSG);
  TSH_CHECK(p->rw_init_offset + p->rw_init_size >= p->rw_init_offset,
            TS_EBADMSG);
  TSH_CHECK(p->rw_init_offset + p->rw_init_size <= raw_data_size, TS_EBADMSG);

  // Check that the stack size is within rw_data
  TSH_CHECK(p->stack_va + p->stack_size >= p->stack_va, TS_EBADMSG);
  TSH_CHECK(p->stack_va >= p->rw_va, TS_EBADMSG);
  TSH_CHECK(p->stack_va + p->stack_size <= p->rw_va + p->rw_size, TS_EBADMSG);

  // Check that the heap size is reasonable
  TSH_CHECK(p->heap_size < APPDATA_RAM_SIZE, TS_ENOMEM);

  // Check that the entrypoint is within the RO segment
  TSH_CHECK(p->entry_va < p->ro_va + p->ro_size, TS_EBADMSG);

cleanup:
  TSH_RETURN;
}

static ts_t align_rwmem(void** rwmem, size_t* rwmem_size) {
  TSH_DECLARE;

  uintptr_t addr = (uintptr_t)(*rwmem);
  size_t size = *rwmem_size;

  uintptr_t aligned_addr = ALIGN_UP(addr, MPU_ALIGNMENT);
  size_t offset = aligned_addr - addr;

  TSH_CHECK(size >= offset, TS_ENOMEM);

  *rwmem = (void*)aligned_addr;
  *rwmem_size = ALIGN_DOWN(size - offset, MPU_ALIGNMENT);

cleanup:
  TSH_RETURN;
}

static ts_t fit_in_memory(const app_payload_header_t* p, void* rwmem,
                          size_t rwmem_size, va_map_t* map) {
  TSH_DECLARE;
  ts_t status;

  status = align_rwmem(&rwmem, &rwmem_size);
  TSH_CHECK_OK(status);

  TSH_CHECK(rwmem_size >= p->rw_size /*+ p->stack_size*/ + p->heap_size, TS_ENOMEM);

  map->ro_v_addr = p->ro_va;
  map->ro_p_addr = (uint32_t)offset_to_ptr(p, p->ro_offset);
  map->ro_size = p->ro_size;

  TSH_CHECK(IS_ALIGNED(map->ro_p_addr, MPU_ALIGNMENT), TS_EBADMSG);
  TSH_CHECK(IS_ALIGNED(map->ro_size, MPU_ALIGNMENT), TS_EBADMSG);

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
static void unload_cb(applet_t* applet) {
  mpu_set_active_applet(&applet->layout);

  // Clear RW segment, stack and the heap to remove any sensitive information
  // before freeing the memory

  void* rwmem = (void*)applet->layout.data1.start;
  size_t rwmem_size = applet->layout.data1.size;
  memset(rwmem, 0, rwmem_size);

  systask_set_mpu(systask_active());
}

// 16-bit Relocation format
// -----------------------------------------------------------------------
// | 15 | 14 | 13 | 12 | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
// |        type       |              value                              |
// -----------------------------------------------------------------------
// s (segment)
//  0 => target is read-only segment
//  1 => target is read-write segment
// type
//   0 => reset address to 0
//   1 => skip `value` bytes
//   2 => skip (`value` << 16) + (next 16-bit value)
//   3 => R_ARM_ABS32
//   4 => R_ARM_THM_MOVT_ABS
//   5 => R_ARM_THM_MOVW_ABS_NC
//   6 => R_ARM_THM_MOVT_PREL
//   7 => R_ARM_THM_MOVW_PREL_NC
// offset = 11 bits
//  difference between the relocation address and the last relocation address + 1

typedef enum {
  REL_TYPE_RESET = 0,
  REL_TYPE_SKIP = 1,
  REL_TYPE_SKIP_LONG = 2,
  REL_TYPE_ABS32 = 3,
  REL_TYPE_MOVT_ABS = 4,
  REL_TYPE_MOVW_ABS = 5,
  REL_TYPE_MOVT_PREL = 6,
  REL_TYPE_MOVW_PREL = 7
} reloc_type_t;

// Extract the immediate value from a MOVT or MOVW instructions
static uint16_t extract_movx_value(uint32_t instruction) {
  uint16_t imm1 = (instruction >> 10) & 0x1;      
  uint16_t imm4 = (instruction >> 0) & 0xF;
  uint16_t imm3 = (instruction >> 28) & 0x7;
  uint16_t imm8 = (instruction >> 16) & 0xFF;
  return (imm4 << 12) | (imm1 << 11) | (imm3 << 8) | imm8;
}

// Insert the immediate value into a MOVT or MOVW instruction
static uint32_t insert_movx_value(uint32_t instruction, uint16_t value) {
  uint16_t imm4 = (value >> 12) & 0xF;
  uint16_t imm1 = (value >> 11) & 0x1;
  uint16_t imm3 = (value >> 8) & 0x7;
  uint16_t imm8 = value & 0xFF;
  instruction = (instruction & ~0x000F) | (imm4 << 0);
  instruction = (instruction & ~0x0400) | (imm1 << 10);
  instruction = (instruction & ~0x70000000) | (imm3 << 28);
  instruction = (instruction & ~0x00FF0000) | (imm8 << 16);
  return instruction; 
}
  

ts_t apply_relocations(const void* rel_table, size_t rel_size,
                              const va_map_t* map) {
  TSH_DECLARE;

  TSH_CHECK(rel_size % sizeof(uint16_t) == 0, TS_EBADMSG);

  const uint16_t* rel_ptr = (uint16_t*)rel_table;
  const uint16_t* rel_end = rel_ptr + (rel_size / sizeof(uint16_t));

  uint32_t address = 0;

  while (rel_ptr < rel_end) {
    uint16_t entry = *rel_ptr++;

    reloc_type_t type = (entry >> 12) & 0xF;
    uint16_t value = entry & ((1 << 12) - 1);

    // Handle address adjustments commands
    switch (type) {
      case REL_TYPE_RESET:
        address = 0;
        continue;

      case REL_TYPE_SKIP:
        address += value;
        continue;

      case REL_TYPE_SKIP_LONG:
        TSH_CHECK(rel_ptr < rel_end, TS_EBADMSG);
        uint16_t low = *rel_ptr++;
        address += (value << 16) + low;
        continue;

      default:
        break;
    }

    // Handle relocation commands
    address += value;

    uint32_t* ptr = (uint32_t*) map_va_size(map, address, sizeof(uint32_t));
    TSH_CHECK(ptr != NULL, TS_EBADMSG);

    switch (type) {
      case REL_TYPE_ABS32: {
        uint32_t pa = (uint32_t)map_va(map, *ptr);
        LOG_DBG("0x%08lX: ABS32: 0x%08lX -> 0x%08lX", address, *ptr, pa);
        TSH_CHECK(pa != 0, TS_EBADMSG);
        *ptr = pa;
      } break;

      case REL_TYPE_MOVT_ABS: {
        TSH_CHECK(rel_ptr < rel_end, TS_EBADMSG);
        uint16_t low = *rel_ptr++;
        uint32_t va = (extract_movx_value(*ptr) << 16) | low;
        uint32_t pa = (uint32_t)map_va(map, va);
        LOG_DBG("0x%08lX: MOVT_ABS: 0x%08lX -> 0x%08lX", address, va, pa);
        TSH_CHECK(pa != 0, TS_EBADMSG);
        *ptr = insert_movx_value(*ptr, (uint16_t)(pa >> 16));
      } break;

      case REL_TYPE_MOVW_ABS: {
        TSH_CHECK(rel_ptr < rel_end, TS_EBADMSG);
        uint16_t high = *rel_ptr++;
        uint32_t va = extract_movx_value(*ptr) | (high << 16);
        uint32_t pa = (uint32_t)map_va(map, va);
        LOG_DBG("0x%08lX: MOVW_ABS: 0x%08lX -> 0x%08lX", address, va, pa);
        TSH_CHECK(pa != 0, TS_EBADMSG);
        *ptr = insert_movx_value(*ptr, (uint16_t)(pa & 0xFFFF));
      } break;

      case REL_TYPE_MOVT_PREL:
        LOG_DBG("0x%08lX: MOVT_PREL", address);
        TSH_RAISE(TS_EBADMSG);
        break;

      case REL_TYPE_MOVW_PREL:
        LOG_DBG("0x%08lX: MOVW_PREL", address);
        TSH_RAISE(TS_EBADMSG);
        break;

      default:
        TSH_CHECK(false, TS_EBADMSG);
    }
  }

cleanup:
  TSH_RETURN;
}


ts_t app_loader_prepare_applet(const app_header_t* header, void* payload,
                               void* rwmem, size_t rwmem_size,
                               applet_t* applet) {
  TSH_DECLARE;
  ts_t status;

  va_map_t map = {0};

  app_payload_header_t* p = (app_payload_header_t*)payload;

  memset(rwmem, 0, rwmem_size);

  status = fit_in_memory(p, rwmem, rwmem_size, &map);
  TSH_CHECK_OK(status);

  // Apply relocations
  if ((p->runtime_flags & RUNTIME_FLAG_RO_SEGMENT_RELOCATED) == 0) {
    status = apply_relocations(offset_to_ptr(p, p->ro_rel_offset),
                               p->ro_rel_size, &map);
    TSH_CHECK_OK(status);
    p->runtime_flags |= RUNTIME_FLAG_RO_SEGMENT_RELOCATED;
  }

  // Copy initialized data from RO to RW segment
  if (p->rw_init_size > 0) {
    const uint8_t* src = offset_to_ptr(p, p->rw_init_offset);
    void* dst = map_va(&map, p->rw_va);
    TSH_CHECK(dst != NULL, TS_EBADMSG);
    memcpy(dst, src, p->rw_init_size);
  }

  // Apply relocations for RW segment
  status = apply_relocations(offset_to_ptr(p, p->rw_rel_offset), p->rw_rel_size,
                             &map);
  TSH_CHECK_OK(status);

  // Get stack address and size
  uint32_t stack_base = (uint32_t)map_va(&map, p->stack_va);
  uint32_t stack_size = p->stack_size;
  TSH_CHECK(stack_base != 0 && stack_size > 0, TS_EBADMSG);

  // Get entrypoint address
  void* entrypoint = map_va(&map, p->entry_va);
  TSH_CHECK(entrypoint != NULL, TS_EBADMSG);

  // Initialize applet privileges
  applet_privileges_t privileges = {0};

  // Get static base address
  uint32_t sb_addr = map.rw_p_addr;

  applet_init(applet, &privileges, unload_cb);

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

  // LOG_DBG("add-symbol-file <elf> 0x%08lX -s .rodata 0x%08lX -s .bss 0x%08lX -s .data 0x%08lX", (uint32_t)map.ro_p_addr, ...);

cleanup:
  systask_set_mpu(systask_active());
  TSH_RETURN;
}

#endif  // KERNEL_MODE
