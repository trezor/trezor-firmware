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

#pragma GCC optimize("O0")

#ifdef KERNEL_MODE

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/applet.h>
#include <sys/coreapp.h>
#include <sys/mpu.h>
#include <util/elf_loader.h>
#include <util/image.h>

#include "../app_arena.h"
#include "elf.h"

// Alignment required for MPU regions
#define MPU_ALIGNMENT 32

static const Elf32_Phdr* elf_get_phdr(const Elf32_Ehdr* ehdr, uint32_t index) {
  if (index >= ehdr->e_phnum) {
    return NULL;
  }
  return (Elf32_Phdr*)((uintptr_t)ehdr + ehdr->e_phoff +
                       index * ehdr->e_phentsize);
}

static const Elf32_Shdr* elf_get_shdr(const Elf32_Ehdr* ehdr, uint32_t index) {
  if (index >= ehdr->e_shnum) {
    return NULL;
  }
  return (Elf32_Shdr*)((uintptr_t)ehdr + ehdr->e_shoff +
                       index * ehdr->e_shentsize);
}

static const Elf32_Ehdr* elf_read_header(const void* elf, size_t elf_size) {
  if (elf_size < sizeof(Elf32_Ehdr)) {
    return NULL;
  }

  const Elf32_Ehdr* ehdr = (const Elf32_Ehdr*)elf;

  if (ehdr->e_ident[EI_MAG0] != ELFMAG0 || ehdr->e_ident[EI_MAG1] != ELFMAG1 ||
      ehdr->e_ident[EI_MAG2] != ELFMAG2 || ehdr->e_ident[EI_MAG3] != ELFMAG3) {
    return NULL;
  }

  if (ehdr->e_ident[EI_CLASS] != ELFCLASS32) {
    return NULL;
  }

  if (ehdr->e_ident[EI_DATA] != ELFDATA2LSB) {
    return NULL;
  }

  if (ehdr->e_ident[EI_VERSION] != EV_CURRENT) {
    return NULL;
  }

  if (ehdr->e_type != ET_EXEC) {
    return NULL;
  }

  if (ehdr->e_machine != EM_ARM) {
    return NULL;
  }

  if (ehdr->e_version != EV_CURRENT) {
    return NULL;
  }

  if (ehdr->e_phoff >= elf_size || ehdr->e_phentsize != sizeof(Elf32_Phdr) ||
      ehdr->e_phnum > 32 ||
      ehdr->e_phoff + ehdr->e_phentsize * ehdr->e_phnum > elf_size) {
    return NULL;
  }

  if (ehdr->e_shoff >= elf_size || ehdr->e_shentsize != sizeof(Elf32_Shdr) ||
      ehdr->e_shnum > 32 ||
      ehdr->e_shoff + ehdr->e_shentsize * ehdr->e_shnum > elf_size) {
    return NULL;
  }

  if (ehdr->e_shstrndx >= ehdr->e_shnum) {
    return NULL;
  }

  if ((ehdr->e_flags & EF_ARM_ABI_FLOAT_HARD) == 0) {
    return NULL;
  }

  // Check all section references part of elf file
  for (int i = 0; i < ehdr->e_shnum; ++i) {
    const Elf32_Shdr* shdr = elf_get_shdr(ehdr, i);
    if (shdr->sh_type != SHT_NOBITS &&
        (shdr->sh_offset >= elf_size ||
         shdr->sh_size > elf_size - shdr->sh_offset)) {
      return NULL;
    }
  }

  return ehdr;
}

#define IS_RW_SEGMENT(phdr)     \
  ((phdr)->p_type == PT_LOAD && \
   ((phdr)->p_flags & (PF_R | PF_W)) == (PF_R | PF_W))

#define IS_RO_SEGMENT(phdr)     \
  ((phdr)->p_type == PT_LOAD && \
   ((phdr)->p_flags & (PF_R | PF_X)) == (PF_R | PF_X))

#define IS_IN_FILE_LIMIT(phdr, elf_size)              \
  ((phdr)->p_offset < elf_size &&                     \
   (phdr)->p_offset + (phdr)->p_filesz <= elf_size && \
   (phdr)->p_filesz <= (phdr)->p_memsz)

static const char* elf_get_shdr_name(const Elf32_Ehdr* ehdr,
                                     const Elf32_Shdr* shdr) {
  const Elf32_Shdr* shstrtab = elf_get_shdr(ehdr, ehdr->e_shstrndx);

  const char* strings = (const char*)ehdr + shstrtab->sh_offset;
  // Ensure the name offset is within bounds
  if (shdr->sh_name >= shstrtab->sh_size) {
    return NULL;
  }

  const char* name = strings + shdr->sh_name;

  // Ensure the name is null-terminated and within bounds
  size_t remaining_bytes = (strings + shstrtab->sh_size) - name;
  if (strnlen(name, remaining_bytes) >= remaining_bytes) {
    return NULL;
  }

  return name;
}

