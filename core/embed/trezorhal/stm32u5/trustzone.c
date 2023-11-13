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

#ifdef BOARDLOADER

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
  for (int index = 0; index < 52; index++) {
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

  // Enable GTZC (Global Trust-Zone Controller) peripheral clock
  __HAL_RCC_GTZC1_CLK_ENABLE();
  __HAL_RCC_GTZC2_CLK_ENABLE();

  // Configure SRAM security attributes
  trustzone_configure_sram();

  // Configure FLASH security attributes
  trustzone_configure_flash();

  // Make all peripherals secure
  HAL_GTZC_TZSC_ConfigPeriphAttributes(GTZC_PERIPH_ALL, GTZC_TZSC_PERIPH_SEC);

  // Clear all illegal access flags in GTZC TZIC
  HAL_GTZC_TZIC_ClearFlag(GTZC_PERIPH_ALL);

  // Enable all illegal access interrupts in GTZC TZIC
  HAL_GTZC_TZIC_EnableIT(GTZC_PERIPH_ALL);

  // Enable GTZC secure interrupt
  HAL_NVIC_SetPriority(GTZC_IRQn, 0, 0);  // Highest priority level
  HAL_NVIC_EnableIRQ(GTZC_IRQn);
}

#endif  // BOARDLOADER
