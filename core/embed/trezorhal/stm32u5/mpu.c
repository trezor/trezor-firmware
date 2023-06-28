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
#include "common.h"
#include "flash.h"
#include "model.h"
#include "stm32u5xx_ll_cortex.h"

#define ATTR_IDX_FLASH (0 << 1)
#define ATTR_IDX_FLASH_NON_CACHABLE (3 << 1)
#define ATTR_IDX_SRAM (1 << 1)
#define ATTR_IDX_PERIPH (2 << 1)
#define REGION_END(x) (((x) & ~0x1F) | 0x01)

#define SHAREABILITY_FLASH (LL_MPU_ACCESS_NOT_SHAREABLE)
#define SHAREABILITY_SRAM \
  (LL_MPU_ACCESS_INNER_SHAREABLE | LL_MPU_ACCESS_OUTER_SHAREABLE)

void mpu_config_off(void) {
  // Disable MPU
  HAL_MPU_Disable();
}

static uint32_t area_start(const flash_area_t* area) {
  return (uint32_t)flash_area_get_address(area, 0, 0);
}

static uint32_t area_end(const flash_area_t* area) {
  uint32_t start = area_start(area);
  uint32_t size = flash_area_get_size(area);
  return start + size;
}

void mpu_config_boardloader(void) {
  // Disable MPU
  HAL_MPU_Disable();

  // flash memory
  MPU->MAIR0 = 0xAA;
  // internal ram
  MPU->MAIR0 |= 0xAA << 8;
  // peripherals
  MPU->MAIR0 |= 0x00 << 16;
  // non-cachable flash
  MPU->MAIR0 |= 0x44 << 24;

  // Secret
  MPU->RNR = MPU_REGION_NUMBER0;
  MPU->RBAR = FLASH_BASE_S | LL_MPU_REGION_ALL_RW | SHAREABILITY_FLASH |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU->RLAR = REGION_END(BOARDLOADER_START - 1) | ATTR_IDX_FLASH_NON_CACHABLE;

  // Flash boardloader (read-write)
  MPU->RNR = MPU_REGION_NUMBER1;
  MPU->RBAR = BOARDLOADER_START | LL_MPU_REGION_ALL_RW | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(BOOTLOADER_START - 1) | ATTR_IDX_FLASH;

  // Flash rest
  MPU->RNR = MPU_REGION_NUMBER2;
  MPU->RBAR = BOOTLOADER_START | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_FLASH;
  MPU->RLAR =
      REGION_END(FLASH_BASE_S + 0x400000 - 1) | ATTR_IDX_FLASH_NON_CACHABLE;

  // RAM  (read-write, execute never) (SRAM1)
  MPU->RNR = MPU_REGION_NUMBER3;
  MPU->RBAR = SRAM1_BASE_S | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(SRAM1_BASE_S + 0xC0000 - 1) | ATTR_IDX_SRAM;

  // RAM  (read-write, execute never) (SRAM2, 3, 5, 6)
  // reserve 256 bytes for stack overflow detection
  MPU->RNR = MPU_REGION_NUMBER4;
  MPU->RBAR = (SRAM2_BASE_S + 0x100) | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(SRAM1_BASE_S + 0x2F0000 - 1) | ATTR_IDX_SRAM;

  // GFXMMU_VIRTUAL_BUFFERS (read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER5;
  MPU->RBAR = GFXMMU_VIRTUAL_BUFFERS_BASE_S | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR =
      REGION_END(GFXMMU_VIRTUAL_BUFFERS_BASE_S + 0x1000000 - 1) | ATTR_IDX_SRAM;

  // Peripherals (read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER6;
  MPU->RBAR =
      PERIPH_BASE_S | LL_MPU_REGION_ALL_RW | LL_MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU->RLAR = REGION_END(PERIPH_BASE_S + 0x10000000 - 1) | ATTR_IDX_PERIPH;

  // OTP (read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER7;
  MPU->RBAR = FLASH_OTP_BASE | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(FLASH_OTP_BASE + FLASH_OTP_SIZE - 1) |
              ATTR_IDX_FLASH_NON_CACHABLE;

  // RAM SRAM4
  MPU->RNR = MPU_REGION_NUMBER7;
  MPU->RBAR = SRAM4_BASE_S | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(SRAM4_BASE_S + 0x4000 - 1) | ATTR_IDX_SRAM;

  // Enable MPU
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_bootloader(void) {
  // Disable MPU
  HAL_MPU_Disable();

  // flash memory
  MPU->MAIR0 = 0xAA;
  // internal ram
  MPU->MAIR0 |= 0xAA << 8;
  // peripherals
  MPU->MAIR0 |= 0x00 << 16;
  // non-cachable flash
  MPU->MAIR0 |= 0x44 << 24;

  // Secret + boardloader
  MPU->RNR = MPU_REGION_NUMBER0;
  MPU->RBAR = FLASH_BASE_S | LL_MPU_REGION_ALL_RW | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(BOOTLOADER_START - 1) | ATTR_IDX_FLASH_NON_CACHABLE;

  // Bootloader (read-write)
  MPU->RNR = MPU_REGION_NUMBER1;
  MPU->RBAR = BOOTLOADER_START | LL_MPU_REGION_ALL_RW | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(area_start(&STORAGE_AREAS[0]) - 1) | ATTR_IDX_FLASH;

  // Flash firmware + storage (read-write, execute never), till flash end
  MPU->RNR = MPU_REGION_NUMBER2;
  MPU->RBAR = area_start(&STORAGE_AREAS[0]) | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_FLASH;
  MPU->RLAR =
      REGION_END(FLASH_BASE_S + 0x400000 - 1) | ATTR_IDX_FLASH_NON_CACHABLE;

  // RAM  (read-write, execute never) (SRAM1)
  MPU->RNR = MPU_REGION_NUMBER3;
  MPU->RBAR = SRAM1_BASE_S | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(SRAM1_BASE_S + 0xC0000 - 1) | ATTR_IDX_SRAM;

  // RAM  (read-write, execute never) (SRAM2, 3, 5, 6)
  // reserve 256 bytes for stack overflow detection
  MPU->RNR = MPU_REGION_NUMBER4;
  MPU->RBAR = (SRAM2_BASE_S + 0x100) | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(SRAM1_BASE_S + 0x2F0000 - 1) | ATTR_IDX_SRAM;

  // GFXMMU_VIRTUAL_BUFFERS (read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER5;
  MPU->RBAR = GFXMMU_VIRTUAL_BUFFERS_BASE_S | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR =
      REGION_END(GFXMMU_VIRTUAL_BUFFERS_BASE_S + 0x1000000 - 1) | ATTR_IDX_SRAM;

  // Peripherals (read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER6;
  MPU->RBAR =
      PERIPH_BASE_S | LL_MPU_REGION_ALL_RW | LL_MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU->RLAR = REGION_END(PERIPH_BASE_S + 0x10000000 - 1) | ATTR_IDX_PERIPH;

  // OTP (read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER7;
  MPU->RBAR = FLASH_OTP_BASE | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(FLASH_OTP_BASE + FLASH_OTP_SIZE - 1) |
              ATTR_IDX_FLASH_NON_CACHABLE;

  // Enable MPU
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_firmware(void) {
  // Disable MPU
  HAL_MPU_Disable();

  // flash memory
  MPU->MAIR0 = 0xAA;
  // internal ram
  MPU->MAIR0 |= 0xAA << 8;
  // peripherals
  MPU->MAIR0 |= 0x00 << 16;
  // non-cachable flash
  MPU->MAIR0 |= 0x44 << 24;

  // bootloader + boardloader: no access, execute never: need to do everything
  // before turning on MPU

  // Storage (read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER0;
  MPU->RBAR = area_start(&STORAGE_AREAS[0]) | LL_MPU_REGION_ALL_RW |
              SHAREABILITY_FLASH | LL_MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU->RLAR = REGION_END(FIRMWARE_START - 1) | ATTR_IDX_FLASH_NON_CACHABLE;

  // Flash firmware (read-write)
  MPU->RNR = MPU_REGION_NUMBER1;
  MPU->RBAR = (FIRMWARE_START) | LL_MPU_REGION_ALL_RO | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(area_end(&FIRMWARE_AREA) - 1) | ATTR_IDX_FLASH;

  // RAM  (read-write, execute never) (SRAM1)
  MPU->RNR = MPU_REGION_NUMBER2;
  MPU->RBAR = SRAM1_BASE_S | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(SRAM1_BASE_S + 0xC0000 - 1) | ATTR_IDX_SRAM;

  // RAM  (read-write, execute never) (SRAM2, 3, 5, 6)
  // reserve 256 bytes for stack overflow detection
  MPU->RNR = MPU_REGION_NUMBER3;
  MPU->RBAR = (SRAM2_BASE_S + 0x100) | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(SRAM1_BASE_S + 0x2F0000 - 1) | ATTR_IDX_SRAM;

  // GFXMMU_VIRTUAL_BUFFERS (read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER4;
  MPU->RBAR = GFXMMU_VIRTUAL_BUFFERS_BASE_S | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR =
      REGION_END(GFXMMU_VIRTUAL_BUFFERS_BASE_S + 0x1000000 - 1) | ATTR_IDX_SRAM;

  // Peripherals (read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER5;
  MPU->RBAR =
      PERIPH_BASE_S | LL_MPU_REGION_ALL_RW | LL_MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU->RLAR = REGION_END(PERIPH_BASE_S + 0x10000000 - 1) | ATTR_IDX_PERIPH;

  // OTP (read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER6;
  MPU->RBAR = FLASH_OTP_BASE | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(FLASH_OTP_BASE + FLASH_OTP_SIZE - 1) |
              ATTR_IDX_FLASH_NON_CACHABLE;

  // Enable MPU
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);

  __asm__ volatile("dsb");
  __asm__ volatile("isb");
}
