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

#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)

#define SAU_INIT_CTRL_ENABLE 1
#define SAU_INIT_CTRL_ALLNS 0
#define SET_REGION(n, start, size, sec)                     \
  SAU->RNR = ((n) & SAU_RNR_REGION_Msk);                    \
  SAU->RBAR = ((start) & SAU_RBAR_BADDR_Msk);               \
  SAU->RLAR = (((start) + (size)-1) & SAU_RLAR_LADDR_Msk) | \
              (((sec) << SAU_RLAR_NSC_Pos) & SAU_RLAR_NSC_Msk) | 1U

#define DIS_REGION(n)                    \
  SAU->RNR = ((n) & SAU_RNR_REGION_Msk); \
  SAU->RBAR = 0;                         \
  SAU->RLAR = 0

#ifndef SECMON
static void tz_configure_sau(void) {
  SET_REGION(0, 0x0BF90000, 0x00019000, 0);  // OTP etc

  SAU->CTRL =
      ((SAU_INIT_CTRL_ENABLE << SAU_CTRL_ENABLE_Pos) & SAU_CTRL_ENABLE_Msk) |
      ((SAU_INIT_CTRL_ALLNS << SAU_CTRL_ALLNS_Pos) & SAU_CTRL_ALLNS_Msk);
}
#endif

#ifdef SECMON

extern uint8_t _sgstubs_section_start;
extern uint8_t _sgstubs_section_end;

#define SGSTUBS_START ((uint32_t) & _sgstubs_section_start)
#define SGSTUBS_END ((uint32_t) & _sgstubs_section_end)
#define SGSTUBS_SIZE (SGSTUBS_END - SGSTUBS_START)

// defined in linker script
extern uint32_t _secmon_size;

#define SECMON_SIZE ((uint32_t) & _secmon_size)

#define NONSECURE_CODE_START (FIRMWARE_START + SECMON_SIZE)
#define NONSECURE_CODE_SIZE (FIRMWARE_MAXSIZE - SECMON_SIZE)

static void tz_configure_sau(void) {
  SAU->CTRL = 0;
  __DSB();
  __ISB();

  // clang-format off
  SET_REGION(0, 0x0BFA0000,            0x800,               0); // OTP, UID, etc
  SET_REGION(1, NONSECURE_CODE_START,  NONSECURE_CODE_SIZE, 0);
  SET_REGION(2, ASSETS_START,          ASSETS_MAXSIZE,      0);
  SET_REGION(3, SGSTUBS_START,         SGSTUBS_SIZE,        1);
  SET_REGION(4, NONSECURE_RAM1_START,  NONSECURE_RAM1_SIZE, 0);
  SET_REGION(5, NONSECURE_RAM2_START,  NONSECURE_RAM2_SIZE, 0);
  SET_REGION(6, PERIPH_BASE_NS,        SIZE_256M,           0);
  SET_REGION(7, GFXMMU_VIRTUAL_BUFFERS_BASE_NS, SIZE_16M,   0);
  // clang-format on

  SAU->CTRL = SAU_CTRL_ENABLE_Msk;
  __DSB();
  __ISB();
}

#endif  // SECMON

static void tz_enable_gtzc(void) {
  // Enable GTZC (Global Trust-Zone Controller) peripheral clock
  __HAL_RCC_GTZC1_CLK_ENABLE();
  __HAL_RCC_GTZC2_CLK_ENABLE();
}

