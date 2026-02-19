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

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <rtl/sizedefs.h>
#include <sys/irq.h>
#include <sys/trustzone.h>

static void set_bit_array(volatile uint32_t* regs, uint32_t bit_offset,
                          uint32_t bit_count, bool value) {
  regs += bit_offset / 32;
  bit_offset %= 32;

  if (bit_offset != 0) {
    uint32_t bc = MIN(32 - bit_offset, bit_count);
    uint32_t mask = (1 << bc) - 1;

    mask <<= bit_offset;

    if (value) {
      *regs |= mask;
    } else {
      *regs &= ~mask;
    }

    regs++;
    bit_count -= bc;
  }

  while (bit_count >= 32) {
    *regs = value ? 0xFFFFFFFF : 0;
    regs++;
    bit_count -= 32;
  }

  if (bit_count > 0) {
    uint32_t mask = (1 << bit_count) - 1;
    if (value) {
      *regs |= mask;
    } else {
      *regs &= ~mask;
    }
  }
}

typedef struct {
  // Start address of the region
  uint32_t start;
  // End address of the region + 1
  size_t end;
  // MPCBB register base
  volatile GTZC_MPCBB_TypeDef* regs;
} sram_region_t;

// SRAM regions must be in order of ascending start address
// and must not overlap
sram_region_t g_sram_regions[] = {
    {SRAM1_BASE, SRAM1_BASE + SRAM1_SIZE, GTZC_MPCBB1},
    {SRAM2_BASE, SRAM2_BASE + SRAM2_SIZE, GTZC_MPCBB2},

};

void tz_set_sram_unpriv(uint32_t start, uint32_t size, bool unpriv) {
  const size_t block_size = TZ_SRAM_ALIGNMENT;

  ensure(sectrue * IS_ALIGNED(start, block_size), "TZ alignment");
  ensure(sectrue * IS_ALIGNED(size, block_size), "TZ alignment");

  uint32_t end = start + size;

  for (int idx = 0; idx < ARRAY_LENGTH(g_sram_regions); idx++) {
    const sram_region_t* r = &g_sram_regions[idx];

    if (start >= r->end) {
      continue;
    }

    if (end <= r->start) {
      break;
    }

    // Clip to region bounds
    uint32_t clipped_start = MAX(start, r->start);
    uint32_t clipped_end = MIN(end, r->end);

    // Calculate bit offsets
    uint32_t bit_offset = (clipped_start - r->start) / block_size;
    uint32_t bit_count = (clipped_end - clipped_start) / block_size;

    // Set/reset bits corresponding to 512B blocks
    set_bit_array(r->regs->PRIVCFGR, bit_offset, bit_count, !unpriv);
  }

  __ISB();
}

void tz_set_sram_unsecure(uint32_t start, uint32_t size, bool unsecure) {
  const size_t block_size = TZ_SRAM_ALIGNMENT;

  ensure(sectrue * IS_ALIGNED(start, block_size), "TZ alignment");
  ensure(sectrue * IS_ALIGNED(size, block_size), "TZ alignment");

  uint32_t end = start + size;

#ifdef SECMON
  // Allow using both secure and non-secure SRAM regions
  if (start >= SRAM1_BASE_NS && end < SRAM1_BASE_S) {
    start += SRAM1_BASE_S - SRAM1_BASE_NS;
    end += SRAM1_BASE_S - SRAM1_BASE_NS;
  }
#endif

  for (int idx = 0; idx < ARRAY_LENGTH(g_sram_regions); idx++) {
    const sram_region_t* r = &g_sram_regions[idx];

    if (start >= r->end) {
      continue;
    }

    if (end <= r->start) {
      break;
    }

    // Clip to region bounds
    uint32_t clipped_start = MAX(start, r->start);
    uint32_t clipped_end = MIN(end, r->end);

    // Calculate bit offsets
    uint32_t bit_offset = (clipped_start - r->start) / block_size;
    uint32_t bit_count = (clipped_end - clipped_start) / block_size;

    // Set/reset bits corresponding to 512B blocks
    set_bit_array(r->regs->SECCFGR, bit_offset, bit_count, !unsecure);
  }

  __ISB();
}

typedef struct {
  // Start address of the region
  uint32_t start;
  // End address of the region + 1
  size_t end;
  // PRIVBB register base
  volatile uint32_t* privbb;
  // SECBB register base
  volatile uint32_t* secbb;
} flash_region_t;

