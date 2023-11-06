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
#include <stdbool.h>
#include "common.h"
#include "stm32u5xx_ll_cortex.h"

// region type
#define MPUX_TYPE_FLASH_CODE 0
#define MPUX_TYPE_SRAM 1
#define MPUX_TYPE_PERIPHERAL 2
#define MPUX_TYPE_FLASH_DATA 3

const static struct {
  uint32_t xn;    // executable
  uint32_t attr;  // attribute index
  uint32_t sh;    // shareable
} mpu_region_lookup[] = {

    // 0 - FLASH_CODE
    {
        .xn = LL_MPU_INSTRUCTION_ACCESS_ENABLE,
        .attr = LL_MPU_ATTRIBUTES_NUMBER0,
        .sh = LL_MPU_ACCESS_NOT_SHAREABLE,
    },
    // 1 - SRAM
    {
        .xn = LL_MPU_INSTRUCTION_ACCESS_DISABLE,
        .attr = LL_MPU_ATTRIBUTES_NUMBER1,
        .sh = LL_MPU_ACCESS_INNER_SHAREABLE,
    },
    // 2 - PERIPHERAL
    {
        .xn = LL_MPU_INSTRUCTION_ACCESS_DISABLE,
        .attr = LL_MPU_ATTRIBUTES_NUMBER2,
        .sh = LL_MPU_ACCESS_NOT_SHAREABLE,
    },
    // 3 - FLASH_DATA
    {
        .xn = LL_MPU_INSTRUCTION_ACCESS_DISABLE,
        .attr = LL_MPU_ATTRIBUTES_NUMBER3,
        .sh = LL_MPU_ACCESS_NOT_SHAREABLE,
    },
};

static inline uint32_t mpu_permission_lookup(bool write, bool unpriv) {
  if (write) {
    return unpriv ? LL_MPU_REGION_ALL_RW : LL_MPU_REGION_PRIV_RW;
  } else {
    return unpriv ? LL_MPU_REGION_ALL_RO : LL_MPU_REGION_PRIV_RO;
  }
}

#define MPUX_FLAG_NO 0
#define MPUX_FLAG_YES 1

#define SET_REGION(region, start, size, type, write, unpriv) \
  do {                                                       \
    uint32_t _type = MPUX_TYPE_##type;                       \
    uint32_t _write = MPUX_FLAG_##write;                     \
    uint32_t _unpriv = MPUX_FLAG_##unpriv;                   \
    MPU->RNR = LL_MPU_REGION_NUMBER##region;                 \
    uint32_t _start = (start) & (~0x1F);                     \
    uint32_t _sh = mpu_region_lookup[_type].sh;              \
    uint32_t _ap = mpu_permission_lookup(_write, _unpriv);   \
    uint32_t _xn = mpu_region_lookup[_type].xn;              \
    MPU->RBAR = _start | _sh | _ap | _xn;                    \
    uint32_t _limit = (_start + (size)-1) & (~0x1F);         \
    uint32_t _attr = mpu_region_lookup[_type].attr << 1;     \
    uint32_t _enable = LL_MPU_REGION_ENABLE;                 \
    MPU->RLAR = _limit | _attr | _enable;                    \
  } while (0)

#define DIS_REGION(region)                   \
  do {                                       \
    MPU->RNR = LL_MPU_REGION_NUMBER##region; \
    MPU->RBAR = 0;                           \
    MPU->RLAR = 0;                           \
  } while (0)

static void mpu_set_attributes() {
  // Attr[0] - FLASH - Not-Transient, Write-Through, Read Allocation
  MPU->MAIR0 = 0xAA;
  // Attr[1] - SRAM - Non-cacheable
  MPU->MAIR0 |= 0x44 << 8;
  // Attr[2] - Peripherals - nGnRnE
  MPU->MAIR0 |= 0x00 << 16;
  // Attr[3] - FLASH - Non-cacheable
  MPU->MAIR0 |= 0x44 << 24;
}

#define GFXMMU_BUFFERS_S GFXMMU_VIRTUAL_BUFFERS_BASE_S

