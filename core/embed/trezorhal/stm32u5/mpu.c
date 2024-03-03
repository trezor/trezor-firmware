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
#include "model.h"
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

static void mpu_set_attributes(void) {
  // Attr[0] - FLASH - Not-Transient, Write-Through, Read Allocation
  MPU->MAIR0 = 0xAA;
  // Attr[1] - SRAM - Non-cacheable
  MPU->MAIR0 |= 0x44 << 8;
  // Attr[2] - Peripherals - nGnRnE
  MPU->MAIR0 |= 0x00 << 16;
  // Attr[3] - FLASH - Non-cacheable
  MPU->MAIR0 |= 0x44 << 24;
}

#define SECRET_START FLASH_BASE
#define SECRET_SIZE SIZE_16K
#define BOARDLOADER_SIZE SIZE_48K
#define BOOTLOADER_SIZE BOOTLOADER_IMAGE_MAXSIZE
#define FIRMWARE_SIZE FIRMWARE_IMAGE_MAXSIZE
#define STORAGE_START \
  (FLASH_BASE + SECRET_SIZE + BOARDLOADER_SIZE + BOOTLOADER_SIZE)
#define STORAGE_SIZE NORCOW_SECTOR_SIZE* STORAGE_AREAS_COUNT

#if defined STM32U5A9xx
#define SRAM_SIZE SIZE_2496K
#elif defined STM32U5G9xx
#define SRAM_SIZE (SIZE_2496K + SIZE_512K)
#elif defined STM32U585xx
#define SRAM_SIZE SIZE_768K
#else
#error "Unknown MCU"
#endif

#define L1_REST_SIZE (FLASH_SIZE - (BOARDLOADER_SIZE + SECRET_SIZE))

#define L2_PREV_SIZE (SECRET_SIZE + BOARDLOADER_SIZE)
#define L2_REST_SIZE \
  (FLASH_SIZE - (BOOTLOADER_SIZE + BOARDLOADER_SIZE + SECRET_SIZE))

#define L3_PREV_SIZE \
  (STORAGE_SIZE + BOOTLOADER_SIZE + BOARDLOADER_SIZE + SECRET_SIZE)

#define ASSETS_START (FIRMWARE_START + FIRMWARE_SIZE)
#define ASSETS_SIZE                                                   \
  (FLASH_SIZE - (FIRMWARE_SIZE + BOOTLOADER_SIZE + BOARDLOADER_SIZE + \
                 SECRET_SIZE + STORAGE_SIZE))

#define L3_PREV_SIZE_BLD (STORAGE_SIZE + BOOTLOADER_SIZE)

#ifdef STM32U585xx
#define GRAPHICS_START FMC_BANK1
#define GRAPHICS_SIZE SIZE_16M
#else
#define GRAPHICS_START GFXMMU_VIRTUAL_BUFFERS_BASE
#define GRAPHICS_SIZE SIZE_16M
#endif

