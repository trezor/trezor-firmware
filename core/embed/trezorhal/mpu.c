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
#include TREZOR_BOARD
#include "stm32f4xx_ll_cortex.h"

// http://infocenter.arm.com/help/topic/com.arm.doc.dui0552a/BABDJJGF.html
#define MPU_RASR_ATTR_FLASH (MPU_RASR_C_Msk)
#define MPU_RASR_ATTR_SRAM (MPU_RASR_C_Msk | MPU_RASR_S_Msk)
#define MPU_RASR_ATTR_PERIPH (MPU_RASR_B_Msk | MPU_RASR_S_Msk)

#define MPU_SUBREGION_DISABLE(X) ((X) << MPU_RASR_SRD_Pos)

void mpu_config_off(void) {
  // Disable MPU
  HAL_MPU_Disable();
}

void mpu_config_bootloader(void) {
  // Disable MPU
  HAL_MPU_Disable();

  // Note: later entries overwrite previous ones

  // Everything (0x00000000 - 0xFFFFFFFF, 4 GiB, read-write)
  MPU->RNR = MPU_REGION_NUMBER0;
  MPU->RBAR = 0;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_4GB | LL_MPU_REGION_FULL_ACCESS;

  // Flash (0x0800C000 - 0x0800FFFF, 16 KiB, no access)
  MPU->RNR = MPU_REGION_NUMBER1;
  MPU->RBAR = FLASH_BASE + 0xC000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_16KB | LL_MPU_REGION_NO_ACCESS;

  // Flash (0x0810C000 - 0x0810FFFF, 16 KiB, no access)
  MPU->RNR = MPU_REGION_NUMBER2;
  MPU->RBAR = FLASH_BASE + 0x10C000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_16KB | LL_MPU_REGION_NO_ACCESS;

  // SRAM (0x20000000 - 0x2002FFFF, 192 KiB = 256 KiB except 2/8 at end,
  // read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER3;
  MPU->RBAR = SRAM_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_SRAM |
              LL_MPU_REGION_SIZE_256KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk | MPU_SUBREGION_DISABLE(0xC0);

#ifdef USE_SDRAM
  // Peripherals (0x40000000 - 0x5FFFFFFF, read-write, execute never)
  // SDRAM (0xC0000000 - 0xDFFFFFFF, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER4;
  MPU->RBAR = 0;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_PERIPH |
              LL_MPU_REGION_SIZE_4GB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk | MPU_SUBREGION_DISABLE(0xBB);
#else
  // Peripherals (0x40000000 - 0x5FFFFFFF, read-write, execute never)
  // External RAM (0x60000000 - 0x7FFFFFFF, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER4;
  MPU->RBAR = PERIPH_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_PERIPH |
              LL_MPU_REGION_SIZE_1GB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;
#endif

#if defined STM32F427xx || defined STM32F429xx
  // CCMRAM (0x10000000 - 0x1000FFFF, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER5;
  MPU->RBAR = CCMDATARAM_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_SRAM |
              LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;
#elif STM32F405xx
  // no CCMRAM
#else
#error Unsupported MCU
#endif

  // Enable MPU
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_firmware(void) {
  // Disable MPU
  HAL_MPU_Disable();

  // Note: later entries overwrite previous ones

  /*
      // Boardloader (0x08000000 - 0x0800FFFF, 64 KiB, read-only, execute never)
      MPU->RBAR = FLASH_BASE | MPU_REGION_NUMBER0;
      MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
     LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_PRIV_RO_URO | MPU_RASR_XN_Msk;
  */

  // Bootloader (0x08020000 - 0x0803FFFF, 64 KiB, read-only)
  MPU->RNR = MPU_REGION_NUMBER0;
  MPU->RBAR = FLASH_BASE + 0x20000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_PRIV_RO_URO;

  // Storage#1 (0x08010000 - 0x0801FFFF, 64 KiB, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER1;
  MPU->RBAR = FLASH_BASE + 0x10000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;
  // Storage#2 (0x08110000 - 0x0811FFFF, 64 KiB, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER2;
  MPU->RBAR = FLASH_BASE + 0x110000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;

  // Firmware (0x08040000 - 0x080FFFFF, 6 * 128 KiB = 1024 KiB except 2/8 at
  // start = 768 KiB, read-only)
  MPU->RNR = MPU_REGION_NUMBER3;
  MPU->RBAR = FLASH_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_1MB | LL_MPU_REGION_PRIV_RO_URO |
              MPU_SUBREGION_DISABLE(0x03);

  // Firmware extra (0x08120000 - 0x081FFFFF, 7 * 128 KiB = 1024 KiB except 1/8
  // at start = 896 KiB, read-only)
  MPU->RNR = MPU_REGION_NUMBER4;
  MPU->RBAR = FLASH_BASE + 0x100000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_1MB | LL_MPU_REGION_PRIV_RO_URO |
              MPU_SUBREGION_DISABLE(0x01);

  // SRAM (0x20000000 - 0x2002FFFF, 192 KiB = 256 KiB except 2/8 at end,
  // read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER5;
  MPU->RBAR = SRAM_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_SRAM |
              LL_MPU_REGION_SIZE_256KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk | MPU_SUBREGION_DISABLE(0xC0);

#ifdef USE_SDRAM
  // Peripherals (0x40000000 - 0x5FFFFFFF, read-write, execute never)
  // SDRAM (0xC0000000 - 0xDFFFFFFF, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER6;
  MPU->RBAR = 0;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_PERIPH |
              LL_MPU_REGION_SIZE_4GB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk | MPU_SUBREGION_DISABLE(0xBB);
#else
  // Peripherals (0x40000000 - 0x5FFFFFFF, read-write, execute never)
  // External RAM (0x60000000 - 0x7FFFFFFF, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER6;
  MPU->RBAR = PERIPH_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_PERIPH |
              LL_MPU_REGION_SIZE_1GB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;
#endif

#if defined STM32F427xx || defined STM32F429xx
  // CCMRAM (0x10000000 - 0x1000FFFF, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER7;
  MPU->RBAR = CCMDATARAM_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_SRAM |
              LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;
#elif STM32F405xx
  // no CCMRAM
#else
#error Unsupported MCU
#endif

  // Enable MPU
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);

  __asm__ volatile("dsb");
  __asm__ volatile("isb");
}