static void tz_enable_illegal_access_interrupt(void) {
  // Clear all illegal access flags in GTZC TZIC
  HAL_GTZC_TZIC_ClearFlag(GTZC_PERIPH_ALL);
  // Enable all illegal access interrupts in GTZC TZIC
  HAL_GTZC_TZIC_EnableIT(GTZC_PERIPH_ALL);
  // Enable GTZC secure interrupt
  NVIC_SetPriority(GTZC_IRQn, IRQ_PRI_HIGHEST);
  NVIC_EnableIRQ(GTZC_IRQn);
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

  uint32_t reg_value = SCB->AIRCR;
  reg_value &= ~SCB_AIRCR_VECTKEY_Msk;
  reg_value |= 0x5FAUL << SCB_AIRCR_VECTKEY_Pos;
  // Prioritize secure world interrupts over non-secure world
  reg_value |= SCB_AIRCR_PRIS_Msk;
#if PRODUCTION
  // Restrict SYSRESETREQ to secure world only.
  // In development builds, this restriction is disabled to allow
  // system resets from non-secure code (e.g., during debugging).
  reg_value |= SCB_AIRCR_SYSRESETREQS_Msk;
#endif
  // NMI, BusFault, HardFault are handled only in secure world
  reg_value &= ~SCB_AIRCR_BFHFNMINS_Msk;
  SCB->AIRCR = reg_value;
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

#endif  // __ARM_FEATURE_CMSE

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

#ifndef SECMON
void tz_init(void) {
#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
  tz_configure_arm();
  tz_configure_sau();
  tz_enable_gtzc();
  tz_configure_sram();
  tz_configure_flash();
  tz_configure_fsmc();

  // Make all peripherals secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_ALL, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  tz_enable_illegal_access_interrupt();
#endif
}
#endif  // !SECMON

#define _PASTE3(a, b, c) a##b##c
#define CONCAT3(a, b, c) _PASTE3(a, b, c)
#define OPTIGA_I2C(FIELD) CONCAT3(I2C_INSTANCE_, OPTIGA_I2C_INSTANCE, FIELD)

#ifdef SECMON
void tz_init(void) {
  tz_configure_arm();
  tz_configure_sau();
  tz_enable_gtzc();
  tz_configure_sram();
  tz_configure_flash();
  tz_configure_fsmc();

  // Make part of the FLASH and SRAM regions non-secure
  // so the kernel can access them
  tz_set_sram_unsecure(NONSECURE_RAM1_START, NONSECURE_RAM1_SIZE, true);
  tz_set_sram_unsecure(NONSECURE_RAM2_START, NONSECURE_RAM2_SIZE, true);
  tz_set_flash_unsecure(NONSECURE_CODE_START, NONSECURE_CODE_SIZE, true);
  tz_set_flash_unsecure(ASSETS_START, ASSETS_MAXSIZE, true);

  // Set all peripherals as non-secure & privileged by default
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_ALL, GTZC_TZSC_PERIPH_NSEC | GTZC_TZSC_PERIPH_PRIV);

  // Set RNG as secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_RNG, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  // Set SAES as secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_SAES, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  // Set IWDG as secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_IWDG, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  // Set HASH as secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_HASH, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  // Set RAMCFG as secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_RAMCFG, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  // Set WWDG as secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_WWDG, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  // Set CACHE registers as secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_ICACHE_REG, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_DCACHE1_REG, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      GTZC_PERIPH_DCACHE2_REG, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  // Set all interrupts as non-secure
  for (int i = 0; i < 512; i++) {
    NVIC_SetTargetState(i);
  }

  // Set GTZC interrupt as secure
  NVIC_ClearTargetState(GTZC_IRQn);

  // System Configuration Controller accessible only from secure mode
  SYSCFG->SECCFGR |= SYSCFG_SECCFGR_FPUSEC | SYSCFG_SECCFGR_CLASSBSEC |
                     SYSCFG_SECCFGR_SYSCFGSEC;

  // Disable chaching of SRAM in DCACHE2 (used only by GPU which we do not use)
  SYSCFG->CFGR1 &= ~SYSCFG_CFGR1_SRAMCACHED;

  // All RCC peripherals secure by default
  const uint32_t RCC_SECCFGR_ALL_BITS =
      RCC_SECCFGR_HSISEC | RCC_SECCFGR_HSESEC | RCC_SECCFGR_MSISEC |
      RCC_SECCFGR_LSISEC | RCC_SECCFGR_LSESEC | RCC_SECCFGR_SYSCLKSEC |
      RCC_SECCFGR_PRESCSEC | RCC_SECCFGR_PLL1SEC | RCC_SECCFGR_PLL2SEC |
      RCC_SECCFGR_PLL3SEC | RCC_SECCFGR_ICLKSEC | RCC_SECCFGR_HSI48SEC |
      RCC_SECCFGR_RMVFSEC;

  // RCC should be accessible only from secure/privileged mode
  // (only exceptions is PLL3 used for display deriver, which is non-secure)
  RCC->SECCFGR |= RCC_SECCFGR_ALL_BITS;  // All secure
  RCC->SECCFGR &= ~RCC_SECCFGR_PLL3SEC;  // PLL3 non-secure
  RCC->PRIVCFGR |= RCC_PRIVCFGR_SPRIV | RCC_PRIVCFGR_NSPRIV;

  const uint32_t PWR_SECCFGR_ALL_BITS =
      PWR_SECCFGR_WUP1SEC | PWR_SECCFGR_WUP2SEC | PWR_SECCFGR_WUP3SEC |
      PWR_SECCFGR_WUP4SEC | PWR_SECCFGR_WUP5SEC | PWR_SECCFGR_WUP6SEC |
      PWR_SECCFGR_WUP7SEC | PWR_SECCFGR_WUP8SEC | PWR_SECCFGR_LPMSEC |
      PWR_SECCFGR_VDMSEC | PWR_SECCFGR_VBSEC | PWR_SECCFGR_APCSEC;

  // PWR should be accessible only from secure/privileged mode
  PWR->SECCFGR |= PWR_SECCFGR_ALL_BITS;  // All secure
  PWR->PRIVCFGR |= PWR_PRIVCFGR_NSPRIV | PWR_PRIVCFGR_SPRIV;

  // Make GPDMA1 non-secure & privilege mode
  // Channel 12 (used for hash processor) is secure, all others are non-secure

  __HAL_RCC_GPDMA1_CLK_ENABLE();
  GPDMA1->SECCFGR &= ~0xFFFF;
  GPDMA1->SECCFGR |= (1 << 12);
  GPDMA1->PRIVCFGR |= 0xFFFF;

  // Enable all GPIOS and make them non-secure & privileged

  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOE_CLK_ENABLE();
  __HAL_RCC_GPIOF_CLK_ENABLE();
  __HAL_RCC_GPIOG_CLK_ENABLE();
  __HAL_RCC_GPIOH_CLK_ENABLE();
  __HAL_RCC_GPIOI_CLK_ENABLE();
#ifdef GPIOJ
  __HAL_RCC_GPIOJ_CLK_ENABLE();
#endif

  GPIOA->SECCFGR &= ~0xFFFF;
  GPIOB->SECCFGR &= ~0xFFFF;
  GPIOC->SECCFGR &= ~0xFFFF;
  GPIOD->SECCFGR &= ~0xFFFF;
  GPIOE->SECCFGR &= ~0xFFFF;
  GPIOF->SECCFGR &= ~0xFFFF;
  GPIOG->SECCFGR &= ~0xFFFF;
  GPIOH->SECCFGR &= ~0xFFFF;
  GPIOI->SECCFGR &= ~0xFFFF;
#ifdef GPIOJ
  GPIOJ->SECCFGR &= ~0xFFFF;
#endif

#ifdef USE_HW_REVISION
  HW_REVISION_0_PORT->SECCFGR |= HW_REVISION_0_PIN;
  HW_REVISION_1_PORT->SECCFGR |= HW_REVISION_1_PIN;
  HW_REVISION_2_PORT->SECCFGR |= HW_REVISION_2_PIN;
#ifdef HW_REVISION_3_PIN
  HW_REVISION_3_PORT->SECCFGR |= HW_REVISION_3_PIN;
#endif
#endif

#ifdef USE_TAMPER
  // Set TAMPER interrupt as secure
  NVIC_ClearTargetState(TAMP_IRQn);
#endif

#ifdef USE_OPTIGA
  // Set Optiga I2C secure & privileged
  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      OPTIGA_I2C(_GTZC_PERIPH), GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);

  OPTIGA_RST_PORT->SECCFGR |= OPTIGA_RST_PIN;
  OPTIGA_PWR_PORT->SECCFGR |= OPTIGA_PWR_PIN;

  OPTIGA_I2C(_SCL_PORT)->SECCFGR |= OPTIGA_I2C(_SCL_PIN);
  OPTIGA_I2C(_SDA_PORT)->SECCFGR |= OPTIGA_I2C(_SDA_PIN);

  NVIC_ClearTargetState(OPTIGA_I2C(_EV_IRQn));
  NVIC_ClearTargetState(OPTIGA_I2C(_ER_IRQn));
