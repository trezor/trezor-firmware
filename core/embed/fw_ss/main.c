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

#include STM32_HAL_H

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <display.h>
#include <touch.h>

#define CORE_SERVICE_VTBL 0x08091600

extern void jump_unsecure(uint32_t location);

void jump_to_core_services(void) { jump_unsecure(CORE_SERVICE_VTBL); }


// from linker
extern uint8_t _sgstubs_start;
extern uint8_t _sgstubs_end;


static void trustzone_configure_sau() {
  // configure unsecure regions for core services & application

  // Flash (Non-Secure)
  SAU->RNR = 0;
  SAU->RBAR = 0x08090000 & SAU_RBAR_BADDR_Msk;
  SAU->RLAR = ((0x08110000 - 1) & SAU_RLAR_LADDR_Msk) | 0x01;
  // Flash (Non-Secure callable)
  SAU->RNR = 1;
  SAU->RBAR = (uint32_t) &_sgstubs_start & SAU_RBAR_BADDR_Msk;
  SAU->RLAR = (((uint32_t) &_sgstubs_end - 1) & SAU_RLAR_LADDR_Msk) | 0x01 | 0x02;
  // SRAM1 (Non-Secure)
  SAU->RNR = 2;
  SAU->RBAR = 0x20020000 & SAU_RBAR_BADDR_Msk;
  SAU->RLAR = ((0x20060000 - 1) & SAU_RLAR_LADDR_Msk) | 0x01;
  // SRAM2 ((Non-Secure, stack)
  SAU->RNR = 3;
  SAU->RBAR = 0x200C4000 & SAU_RBAR_BADDR_Msk;
  SAU->RLAR = ((0x200CC000 - 1) & SAU_RLAR_LADDR_Msk) | 0x01;
  // SRAM3+5 (Non-Secure, fb1+fb2)
  SAU->RNR = 4;
  SAU->RBAR = 0x200D0000 & SAU_RBAR_BADDR_Msk;
  SAU->RLAR = ((0x20270000 - 1) & SAU_RLAR_LADDR_Msk) | 0x01;
  // PERIPHERAL (Non-Secure)
  SAU->RNR = 5;
  SAU->RBAR = PERIPH_BASE_NS & SAU_RBAR_BADDR_Msk;
  SAU->RLAR =
      ((PERIPH_BASE_NS + 256 * 1024 * 1024 - 1) & SAU_RLAR_LADDR_Msk) | 0x01;
  // GFXMMU (Non-Secure)
  SAU->RNR = 6;
  SAU->RBAR = GFXMMU_VIRTUAL_BUFFERS_BASE_NS & SAU_RBAR_BADDR_Msk;
  SAU->RLAR = ((GFXMMU_VIRTUAL_BUFFERS_BASE_NS + 16 * 1024 * 1024 - 1) &
               SAU_RLAR_LADDR_Msk) |
              0x01;

  // Enable SAU
  SAU->CTRL = SAU_CTRL_ENABLE_Msk;
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

  // Set all blocks unsecured & unprivileged
  for (int index = 0; index < 52; index++) {
    mpcbb.AttributeConfig.MPCBB_SecConfig_array[index] = 0x00000000U;
    mpcbb.AttributeConfig.MPCBB_PrivConfig_array[index] = 0x00000000U;
  }

  HAL_GTZC_MPCBB_ConfigMem(SRAM3_BASE, &mpcbb);
  HAL_GTZC_MPCBB_ConfigMem(SRAM4_BASE, &mpcbb);
#if defined STM32U5A9xx | defined STM32U5G9xx
  HAL_GTZC_MPCBB_ConfigMem(SRAM5_BASE, &mpcbb);
#endif

  // Set all blocks secured & unprivileged
  for (int index = 0; index < 52; index++) {
    mpcbb.AttributeConfig.MPCBB_SecConfig_array[index] = 0xFFFFFFFFU;
    mpcbb.AttributeConfig.MPCBB_PrivConfig_array[index] = 0x00000000U;
  }

  // unsecure 256KB of SRAM1 for core services & app
  for (int index = 8; index < 24; index++) {
    mpcbb.AttributeConfig.MPCBB_SecConfig_array[index] = 0x00000000U;
  }

  HAL_GTZC_MPCBB_ConfigMem(SRAM1_BASE, &mpcbb);

  // Set all blocks secured & unprivileged
  for (int index = 0; index < 52; index++) {
    mpcbb.AttributeConfig.MPCBB_SecConfig_array[index] = 0xFFFFFFFFU;
    mpcbb.AttributeConfig.MPCBB_PrivConfig_array[index] = 0x00000000U;
  }

  // unsecure 32KB of SRAM2 (stack) for core services & app
  mpcbb.AttributeConfig.MPCBB_SecConfig_array[1] = 0x00000000U;
  mpcbb.AttributeConfig.MPCBB_SecConfig_array[2] = 0x00000000U;

  HAL_GTZC_MPCBB_ConfigMem(SRAM2_BASE, &mpcbb);
}

// Configure FLASH security
static void trustzone_configure_flash(void) {
  FLASH_BBAttributesTypeDef flash_bb = {0};

  flash_bb.Bank = FLASH_BANK_1;
  flash_bb.BBAttributesType = FLASH_BB_SEC;

  HAL_FLASHEx_GetConfigBBAttributes(&flash_bb);

  // Set 512KB (64 pages) after secure services unsecure
  flash_bb.BBAttributes_array[2] = 0x000000FF;
  flash_bb.BBAttributes_array[3] = 0x00000000;
  flash_bb.BBAttributes_array[4] = 0xFFFFFF00;

  HAL_FLASHEx_ConfigBBAttributes(&flash_bb);
}

static void trustzone_configure_peripherals(void) {
  // Make all peripherals unsecure
  HAL_GTZC_TZSC_ConfigPeriphAttributes(GTZC_PERIPH_ALL, GTZC_TZSC_PERIPH_NSEC);
}

void isolate_unsecured_world(void) {
  trustzone_configure_sau();
  trustzone_configure_flash();
  trustzone_configure_sram();
  trustzone_configure_peripherals();

  // SCB->AIRCR
  //   SYSRESETREQS <- ?,
  //   BFHFMINS <- BusFault, HarudFault, NMI Secure/Non-Secure
  // SCB->SCR
  //    SLEEPDEEPS <- ?

  // Select secure/unsecure flag for exception handlers
  //

  // Select secure/unsecure flag for interrupts
  // NVIC_SetTargetState()


  // PWR_SECCFGR -- Secure everything needed for secure services
  // PWR_PRIVCFGR -- NSPRIV, SPRIV <- 1
  // TODO

  // RCC_SECCFGR -- Secure everything needed for secure services
  // RCC_PRIVCFGR -- NSPRIV, SPRIV <- 1
  // TODO

  // SYSCFG_SECCFGR
  // TODO

  // GPIO -- Set selected PINs unsecure (all are secure by default)
  // TODO
}

void platform_init() {
  touch_init();
  display_reinit();
}

int main(void) {  // SECURE SERVICES

  // Initialize hardware driver
  platform_init();

  display_printf("Secure services are running...\n");

  HAL_Delay(500);  // uses Secure SysTick

  // Configure trust-zone
  isolate_unsecured_world();

  // Pass execution to unsecured core services
  jump_to_core_services();

  return 0;
}

