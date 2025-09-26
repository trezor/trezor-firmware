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

#pragma GCC optimize("O0")

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/applet.h>
#include <sys/coreapp.h>
#include <sys/dbg_console.h>
#include <sys/mpu.h>
#include <util/image.h>

#include "elf.h"

#define GCC_PIC_SUPPORT
#define CLANG_RWPI_SUPPORT

typedef struct {
  size_t elf_size;

  const Elf32_Ehdr* ehdr;
  const Elf32_Phdr* ro_phdr;
  const Elf32_Phdr* rw_phdr;
  const Elf32_Phdr* dyn_phdr;

  applet_layout_t layout;

} elf_ctx_t;

const Elf32_Ehdr* elf_read_header(const void* elf, size_t elf_size) {
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

  if (ehdr->e_type != ET_EXEC && ehdr->e_type != ET_DYN) {
    // GCC PIC => ET_DYN
    // CLANG ROPI/RWPI => ET_EXEC
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

  // !@# ABI Version??

  return ehdr;
}

const Elf32_Phdr* elf_get_phdr(const Elf32_Ehdr* ehdr, uint32_t index) {
  if (index >= ehdr->e_phnum) {
    return NULL;
  }
  return (Elf32_Phdr*)((uintptr_t)ehdr + ehdr->e_phoff +
                       index * ehdr->e_phentsize);
}

const Elf32_Shdr* elf_get_shdr(const Elf32_Ehdr* ehdr, uint32_t index) {
  if (index >= ehdr->e_shnum) {
    return NULL;
  }
  return (Elf32_Shdr*)((uintptr_t)ehdr + ehdr->e_shoff +
                       index * ehdr->e_shentsize);
}

#define IS_RW_SEGMENT(phdr)     \
  ((phdr)->p_type == PT_LOAD && \
   ((phdr)->p_flags & (PF_R | PF_W)) == (PF_R | PF_W))

#define IS_RO_SEGMENT(phdr)     \
  ((phdr)->p_type == PT_LOAD && \
   ((phdr)->p_flags & (PF_R | PF_X)) == (PF_R | PF_X))

#define IS_DYN_SEGMENT(phdr) ((phdr)->p_type == PT_DYNAMIC)

#define IS_IN_FILE_LIMIT(phdr, elf_size)              \
  ((phdr)->p_offset < elf_size &&                     \
   (phdr)->p_offset + (phdr)->p_filesz <= elf_size && \
   (phdr)->p_filesz <= (phdr)->p_memsz)

uint32_t elf_get_dyn_value(const elf_ctx_t* elf, uint32_t tag) {
  const Elf32_Dyn* dyn =
      (const Elf32_Dyn*)((uintptr_t)elf->ehdr + elf->dyn_phdr->p_offset);
  const Elf32_Dyn* end = dyn + elf->dyn_phdr->p_filesz / sizeof(Elf32_Dyn);
  while (dyn < end && dyn->d_tag != DT_NULL) {
    if (dyn->d_tag == tag) {
      return dyn->d_un.d_val;
    }
    dyn++;
  }
  return 0;
}

const char* elf_get_shdr_name(const elf_ctx_t* elf, const Elf32_Shdr* shdr) {
  const Elf32_Shdr* shstrtab = elf_get_shdr(elf->ehdr, elf->ehdr->e_shstrndx);

  const char* strings = (const char*)elf->ehdr + shstrtab->sh_offset;

  // !@# check string size

  if (shdr->sh_name < shstrtab->sh_size) {
    return strings + shdr->sh_name;
  }

  return NULL;
}

Elf32_Addr map_va(elf_ctx_t* elf, Elf32_Addr va) {
  if (va >= elf->ro_phdr->p_vaddr &&
      va <= elf->ro_phdr->p_vaddr + elf->ro_phdr->p_memsz) {
    return elf->layout.code1.start + (va - elf->ro_phdr->p_vaddr);
  } else if (va >= elf->rw_phdr->p_vaddr &&
             va <= elf->rw_phdr->p_vaddr + elf->rw_phdr->p_memsz) {
    return elf->layout.data1.start + (va - elf->rw_phdr->p_vaddr);
  }
  return 0;
}

bool elf_load(const void* elf_ptr, size_t elf_size, void* ram_ptr,
              size_t ram_size, applet_t* applet) {
  elf_ctx_t elf = {0};

  applet_layout_t temp_layout = {
      .code1 = {.start = APPCODE_START, .size = APPCODE_MAXSIZE},
      .data1 = {.start = APPDATA_RAM_START, .size = APPDATA_RAM_SIZE},
  };

  mpu_set_active_applet(&temp_layout);

  elf.ehdr = elf_read_header(elf_ptr, elf_size);
  if (elf.ehdr == NULL) {
    dbg_printf("Invalid ELF header\n");
    return false;
  }

  // Check program headers
  for (int i = 0; i < elf.ehdr->e_phnum; i++) {
    const Elf32_Phdr* phdr = elf_get_phdr(elf.ehdr, i);
    if (IS_RO_SEGMENT(phdr)) {
      if (elf.ro_phdr != NULL || !IS_IN_FILE_LIMIT(phdr, elf_size)) {
        return false;
      }
      elf.ro_phdr = phdr;
    } else if (IS_RW_SEGMENT(phdr)) {
      if (elf.rw_phdr != NULL || !IS_IN_FILE_LIMIT(phdr, elf_size)) {
        return false;
      }
      elf.rw_phdr = phdr;
    } else if (IS_DYN_SEGMENT(phdr)) {
      if (elf.dyn_phdr != NULL || !IS_IN_FILE_LIMIT(phdr, elf_size)) {
        return false;
      }
      elf.dyn_phdr = phdr;
    }
  }

  // Check if all required segments are present
  // (elf.dyn_phdr required only from GCC PIC)
  if (elf.ro_phdr == NULL || elf.rw_phdr == NULL /*|| elf.dyn_phdr == NULL*/) {
    return false;
  }

  // Check if RW segment fits available RAM
  if (elf.rw_phdr->p_memsz > ram_size) {
    dbg_printf("RW segment too large for RAM\n");
    return false;
  }

  elf.layout.code1.start = (uintptr_t)elf.ehdr + elf.ro_phdr->p_offset;
  elf.layout.code1.size = ALIGN_UP(elf.ro_phdr->p_filesz, 8192);  //!@# const
  elf.layout.data1.start = (uintptr_t)ram_ptr;
  elf.layout.data1.size = ALIGN_UP(elf.rw_phdr->p_memsz, 512);  // !@# const
  elf.layout.code2 = coreapp_get_code_area();
  elf.layout.tls = coreapp_get_tls_area();

  // !@# rw alignment check
  // !@# ro segment memsz check

  uint32_t sb_addr = 0;
  uint32_t stack_base = 0;
  uint32_t stack_size = 0;
  uint32_t entrypoint = map_va(&elf, elf.ehdr->e_entry);
  // !@# check entrypoint
#ifdef CLANG_RWPI_SUPPORT
  uint32_t rel_data = 0;
  uint32_t rel_data_size = 0;
#endif

  // Go through section headers - search for .got and .stack
  for (int i = 0; i < elf.ehdr->e_shnum; i++) {
    const Elf32_Shdr* shdr = elf_get_shdr(elf.ehdr, i);
    const char* section_name = elf_get_shdr_name(&elf, shdr);
    if (section_name != NULL) {
      if (strcmp(section_name, ".got") == 0) {
        sb_addr = map_va(&elf, shdr->sh_addr);

      } else if (strcmp(section_name, ".stack") == 0) {
        stack_base = map_va(&elf, shdr->sh_addr);
        stack_size = shdr->sh_size;
      }
#ifdef CLANG_RWPI_SUPPORT
      else if (strcmp(section_name, ".rel.data") == 0) {
        rel_data = (uint32_t)elf.ehdr + shdr->sh_offset;
        rel_data_size = shdr->sh_size;
      }
#endif
    }
  }

  if (sb_addr == 0) {
    sb_addr = (uintptr_t)ram_ptr;
  }

  applet_privileges_t app_privileges = {0};

  applet_init(applet, &elf.layout, &app_privileges);

  // Initialize RW segment
  memset((void*)elf.layout.data1.start, 0, elf.rw_phdr->p_memsz);
  memcpy((void*)elf.layout.data1.start,
         (const uint8_t*)elf_ptr + elf.rw_phdr->p_offset,
         elf.rw_phdr->p_filesz);

  Elf32_Rel* rel = NULL;
  Elf32_Rel* rel_end = NULL;

#ifdef GCC_PIC_SUPPORT
  if (elf.dyn_phdr != NULL) {
    // Get relocation info
    uint32_t relsz = elf_get_dyn_value(&elf, DT_RELSZ);
    if (relsz > 0) {
      Elf32_Addr relva = elf_get_dyn_value(&elf, DT_REL);
      uint32_t relent = elf_get_dyn_value(&elf, DT_RELENT);

      if (relent != sizeof(Elf32_Rel)) {
        // Unexpected relocation entry size
        return false;
      }

      rel = (Elf32_Rel*)(map_va(&elf, relva));
      rel_end = rel + relsz / sizeof(Elf32_Rel);

      // !@# check rel_end

      if (rel == NULL) {
        // Relocation table is outside of mapped segments
        return false;
      }
    }
  }
#endif

#ifdef CLANG_RWPI_SUPPORT
  if (rel == NULL) {
    rel = (Elf32_Rel*)rel_data;
    rel_end = (Elf32_Rel*)(rel_data + rel_data_size);
  }
#endif

  while (rel < rel_end) {
    if (ELF32_R_TYPE(rel->r_info) != R_ARM_ABS32 &&
        rel->r_info != R_ARM_RELATIVE) {
      // Unsupported relocation type
      return false;
    }
    // Get pointer to the relocated 32-bit word
    uint32_t* mem_ptr = (uint32_t*)map_va(&elf, rel->r_offset);
    if (mem_ptr == NULL) {
      // !@# check that P is RW area
      return false;
    }
    // Relocate the 32-bit word
    *mem_ptr = map_va(&elf, *mem_ptr);

    ++rel;
  }

  mpu_set_active_applet(&applet->layout);

  if (!systask_init(&applet->task, stack_base, stack_size, sb_addr, applet)) {
    return false;
  }

  systask_enable_tls(&applet->task, coreapp_get_tls_area());

  return systask_push_call(&applet->task, (void*)entrypoint, 0, 0, 0);
}

extern uint32_t _kernel_flash_end;
#define COREAPP_START COREAPP_CODE_ALIGN((uint32_t) & _kernel_flash_end)
#define COREAPP_END (FIRMWARE_START + FIRMWARE_MAXSIZE)

void elf_test(void) {
  static applet_t applet;

  if (!elf_load((const void*)APPCODE_START, APPCODE_MAXSIZE,
                (void*)APPDATA_RAM_START, APPDATA_RAM_SIZE, &applet)) {
    dbg_printf("Failed to load ELF\n");
    return;
  }

  // Test the ELF applet
  applet_run(&applet);
}

#endif  // KERNEL_MODE
