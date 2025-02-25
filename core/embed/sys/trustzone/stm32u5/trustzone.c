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

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <rtl/sizedefs.h>
#include <sys/irq.h>
#include <sys/trustzone.h>
#include <util/image.h>

#define SAU_INIT_CTRL_ENABLE 1
#define SAU_INIT_CTRL_ALLNS 0
#define SAU_INIT_REGION(n, start, end, sec)   \
  SAU->RNR = ((n) & SAU_RNR_REGION_Msk);      \
  SAU->RBAR = ((start) & SAU_RBAR_BADDR_Msk); \
  SAU->RLAR = ((end) & SAU_RLAR_LADDR_Msk) |  \
              (((sec) << SAU_RLAR_NSC_Pos) & SAU_RLAR_NSC_Msk) | 1U

static void tz_configure_sau(void) {
  SAU_INIT_REGION(0, 0x0BF90000, 0x0BFA8FFF, 0);  // OTP etc

  SAU->CTRL =
      ((SAU_INIT_CTRL_ENABLE << SAU_CTRL_ENABLE_Pos) & SAU_CTRL_ENABLE_Msk) |
      ((SAU_INIT_CTRL_ALLNS << SAU_CTRL_ALLNS_Pos) & SAU_CTRL_ALLNS_Msk);
}

// Configure ARMCortex-M33 SCB and FPU security
static void tz_configure_arm(void) {
  // Enable FPU in both secure and non-secure modes
  SCB->NSACR |= SCB_NSACR_CP10_Msk | SCB_NSACR_CP11_Msk;

  // Treat FPU registers as non-secure
  FPU->FPCCR &= ~FPU_FPCCR_TS_Msk;
  // CLRONRET field is accessible from both security states
  FPU->FPCCR &= ~FPU_FPCCR_CLRONRETS_Msk;
  // FPU registers are cleared on exception return
  FPU->FPCCR |= FPU_FPCCR_CLRONRET_Msk;
}

// Configure SRAM security
static void tz_configure_sram(void) {
  MPCBB_ConfigTypeDef mpcbb = {0};

  // No exceptions on illegal access
  mpcbb.SecureRWIllegalMode = GTZC_MPCBB_SRWILADIS_DISABLE;
  // Settings of SRAM clock in RCC is secure
  mpcbb.InvertSecureState = GTZC_MPCBB_INVSECSTATE_NOT_INVERTED;
  // Set configuration as unlocked
  mpcbb.AttributeConfig.MPCBB_LockConfig_array[0] = 0x00000000U;

  // Set all blocks secured & privileged
  for (int index = 0; index < GTZC_MPCBB_NB_VCTR_REG_MAX; index++) {
    mpcbb.AttributeConfig.MPCBB_SecConfig_array[index] = 0xFFFFFFFFU;
    mpcbb.AttributeConfig.MPCBB_PrivConfig_array[index] = 0xFFFFFFFFU;
  }

  HAL_GTZC_MPCBB_ConfigMem(SRAM1_BASE, &mpcbb);
  HAL_GTZC_MPCBB_ConfigMem(SRAM2_BASE, &mpcbb);
  HAL_GTZC_MPCBB_ConfigMem(SRAM3_BASE, &mpcbb);
  HAL_GTZC_MPCBB_ConfigMem(SRAM4_BASE, &mpcbb);
#if defined STM32U5A9xx || defined STM32U5G9xx
  HAL_GTZC_MPCBB_ConfigMem(SRAM5_BASE, &mpcbb);
#endif
#if defined STM32U5G9xx
  HAL_GTZC_MPCBB_ConfigMem(SRAM6_BASE, &mpcbb);
#endif
}

static void tz_configure_fsmc(void) {
  __HAL_RCC_FMC_CLK_ENABLE();
  MPCWM_ConfigTypeDef mpcwm = {0};

  mpcwm.AreaId = GTZC_TZSC_MPCWM_ID1;
  mpcwm.AreaStatus = ENABLE;
  mpcwm.Attribute = GTZC_TZSC_MPCWM_REGION_SEC | GTZC_TZSC_MPCWM_REGION_PRIV;
  mpcwm.Length = 128 * 1024;
  mpcwm.Offset = 0;
  mpcwm.Lock = GTZC_TZSC_MPCWM_LOCK_OFF;
  HAL_GTZC_TZSC_MPCWM_ConfigMemAttributes(FMC_BANK1, &mpcwm);
}

