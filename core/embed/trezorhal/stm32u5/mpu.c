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

void mpu_config_bootloader(void) {
  uint32_t storage_start =
      (uint32_t)flash_area_get_address(&STORAGE_AREAS[0], 0, 0);
  uint32_t storage_size = flash_area_get_size(&STORAGE_AREAS[0]) * 2;

  // Disable MPU
  HAL_MPU_Disable();

  // Note: later entries overwrite previous ones

  // flash memory
  MPU->MAIR0 = 0xAA;
  // internal ram
  MPU->MAIR0 |= 0xAA << 8;
  // peripherals
  MPU->MAIR0 |= 0x00 << 16;
  // non-cachable flash
  MPU->MAIR0 |= 0x44 << 24;

  // Flash boardloader + bootloader (read-write)
  MPU->RNR = MPU_REGION_NUMBER0;
  MPU->RBAR = FLASH_BASE | LL_MPU_REGION_ALL_RW | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(FIRMWARE_START - 1) | ATTR_IDX_FLASH;

  // Flash firmware (read-write)
  MPU->RNR = MPU_REGION_NUMBER1;
  MPU->RBAR = FIRMWARE_START | LL_MPU_REGION_ALL_RW | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(storage_start - 1) | ATTR_IDX_FLASH_NON_CACHABLE;

  // Storage (read-write, execute never)
  // TODO prepend secret?
  MPU->RNR = MPU_REGION_NUMBER2;
  MPU->RBAR = storage_start | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(storage_start + storage_size - 1) |
              ATTR_IDX_FLASH_NON_CACHABLE;

  // RAM (0x20000000 - 0x20260000, 4 MB, read-write, execute never) (SRAM
  // 1,2,3,5)
  MPU->RNR = MPU_REGION_NUMBER3;
  MPU->RBAR = SRAM1_BASE | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(SRAM1_BASE + 0x260000 - 1) | ATTR_IDX_SRAM;

  // GFXMMU_VIRTUAL_BUFFERS (0x24000000 - 0x25000000, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER4;
  MPU->RBAR = GFXMMU_VIRTUAL_BUFFERS_BASE_NS | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(GFXMMU_VIRTUAL_BUFFERS_BASE_NS + 0x1000000 - 1) |
              ATTR_IDX_SRAM;

  // Peripherals (0x40000000 - 0x5FFFFFFF, 4 MB, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER5;
  MPU->RBAR =
      PERIPH_BASE | LL_MPU_REGION_ALL_RW | LL_MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU->RLAR = REGION_END(PERIPH_BASE + 0x20000000 - 1) | ATTR_IDX_PERIPH;

  // OTP (0x0BFA 0000 - 0x0BFA 0200, read-write)
  MPU->RNR = MPU_REGION_NUMBER6;
  MPU->RBAR = FLASH_OTP_BASE | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(FLASH_OTP_BASE + FLASH_OTP_SIZE - 1) |
              ATTR_IDX_FLASH_NON_CACHABLE;

  // Enable MPU
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_firmware(void) {
  uint32_t storage_start =
      (uint32_t)flash_area_get_address(&STORAGE_AREAS[0], 0, 0);
  uint32_t storage_size = flash_area_get_size(&STORAGE_AREAS[0]) * 2;

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

  // Note: later entries overwrite previous ones

  // Boarloader + Bootloader (0x08000000 - 0x0803FFFF, read-only)
  MPU->RNR = MPU_REGION_NUMBER0;
  MPU->RBAR = FLASH_BASE | LL_MPU_REGION_ALL_RO | SHAREABILITY_FLASH;
  MPU->RLAR =
      REGION_END(FLASH_BASE + 0x40000 - 1) | ATTR_IDX_FLASH_NON_CACHABLE;

  // Flash (0x08000000 - 0x08400000, 4 MB, read-write)
  MPU->RNR = MPU_REGION_NUMBER1;
  MPU->RBAR =
      (FLASH_BASE + 0x40000) | LL_MPU_REGION_ALL_RO | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(storage_start - 1) | ATTR_IDX_FLASH;

  // Storage (read-write, execute never)
  // TODO prepend secret?
  MPU->RNR = MPU_REGION_NUMBER2;
  MPU->RBAR = storage_start | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_FLASH;
  MPU->RLAR = REGION_END(storage_start + storage_size - 1) |
              ATTR_IDX_FLASH_NON_CACHABLE;

  // RAM (0x20000000 - 0x20260000, 4 MB, read-write, execute never) (SRAM
  // 1,2,3,5)
  MPU->RNR = MPU_REGION_NUMBER3;
  MPU->RBAR = SRAM1_BASE | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(SRAM1_BASE + 0x260000 - 1) | ATTR_IDX_SRAM;

  // GFXMMU_VIRTUAL_BUFFERS (0x24000000 - 0x25000000, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER4;
  MPU->RBAR = GFXMMU_VIRTUAL_BUFFERS_BASE_NS | LL_MPU_REGION_ALL_RW |
              LL_MPU_INSTRUCTION_ACCESS_DISABLE | SHAREABILITY_SRAM;
  MPU->RLAR = REGION_END(GFXMMU_VIRTUAL_BUFFERS_BASE_NS + 0x1000000 - 1) |
              ATTR_IDX_SRAM;

  // Peripherals (0x40000000 - 0x5FFFFFFF, 4 MB, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER5;
  MPU->RBAR =
      PERIPH_BASE | LL_MPU_REGION_ALL_RW | LL_MPU_INSTRUCTION_ACCESS_DISABLE;
  MPU->RLAR = REGION_END(PERIPH_BASE + 0x20000000 - 1) | ATTR_IDX_PERIPH;

  // OTP (0x0BFA 0000 - 0x0BFA 0200, read-write)
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
