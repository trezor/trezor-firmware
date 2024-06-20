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

#include <trustzone.h>

#include STM32_HAL_H
#include "irq.h"

#ifdef BOARDLOADER

#define SAU_INIT_CTRL_ENABLE 1
#define SAU_INIT_CTRL_ALLNS 0
#define SAU_INIT_REGION(n, start, end, sec)   \
  SAU->RNR = ((n) & SAU_RNR_REGION_Msk);      \
  SAU->RBAR = ((start) & SAU_RBAR_BADDR_Msk); \
  SAU->RLAR = ((end) & SAU_RLAR_LADDR_Msk) |  \
              (((sec) << SAU_RLAR_NSC_Pos) & SAU_RLAR_NSC_Msk) | 1U

static void trustzone_configure_sau(void) {
  SAU_INIT_REGION(0, 0x0BF90000, 0x0BFA8FFF, 0);  // OTP etc

  SAU->CTRL =
      ((SAU_INIT_CTRL_ENABLE << SAU_CTRL_ENABLE_Pos) & SAU_CTRL_ENABLE_Msk) |
      ((SAU_INIT_CTRL_ALLNS << SAU_CTRL_ALLNS_Pos) & SAU_CTRL_ALLNS_Msk);
}

// Configure ARMCortex-M33 SCB and FPU security
static void trustzone_configure_arm(void) {
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
static void trustzone_configure_sram(void) {
  MPCBB_ConfigTypeDef mpcbb = {0};

  // No exceptions on illegal access
  mpcbb.SecureRWIllegalMode = GTZC_MPCBB_SRWILADIS_DISABLE;
  // Settings of SRAM clock in RCC is secure
  mpcbb.InvertSecureState = GTZC_MPCBB_INVSECSTATE_NOT_INVERTED;
  // Set configuration as unlocked
  mpcbb.AttributeConfig.MPCBB_LockConfig_array[0] = 0x00000000U;

  // Set all blocks secured & unprivileged
  for (int index = 0; index < GTZC_MPCBB_NB_VCTR_REG_MAX; index++) {
    mpcbb.AttributeConfig.MPCBB_SecConfig_array[index] = 0xFFFFFFFFU;
    mpcbb.AttributeConfig.MPCBB_PrivConfig_array[index] = 0x00000000U;
  }

  HAL_GTZC_MPCBB_ConfigMem(SRAM1_BASE, &mpcbb);
  HAL_GTZC_MPCBB_ConfigMem(SRAM2_BASE, &mpcbb);
  HAL_GTZC_MPCBB_ConfigMem(SRAM3_BASE, &mpcbb);
  HAL_GTZC_MPCBB_ConfigMem(SRAM4_BASE, &mpcbb);
#if defined STM32U5A9xx | defined STM32U5G9xx
  HAL_GTZC_MPCBB_ConfigMem(SRAM5_BASE, &mpcbb);
#endif
#if defined STM32U5G9xx
  HAL_GTZC_MPCBB_ConfigMem(SRAM6_BASE, &mpcbb);
#endif
}

static void trustzone_configure_fsmc(void) {
  __HAL_RCC_FMC_CLK_ENABLE();
  MPCWM_ConfigTypeDef mpcwm = {0};

  mpcwm.AreaId = GTZC_TZSC_MPCWM_ID1;
  mpcwm.AreaStatus = ENABLE;
  mpcwm.Attribute = GTZC_TZSC_MPCWM_REGION_SEC;
  mpcwm.Length = 128 * 1024;
  mpcwm.Offset = 0;
  mpcwm.Lock = GTZC_TZSC_MPCWM_LOCK_OFF;
  HAL_GTZC_TZSC_MPCWM_ConfigMemAttributes(FMC_BANK1, &mpcwm);
}

// Configure FLASH security
static void trustzone_configure_flash(void) {
  FLASH_BBAttributesTypeDef flash_bb = {0};

  // Set all blocks as secured
  for (int index = 0; index < FLASH_BLOCKBASED_NB_REG; index++) {
    flash_bb.BBAttributes_array[index] = 0xFFFFFFFF;
  }

  flash_bb.Bank = FLASH_BANK_1;
  flash_bb.BBAttributesType = FLASH_BB_SEC;
  HAL_FLASHEx_ConfigBBAttributes(&flash_bb);

  flash_bb.Bank = FLASH_BANK_2;
  flash_bb.BBAttributesType = FLASH_BB_SEC;
  HAL_FLASHEx_ConfigBBAttributes(&flash_bb);
}

void trustzone_init_boardloader(void) {
  // Configure ARM SCB/FBU security
  trustzone_configure_arm();

  // Configure SAU security attributes
  trustzone_configure_sau();

  // Enable GTZC (Global Trust-Zone Controller) peripheral clock
  __HAL_RCC_GTZC1_CLK_ENABLE();
  __HAL_RCC_GTZC2_CLK_ENABLE();

  // Configure SRAM security attributes
  trustzone_configure_sram();

  // Configure FLASH security attributes
  trustzone_configure_flash();

  // Configure FSMC security attributes
  trustzone_configure_fsmc();

  // Make all peripherals secure
  HAL_GTZC_TZSC_ConfigPeriphAttributes(GTZC_PERIPH_ALL, GTZC_TZSC_PERIPH_SEC);

  // Clear all illegal access flags in GTZC TZIC
  HAL_GTZC_TZIC_ClearFlag(GTZC_PERIPH_ALL);

  // Enable all illegal access interrupts in GTZC TZIC
  HAL_GTZC_TZIC_EnableIT(GTZC_PERIPH_ALL);

  // Enable GTZC secure interrupt
  NVIC_SetPriority(GTZC_IRQn, IRQ_PRI_HIGHEST);
  NVIC_EnableIRQ(GTZC_IRQn);
}

#endif  // BOARDLOADER