#endif

#ifdef USE_TROPIC
  TROPIC01_INT_PORT->SECCFGR |= TROPIC01_INT_PIN;
  TROPIC01_PWR_PORT->SECCFGR |= TROPIC01_PWR_PIN;
  TROPIC01_SPI_NSS_PORT->SECCFGR |= TROPIC01_SPI_NSS_PIN;
  TROPIC01_SPI_SCK_PORT->SECCFGR |= TROPIC01_SPI_SCK_PIN;
  TROPIC01_SPI_MISO_PORT->SECCFGR |= TROPIC01_SPI_MISO_PIN;
  TROPIC01_SPI_MOSI_PORT->SECCFGR |= TROPIC01_SPI_MOSI_PIN;

  HAL_GTZC_TZSC_ConfigPeriphAttributes(
      TROPIC01_SPI_GTZC_PERIPH, GTZC_TZSC_PERIPH_SEC | GTZC_TZSC_PERIPH_PRIV);
#endif

  tz_enable_illegal_access_interrupt();

  // Lock SAU configuration & AIRCR register against further modifications
  SYSCFG->CSLCKR |= SYSCFG_CSLCKR_LOCKSAU | SYSCFG_CSLCKR_LOCKSVTAIRCR;

  // Lock GTZC peripheral attributes against further modifications
  GTZC_TZSC1->CR |= GTZC_TZSC_CR_LCK_Msk;
  GTZC_TZSC2->CR |= GTZC_TZSC_CR_LCK_Msk;
}

#endif  // SECMON

#endif  // KERNEL_MODE