static const Elf32_Phdr* elf_read_rw_phdr(const Elf32_Ehdr* ehdr,
                                          size_t elf_size) {
  const Elf32_Phdr* rw_phdr = NULL;

  // Parse program headers, find RO, RW segments
  for (int i = 0; i < ehdr->e_phnum; i++) {
    const Elf32_Phdr* phdr = elf_get_phdr(ehdr, i);
    if (IS_RW_SEGMENT(phdr)) {
      if (rw_phdr != NULL || !IS_IN_FILE_LIMIT(phdr, elf_size)) {
        // Multiple RW segments or invalid segment
        return NULL;
      }
      rw_phdr = phdr;
    }
  }

  // Check if the RW segment is present
  if (rw_phdr == NULL) {
    return NULL;
  }

  // Check if RO segment size is within elf file
  if (rw_phdr->p_memsz < rw_phdr->p_filesz) {
    return NULL;
  }

  return rw_phdr;
}

static const Elf32_Phdr* elf_read_ro_phdr(const Elf32_Ehdr* ehdr,
                                          size_t elf_size) {
  const Elf32_Phdr* ro_phdr = NULL;

  // Parse program headers, search for RO segment
  for (int i = 0; i < ehdr->e_phnum; i++) {
    const Elf32_Phdr* phdr = elf_get_phdr(ehdr, i);
    if (IS_RO_SEGMENT(phdr)) {
      if (ro_phdr != NULL || !IS_IN_FILE_LIMIT(phdr, elf_size)) {
        // Multiple RO segments or invalid segment
        return NULL;
      }
      ro_phdr = phdr;
    }
  }

  // Check if the RO segment is present
  if (ro_phdr == NULL) {
    return NULL;
  }

  // Check if RO segment size is within elf file
  if (ro_phdr->p_memsz < ro_phdr->p_filesz) {
    return NULL;
  }

  // Check if RO segment is aligned properly
  if (!IS_ALIGNED((uint32_t)ehdr + ro_phdr->p_offset, MPU_ALIGNMENT)) {
    return NULL;
  }

  return ro_phdr;
}

typedef struct {
  uint32_t ro_size;
  uint32_t ro_v_addr;
  uint32_t ro_p_addr;

  uint32_t rw_size;
  uint32_t rw_v_addr;
  uint32_t rw_p_addr;
} va_mapping_t;

static Elf32_Addr map_va(va_mapping_t* map, Elf32_Addr va) {
  if (va >= map->ro_v_addr && va <= map->ro_v_addr + map->ro_size) {
    return map->ro_p_addr + (va - map->ro_v_addr);
  } else if (va >= map->rw_v_addr && va <= map->rw_v_addr + map->rw_size) {
    return map->rw_p_addr + (va - map->rw_v_addr);
  }
  return 0;
}

static bool relocate_section(const Elf32_Ehdr* ehdr, const Elf32_Shdr* shdr,
                             va_mapping_t* map) {
  const Elf32_Rel* rel = (Elf32_Rel*)((uint32_t)ehdr + shdr->sh_offset);
  const Elf32_Rel* rel_end = (Elf32_Rel*)((uint32_t)rel + shdr->sh_size);

  // Get section we are relocating
  const Elf32_Shdr* target_shdr = elf_get_shdr(ehdr, shdr->sh_info);
  if (target_shdr == NULL) {
    return false;
  }

  // Get target section boundaries
  uint32_t target_start = map_va(map, target_shdr->sh_addr);
  uint32_t target_end = target_start + target_shdr->sh_size;

  while (rel < rel_end) {
    if (ELF32_R_TYPE(rel->r_info) != R_ARM_ABS32) {
      // Unsupported relocation type
      return false;
    }

    // Get pointer to the relocated 32-bit word
    uint32_t* mem_ptr = (uint32_t*)map_va(map, rel->r_offset);
    if (mem_ptr == NULL) {
      return false;
    }

    // Ensure the pointer is within the target section
    if ((uint32_t)mem_ptr < target_start ||
        (uint32_t)mem_ptr + 4 > target_end) {
      return false;
    }

    // Relocate the 32-bit word
    *mem_ptr = map_va(map, *mem_ptr);

    ++rel;
  }

  return true;
}

static void get_stack_info(const Elf32_Ehdr* ehdr, uint32_t* stack_base,
                           uint32_t* stack_size) {
  for (int i = 0; i < ehdr->e_shnum; i++) {
    const Elf32_Shdr* shdr = elf_get_shdr(ehdr, i);
    const char* section_name = elf_get_shdr_name(ehdr, shdr);
    if (section_name != NULL && strcmp(section_name, ".stack") == 0) {
      *stack_base = shdr->sh_addr;
      *stack_size = shdr->sh_size;
      break;
    }
  }
}

static void elf_unload_cb(applet_t* applet) {
  void* ram_start = (void*)applet->layout.data1.start;
  size_t ram_size = applet->layout.data1.size;

  if (ram_start != NULL && ram_size > 0) {
    // Clear applet data segment
    mpu_set_active_applet(&applet->layout);
    memset(ram_start, 0, ram_size);

    systask_t* active_task = systask_active();
    if (active_task->applet != NULL) {
      applet_t* active_applet = (applet_t*)active_task->applet;
      mpu_set_active_applet(&active_applet->layout);
    }

    // Free applet RAM
    app_arena_free(ram_start);
  }
}