#if defined STM32U5A9xx
#define XFLASH_BANK_SIZE 0x200000
#elif defined STM32U5G9xx
#define XFLASH_BANK_SIZE 0x200000
#elif defined STM32U585xx
#define XFLASH_BANK_SIZE 0x100000
#elif defined STM32U385xx
#define XFLASH_BANK_SIZE 0x80000
#else
#error "Unknown MCU"
#endif

#define FLASH_BANK1_BASE FLASH_BASE
#define FLASH_BANK2_BASE (FLASH_BASE + XFLASH_BANK_SIZE)

// FLASH regions must be in order of ascending start address
// and must not overlap
flash_region_t g_flash_regions[] = {
    {FLASH_BANK1_BASE, FLASH_BANK1_BASE + XFLASH_BANK_SIZE, &FLASH->PRIVBB1R1,
     &FLASH->SECBB1R1},
    {FLASH_BANK2_BASE, FLASH_BANK2_BASE + XFLASH_BANK_SIZE, &FLASH->PRIVBB2R1,
     &FLASH->SECBB2R1},
};

void tz_set_flash_unpriv(uint32_t start, uint32_t size, bool unpriv) {
  const size_t block_size = TZ_FLASH_ALIGNMENT;

  ensure(sectrue * IS_ALIGNED(start, block_size), "TZ alignment");
  ensure(sectrue * IS_ALIGNED(size, block_size), "TZ alignment");

  uint32_t end = start + size;

  for (int idx = 0; idx < ARRAY_LENGTH(g_flash_regions); idx++) {
    const flash_region_t* r = &g_flash_regions[idx];

    if (start >= r->end) {
      continue;
    }

    if (end <= r->start) {
      break;
    }

    // Clip to region bounds
    uint32_t clipped_start = MAX(start, r->start);
    uint32_t clipped_end = MIN(end, r->end);

    // Calculate bit offsets
    uint32_t bit_offset = (clipped_start - r->start) / block_size;
    uint32_t bit_count = (clipped_end - clipped_start) / block_size;

    // Set/reset bits corresponding to flash pages (8KB)
    set_bit_array(r->privbb, bit_offset, bit_count, !unpriv);
  }

  __ISB();
}

void tz_set_flash_unsecure(uint32_t start, uint32_t size, bool unsecure) {
  const size_t block_size = TZ_FLASH_ALIGNMENT;

  ensure(sectrue * IS_ALIGNED(start, block_size), "TZ alignment");
  ensure(sectrue * IS_ALIGNED(size, block_size), "TZ alignment");

  uint32_t end = start + size;

#ifdef SECMON
  // Allow using both secure and non-secure FLASH regions
  if (start >= FLASH_BASE_NS && end < FLASH_BASE_S) {
    start += FLASH_BASE_S - FLASH_BASE_NS;
    end += FLASH_BASE_S - FLASH_BASE_NS;
  }
#endif

  for (int idx = 0; idx < ARRAY_LENGTH(g_flash_regions); idx++) {
    const flash_region_t* r = &g_flash_regions[idx];

    if (start >= r->end) {
      continue;
    }

    if (end <= r->start) {
      break;
    }

    // Clip to region bounds
    uint32_t clipped_start = MAX(start, r->start);
    uint32_t clipped_end = MIN(end, r->end);

    // Calculate bit offsets
    uint32_t bit_offset = (clipped_start - r->start) / block_size;
    uint32_t bit_count = (clipped_end - clipped_start) / block_size;

    // Set/reset bits corresponding to flash pages (8KB)
    set_bit_array(r->secbb, bit_offset, bit_count, !unsecure);
  }

  __ISB();
}

void tz_set_saes_unpriv(bool unpriv) {
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_SAES,
      unpriv ? GTZC_TZSC_PERIPH_NPRIV : GTZC_TZSC_PERIPH_PRIV);
}

void tz_set_tamper_unpriv(bool unpriv) {
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_TAMP,
      unpriv ? GTZC_TZSC_PERIPH_NPRIV : GTZC_TZSC_PERIPH_PRIV);
}

#if defined STM32U5A9xx || defined STM32U5G9xx
void tz_set_gfxmmu_unpriv(bool unpriv) {
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_GFXMMU,
      unpriv ? GTZC_TZSC_PERIPH_NPRIV : GTZC_TZSC_PERIPH_PRIV);
}
#endif

#endif  // KERNEL_MODE