void mpu_config_boardloader(void) {
  HAL_MPU_Disable();
  mpu_set_attributes();
  // clang-format off
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, SECRET_START,             SECRET_SIZE,        FLASH_DATA,  YES,    NO ); // Secret
  SET_REGION( 1, BOARDLOADER_START,        BOARDLOADER_SIZE,   FLASH_CODE,   NO,    NO ); // Boardloader code
  SET_REGION( 2, BOOTLOADER_START,         L1_REST_SIZE,       FLASH_DATA,  YES,    NO ); // Bootloader + Storage + Firmware
  SET_REGION( 3, SRAM1_BASE,               SRAM_SIZE,          SRAM,        YES,    NO ); // SRAM1/2/3/5
  SET_REGION( 4, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,    NO ); // Frame buffer or display interface
  SET_REGION( 5, PERIPH_BASE_NS,           SIZE_512M,          PERIPHERAL,  YES,    NO ); // Peripherals
  DIS_REGION( 6 );
  SET_REGION( 7, SRAM4_BASE,               SIZE_16K,           SRAM,        YES,    NO ); // SRAM4
  // clang-format on
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_bootloader(void) {
  HAL_MPU_Disable();
  mpu_set_attributes();
  // clang-format off
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, SECRET_START,             L2_PREV_SIZE,       FLASH_DATA,  YES,    NO ); // Secret + Boardloader
  SET_REGION( 1, BOOTLOADER_START,         BOOTLOADER_SIZE,    FLASH_CODE,  NO,     NO ); // Bootloader code
  SET_REGION( 2, STORAGE_START,            L2_REST_SIZE,       FLASH_DATA,  YES,    NO ); // Storage + Firmware
  SET_REGION( 3, SRAM1_BASE,               SRAM_SIZE,          SRAM,        YES,    NO ); // SRAM1/2/3/5
  SET_REGION( 4, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,    NO ); // Frame buffer or display interface
  SET_REGION( 5, PERIPH_BASE_NS,           SIZE_512M,          PERIPHERAL,  YES,    NO ); // Peripherals
  SET_REGION( 6, FLASH_OTP_BASE,           FLASH_OTP_SIZE,     FLASH_DATA,  YES,    NO ); // OTP
  SET_REGION( 7, SRAM4_BASE,               SIZE_16K,           SRAM,        YES,    NO ); // SRAM4
  // clang-format on
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_firmware_initial(void) {
  HAL_MPU_Disable();
  mpu_set_attributes();
  // clang-format off
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, BOOTLOADER_START,         L3_PREV_SIZE_BLD,   FLASH_DATA,  YES,   YES ); // Bootloader + Storage
  SET_REGION( 1, FIRMWARE_START,           FIRMWARE_SIZE,      FLASH_CODE,   NO,   YES ); // Firmware
  SET_REGION( 2, ASSETS_START,             ASSETS_SIZE,        FLASH_DATA,  YES,   YES ); // Assets
  SET_REGION( 3, SRAM1_BASE,               SRAM_SIZE,          SRAM,        YES,   YES ); // SRAM1/2/3/5
  SET_REGION( 4, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,   YES ); // Frame buffer or display interface
  SET_REGION( 5, PERIPH_BASE_NS,           SIZE_512M,          PERIPHERAL,  YES,   YES ); // Peripherals
  SET_REGION( 6, FLASH_OTP_BASE,           SIZE_2K,            FLASH_DATA,  YES,   YES ); // OTP
  SET_REGION( 7, SRAM4_BASE,               SIZE_16K,           SRAM,        YES,   YES ); // SRAM4
  // clang-format on
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_firmware(void) {
  HAL_MPU_Disable();
  mpu_set_attributes();
  // clang-format off
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, STORAGE_START,            STORAGE_SIZE,       FLASH_DATA,  YES,   YES ); // Storage
  SET_REGION( 1, FIRMWARE_START,           FIRMWARE_SIZE,      FLASH_CODE,   NO,   YES ); // Firmware
  SET_REGION( 2, ASSETS_START,             ASSETS_SIZE,        FLASH_DATA,  YES,   YES ); // Assets
  SET_REGION( 3, SRAM1_BASE,               SRAM_SIZE,          SRAM,        YES,   YES ); // SRAM1/2/3/5
  SET_REGION( 4, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,   YES ); // Frame buffer or display interface
  SET_REGION( 5, PERIPH_BASE_NS,           SIZE_512M,          PERIPHERAL,  YES,   YES ); // Peripherals
  SET_REGION( 6, FLASH_OTP_BASE,           FLASH_OTP_SIZE,     FLASH_DATA,  YES,   YES ); // OTP
  SET_REGION( 7, SRAM4_BASE,               SIZE_16K,           SRAM,        YES,   YES ); // SRAM4
  // clang-format on
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_prodtest_initial(void) {
  HAL_MPU_Disable();
  mpu_set_attributes();
  // clang-format off
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, FLASH_BASE,               L3_PREV_SIZE,       FLASH_DATA,  YES,   YES ); // Secret, Bld, Storage
  SET_REGION( 1, FIRMWARE_START,           FIRMWARE_SIZE,      FLASH_CODE,   NO,   YES ); // Firmware
  SET_REGION( 2, ASSETS_START,             ASSETS_SIZE,        FLASH_DATA,  YES,   YES ); // Assets
  SET_REGION( 3, SRAM1_BASE,               SRAM_SIZE,          SRAM,        YES,   YES ); // SRAM1/2/3/5
  SET_REGION( 4, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,   YES ); // Frame buffer or display interface
  SET_REGION( 5, PERIPH_BASE_NS,           SIZE_512M,          PERIPHERAL,  YES,   YES ); // Peripherals
  SET_REGION( 6, FLASH_OTP_BASE,           FLASH_OTP_SIZE,     FLASH_DATA,  YES,   YES ); // OTP
  SET_REGION( 7, SRAM4_BASE,               SIZE_16K,           SRAM,        YES,   YES ); // SRAM4
  // clang-format on
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_prodtest(void) {
  HAL_MPU_Disable();
  mpu_set_attributes();
  // clang-format off
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, STORAGE_START,            STORAGE_SIZE,       FLASH_DATA,  YES,   YES ); // Storage
  SET_REGION( 1, FIRMWARE_START,           FIRMWARE_SIZE,      FLASH_CODE,   NO,   YES ); // Firmware
  SET_REGION( 2, ASSETS_START,             ASSETS_SIZE,        FLASH_DATA,  YES,   YES ); // Assets
  SET_REGION( 3, SRAM1_BASE,               SRAM_SIZE,          SRAM,        YES,   YES ); // SRAM1/2/3/5
  SET_REGION( 4, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,   YES ); // Frame buffer or display interface
  SET_REGION( 5, PERIPH_BASE_NS,           SIZE_512M,          PERIPHERAL,  YES,   YES ); // Peripherals
  SET_REGION( 6, FLASH_OTP_BASE,           FLASH_OTP_SIZE,     FLASH_DATA,  YES,   YES ); // OTP
  SET_REGION( 7, SRAM4_BASE,               SIZE_16K,           SRAM,        YES,   YES ); // SRAM4
  // clang-format on
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
}

void mpu_config_off(void) { HAL_MPU_Disable(); }