bool elf_load(applet_t* applet, const void* elf_ptr, size_t elf_size) {
  bool retval = false;

  applet_init(applet, NULL, NULL);

  // Make sure the entire ELF file is accessible
  // (temporarily map it as data)
  const applet_layout_t temp_layout_1 = {
      .data1 = {.start = (uintptr_t)elf_ptr, .size = elf_size},
  };
  mpu_set_active_applet(&temp_layout_1);

  // Read and validate ELF header
  const Elf32_Ehdr* ehdr = elf_read_header(elf_ptr, elf_size);
  if (ehdr == NULL) {
    goto cleanup;
  }

  // Read and validate RO segment
  const Elf32_Phdr* ro_phdr = elf_read_ro_phdr(ehdr, elf_size);
  if (ro_phdr == NULL) {
    goto cleanup;
  }

  // Read and validate RW segment
  const Elf32_Phdr* rw_phdr = elf_read_rw_phdr(ehdr, elf_size);
  if (rw_phdr == NULL) {
    goto cleanup;
  }

  // Allocate RAM for RW segment
  size_t ram_size = ALIGN_UP(rw_phdr->p_memsz, MPU_ALIGNMENT);
  void* ram_ptr = app_arena_alloc(ram_size, APP_ALLOC_DATA);
  if (ram_ptr == NULL) {
    goto cleanup;
  }

  // Make sure ELF and allocated RAM are accessible
  // (temporarily map it as data => we can apply relocation fixups)
  const applet_layout_t temp_layout_2 = {
      .data1 = {.start = (uintptr_t)elf_ptr, .size = elf_size},
      .data2 = {.start = (uintptr_t)ram_ptr, .size = ram_size},
  };
  mpu_set_active_applet(&temp_layout_2);

  // Clear the allocated RAM
  memset(ram_ptr, 0, ram_size);

  // Copy initialized data
  memcpy(ram_ptr, (uint8_t*)elf_ptr + rw_phdr->p_offset, rw_phdr->p_filesz);

  // Prepare VA -> PA mapping
  va_mapping_t map = {
      .ro_size = ro_phdr->p_memsz,
      .ro_v_addr = ro_phdr->p_vaddr,
      .ro_p_addr = (uintptr_t)elf_ptr + ro_phdr->p_offset,
      .rw_size = rw_phdr->p_memsz,
      .rw_v_addr = rw_phdr->p_vaddr,
      .rw_p_addr = (uintptr_t)ram_ptr,
  };

  // Apply relocation fixups
  for (int i = 0; i < ehdr->e_shnum; i++) {
    const Elf32_Shdr* shdr = elf_get_shdr(ehdr, i);
    if (shdr->sh_type == SHT_REL) {
      if (!relocate_section(ehdr, shdr, &map)) {
        goto cleanup;
      }
    }
  }

  // Get stack address and size
  uint32_t stack_base = 0;
  uint32_t stack_size = 0;
  get_stack_info(ehdr, &stack_base, &stack_size);
  stack_base = map_va(&map, stack_base);
  if (stack_base == 0 || stack_size == 0) {
    goto cleanup;
  }

  // Get static base address
  uint32_t sb_addr = (uintptr_t)ram_ptr;

  // Get entrypoint address
  uint32_t entrypoint = map_va(&map, ehdr->e_entry);

  // Initialize applet privileges
  applet_privileges_t app_privileges = {0};

  applet_init(applet, &app_privileges, elf_unload_cb);

  applet->layout = (applet_layout_t){
      .code1.start = (uintptr_t)ehdr + ro_phdr->p_offset,
      .code1.size = ro_phdr->p_memsz,
      .data1.start = (uintptr_t)ram_ptr,
      .data1.size = ram_size,
      .code2 = coreapp_get_code_area(),  // app needs access to coreapp code
      .tls = coreapp_get_tls_area(),     // app needs access to coreapp TLS
  };

  ram_ptr = NULL;  // ownership transferred to applet

  // Enable access to applet memory regions
  mpu_set_active_applet(&applet->layout);

  // Initialize the applet task
  if (!systask_init(&applet->task, stack_base, stack_size, sb_addr, applet)) {
    goto cleanup;
  }

  // Enable coreapp TLS area swapping
  systask_enable_tls(&applet->task, coreapp_get_tls_area());

  uint32_t api_getter = (uint32_t)coreapp_get_api_getter();

  // Prepare the applet to run - push exception frame on the stack
  // with the entrypoint address
  if (!systask_push_call(&applet->task, (void*)entrypoint, api_getter, 0, 0)) {
    goto cleanup;
  }

  retval = true;

cleanup:

  if (ram_ptr != NULL) {
    app_arena_free(ram_ptr);
  }

  if (!retval) {
    applet_unload(applet);
  }

  // Recover MPU state for the active task
  systask_t* active_task = systask_active();
  if (active_task->applet != NULL) {
    applet_t* applet = (applet_t*)active_task->applet;
    mpu_set_active_applet(&applet->layout);
  }

  return retval;
}

#endif  // KERNEL_MODE