// Configure FLASH security
static void tz_configure_flash(void) {
  FLASH_BBAttributesTypeDef flash_bb = {0};

  // Set all blocks as secured & privileged
  for (int index = 0; index < FLASH_BLOCKBASED_NB_REG; index++) {
    flash_bb.BBAttributes_array[index] = 0xFFFFFFFF;
  }

  flash_bb.Bank = FLASH_BANK_1;
  flash_bb.BBAttributesType = FLASH_BB_SEC;
  HAL_FLASHEx_ConfigBBAttributes(&flash_bb);
  flash_bb.BBAttributesType = FLASH_BB_PRIV;
  HAL_FLASHEx_ConfigBBAttributes(&flash_bb);

  flash_bb.Bank = FLASH_BANK_2;
  flash_bb.BBAttributesType = FLASH_BB_SEC;
  HAL_FLASHEx_ConfigBBAttributes(&flash_bb);
  flash_bb.BBAttributesType = FLASH_BB_PRIV;
  HAL_FLASHEx_ConfigBBAttributes(&flash_bb);
}

void tz_init_boardloader(void) {
  // Configure ARM SCB/FBU security
  tz_configure_arm();

  // Configure SAU security attributes
  tz_configure_sau();

  // Enable GTZC (Global Trust-Zone Controller) peripheral clock
  __HAL_RCC_GTZC1_CLK_ENABLE();
  __HAL_RCC_GTZC2_CLK_ENABLE();

  // Configure SRAM security attributes
  tz_configure_sram();

  // Configure FLASH security attributes
  tz_configure_flash();

  // Configure FSMC security attributes
  tz_configure_fsmc();

  // Make all peripherals secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_ALL, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  // Clear all illegal access flags in GTZC TZIC
  HAL_GTZC_TZIC_ClearFlag(GTZC_PERIPH_ALL);

  // Enable all illegal access interrupts in GTZC TZIC
  HAL_GTZC_TZIC_EnableIT(GTZC_PERIPH_ALL);

  // Enable GTZC secure interrupt
  NVIC_SetPriority(GTZC_IRQn, IRQ_PRI_HIGHEST);
  NVIC_EnableIRQ(GTZC_IRQn);
}

void tz_init_kernel(void) {
  // Configure SRAM security attributes
  tz_configure_sram();

  // Configure FLASH security attributes
  tz_configure_flash();

  // Configure FSMC security attributes
  tz_configure_fsmc();

  // Make all peripherals secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_ALL, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  // Clear all illegal access flags in GTZC TZIC
  HAL_GTZC_TZIC_ClearFlag(GTZC_PERIPH_ALL);

  // Enable all illegal access interrupts in GTZC TZIC
  HAL_GTZC_TZIC_EnableIT(GTZC_PERIPH_ALL);

  // Enable GTZC secure interrupt
  NVIC_SetPriority(GTZC_IRQn, IRQ_PRI_HIGHEST);
  NVIC_EnableIRQ(GTZC_IRQn);
}

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
    {SRAM3_BASE, SRAM3_BASE + SRAM3_SIZE, GTZC_MPCBB3},
#if defined STM32U5A9xx | defined STM32U5G9xx
    {SRAM5_BASE, SRAM5_BASE + SRAM5_SIZE, GTZC_MPCBB5},
#endif
#if defined STM32U5G9xx
    {SRAM6_BASE, SRAM6_BASE + SRAM6_SIZE, GTZC_MPCBB6},
#endif
    {SRAM4_BASE, SRAM4_BASE + SRAM4_SIZE, GTZC_MPCBB4},
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

typedef struct {
  // Start address of the region
  uint32_t start;
  // End address of the region + 1
  size_t end;
  // PRIVBB register base
  volatile uint32_t* privbb;
} flash_region_t;

#if defined STM32U5A9xx
#define XFLASH_BANK_SIZE 0x200000
#elif defined STM32U5G9xx
#define XFLASH_BANK_SIZE 0x200000
#elif defined STM32U585xx
#define XFLASH_BANK_SIZE 0x100000
#else
#error "Unknown MCU"
#endif

#define FLASH_BANK1_BASE FLASH_BASE
#define FLASH_BANK2_BASE (FLASH_BASE + XFLASH_BANK_SIZE)

// FLASH regions must be in order of ascending start address
// and must not overlap
flash_region_t g_flash_regions[] = {
    {FLASH_BANK1_BASE, FLASH_BANK1_BASE + XFLASH_BANK_SIZE, &FLASH->PRIVBB1R1},
    {FLASH_BANK2_BASE, FLASH_BANK2_BASE + XFLASH_BANK_SIZE, &FLASH->PRIVBB2R1},
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