#define SIZE_16K (16 * 1024)
#define SIZE_48K (48 * 1024)
#define SIZE_64K (64 * 1024)
#define SIZE_128K (128 * 1024)
#define SIZE_192K (192 * 1024)
#define SIZE_320K (320 * 1024)
#define SIZE_768K (768 * 1024)
#define SIZE_1728K ((832 * 2 + 64) * 1024)
#define SIZE_3776K ((4096 - 320) * 1024)
#define SIZE_3904K ((4096 - 192) * 1024)
#define SIZE_4032K ((4096 - 64) * 1024)
#define SIZE_4M (4 * 1024 * 1024)
#define SIZE_16M (16 * 1024 * 1024)
#define SIZE_256M (256 * 1024 * 1024)
#define SIZE_512M (512 * 1024 * 1024)

void mpu_config_boardloader() {
  HAL_MPU_Disable();
  mpu_set_attributes();
  // clang-format off
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, FLASH_BASE_S,             SIZE_16K,           FLASH_DATA,  YES,   YES ); // Secret
  SET_REGION( 1, FLASH_BASE_S + SIZE_16K,  SIZE_48K,           FLASH_CODE,   NO,   YES ); // Boardloader code
  SET_REGION( 2, FLASH_BASE_S + SIZE_64K,  SIZE_4032K,         FLASH_DATA,  YES,   YES ); // Bootloader + Storage + Firmware
  SET_REGION( 3, SRAM1_BASE_S,             SIZE_768K,          SRAM,        YES,   YES ); // SRAM1
  SET_REGION( 4, SRAM2_BASE_S + 0x100,     SIZE_1728K - 0x100, SRAM,        YES,   YES ); // SRAM2/3/5 + stack guard
  SET_REGION( 5, GFXMMU_BUFFERS_S,         SIZE_16M,           SRAM,        YES,   YES ); // Frame buffer
  SET_REGION( 6, PERIPH_BASE_S,            SIZE_256M,          PERIPHERAL,  YES,   YES ); // Peripherals
  SET_REGION( 7, FLASH_BASE_NS,            SIZE_4M,            FLASH_DATA,  YES,   YES ); //
  // clang-format on
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_bootloader() {
  HAL_MPU_Disable();
  mpu_set_attributes();
  // clang-format off
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, FLASH_BASE_S,             SIZE_64K,           FLASH_DATA,  YES,   YES ); // Secret + Boardloader
  SET_REGION( 1, FLASH_BASE_S + SIZE_64K,  SIZE_128K,          FLASH_CODE,  NO,    YES ); // Bootloader code
  SET_REGION( 2, FLASH_BASE_S + SIZE_192K, SIZE_3904K,         FLASH_DATA,  YES,   YES ); // Storage + Firmware
  SET_REGION( 3, SRAM1_BASE_S,             SIZE_768K,          SRAM,        YES,   YES ); // SRAM1
  SET_REGION( 4, SRAM2_BASE_S + 0x100,     SIZE_1728K - 0x100, SRAM,        YES,   YES ); // SRAM2/3/5 + stack guard
  SET_REGION( 5, GFXMMU_BUFFERS_S,         SIZE_16M,           SRAM,        YES,   YES ); // Frame buffer
  SET_REGION( 6, PERIPH_BASE_S,            SIZE_256M,          PERIPHERAL,  YES,   YES ); // Peripherals
  SET_REGION( 7, FLASH_OTP_BASE,           FLASH_OTP_SIZE,     FLASH_DATA,  YES,   YES ); // OTP
  // clang-format on
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_firmware() {
  HAL_MPU_Disable();
  mpu_set_attributes();
  // clang-format off
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, FLASH_BASE_S + SIZE_192K, SIZE_128K,          FLASH_DATA,  YES,   YES ); // Storage
  SET_REGION( 1, FLASH_BASE_S + SIZE_320K, SIZE_3776K,         FLASH_CODE,   NO,   YES ); // Firmware
  SET_REGION( 2, SRAM1_BASE_S,             SIZE_768K,          SRAM,        YES,   YES ); // SRAM1
  SET_REGION( 3, SRAM2_BASE_S + 0x100,     SIZE_1728K - 0x100, SRAM,        YES,   YES ); // SRAM2/3/5 + stack guard
  SET_REGION( 4, GFXMMU_BUFFERS_S,         SIZE_16M,           SRAM,        YES,   YES ); // Frame buffer
  SET_REGION( 5, PERIPH_BASE_S,            SIZE_256M,          PERIPHERAL,  YES,   YES ); // Peripherals
  SET_REGION( 6, FLASH_OTP_BASE,           FLASH_OTP_SIZE,     FLASH_DATA,  YES,   YES ); // OTP
  DIS_REGION( 7 );
  // clang-format on
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_off(void) { HAL_MPU_Disable(); }
