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
#include "irq.h"
#include "model.h"
#include "mpu.h"

#include "stm32u5xx_ll_cortex.h"

#ifdef KERNEL_MODE

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
#define BOARDLOADER_SIZE BOARDLOADER_IMAGE_MAXSIZE
#define BOOTLOADER_SIZE BOOTLOADER_IMAGE_MAXSIZE
#define FIRMWARE_SIZE FIRMWARE_IMAGE_MAXSIZE
#define STORAGE_START \
  (FLASH_BASE + SECRET_SIZE + BOARDLOADER_SIZE + BOOTLOADER_SIZE)
#define STORAGE_SIZE NORCOW_SECTOR_SIZE* STORAGE_AREAS_COUNT

#if defined STM32U5A9xx
#define SRAM_SIZE SRAM1_SIZE + SRAM2_SIZE + SRAM3_SIZE + SRAM5_SIZE
#elif defined STM32U5G9xx
#define SRAM_SIZE SRAM1_SIZE + SRAM2_SIZE + SRAM3_SIZE + SRAM5_SIZE + SRAM6_SIZE
#elif defined STM32U585xx
#define SRAM_SIZE SRAM1_SIZE + SRAM2_SIZE + SRAM3_SIZE
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

#define OTP_AND_ID_SIZE 0x800

// clang-format on

#define KERNEL_RAM_START (SRAM2_BASE - KERNEL_SRAM1_SIZE)
#define KERNEL_RAM_SIZE \
  ((KERNEL_SRAM1_SIZE + KERNEL_SRAM2_SIZE) - KERNEL_U_RAM_SIZE)

#ifdef SYSCALL_DISPATCH
extern uint32_t _uflash_start;
extern uint32_t _uflash_end;
#define KERNEL_RAM_U_START (KERNEL_RAM_START + KERNEL_RAM_SIZE)
#define KERNEL_RAM_U_SIZE KERNEL_U_RAM_SIZE
#define KERNEL_FLASH_U_START (uint32_t) & _uflash_start
#define KERNEL_FLASH_U_SIZE ((uint32_t) & _uflash_end - KERNEL_FLASH_U_START)
#else
#define KERNEL_RAM_U_START 0
#define KERNEL_RAM_U_SIZE 0
#define KERNEL_FLASH_U_START 0
#define KERNEL_FLASH_U_SIZE 0
#endif

extern uint32_t _codelen;
#define KERNEL_SIZE (uint32_t) & _codelen

#define KERNEL_FLASH_START KERNEL_START
#define KERNEL_FLASH_SIZE (KERNEL_SIZE - KERNEL_U_FLASH_SIZE)

#define COREAPP_FLASH_START (KERNEL_FLASH_START + KERNEL_SIZE)
#define COREAPP_FLASH_SIZE (FIRMWARE_IMAGE_MAXSIZE - KERNEL_SIZE)

#define COREAPP_RAM1_START SRAM1_BASE
#define COREAPP_RAM1_SIZE (SRAM1_SIZE - KERNEL_SRAM1_SIZE)

#define COREAPP_RAM2_START (SRAM2_BASE + KERNEL_SRAM2_SIZE)
#define COREAPP_RAM2_SIZE (SRAM_SIZE - (SRAM1_SIZE + KERNEL_SRAM2_SIZE))

typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Current mode
  mpu_mode_t mode;

} mpu_driver_t;

mpu_driver_t g_mpu_driver = {
    .initialized = false,
    .mode = MPU_MODE_DISABLED,
};

static void mpu_init_fixed_regions(void) {
  // Regions #0 to #5 are fixed for all targets

  // clang-format off
#if defined(BOARDLOADER)
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, BOARDLOADER_START,        BOARDLOADER_SIZE,   FLASH_CODE,   NO,    NO );
  SET_REGION( 1, SRAM1_BASE,               SRAM_SIZE,          SRAM,        YES,    NO );
  DIS_REGION( 2 );
  DIS_REGION( 3 );
  DIS_REGION( 4 );
  SET_REGION( 5, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,    NO );
#endif
#if defined(BOOTLOADER)
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, BOOTLOADER_START,         BOOTLOADER_SIZE,    FLASH_CODE,  NO,     NO );
  SET_REGION( 1, SRAM1_BASE,               SRAM_SIZE,          SRAM,        YES,    NO );
  DIS_REGION( 2 );
  DIS_REGION( 3 );
  DIS_REGION( 4 );
  SET_REGION( 5, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,    NO );
#endif
#if defined(KERNEL)
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, KERNEL_FLASH_START,       KERNEL_FLASH_SIZE,  FLASH_CODE,   NO,    NO ); // Kernel Code
  SET_REGION( 1, KERNEL_RAM_START,         KERNEL_RAM_SIZE,    SRAM,        YES,    NO ); // Kernel RAM
  SET_REGION( 2, COREAPP_FLASH_START,      COREAPP_FLASH_SIZE, FLASH_CODE,   NO,   YES ); // CoreApp Code
  SET_REGION( 3, COREAPP_RAM1_START,       COREAPP_RAM1_SIZE,  SRAM,        YES,   YES ); // SRAM1
  SET_REGION( 4, COREAPP_RAM2_START,       COREAPP_RAM2_SIZE,  SRAM,        YES,   YES ); // SRAM2/3/5
  SET_REGION( 5, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,   YES ); // Frame buffer or display interface
#endif
#if defined(FIRMWARE)
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, FIRMWARE_START,           FIRMWARE_SIZE,      FLASH_CODE,   NO,    NO );
  SET_REGION( 1, SRAM1_BASE,               SRAM_SIZE,          SRAM,        YES,    NO );
  DIS_REGION( 2 );
  DIS_REGION( 3 );
  DIS_REGION( 4 );
  SET_REGION( 5, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,    NO );
#endif
#if defined(PRODTEST)
  SET_REGION( 0, FIRMWARE_START,           FIRMWARE_SIZE,      FLASH_CODE,   NO,    NO );
  SET_REGION( 1, SRAM1_BASE,               SRAM_SIZE,          SRAM,        YES,    NO );
  DIS_REGION( 2 );
  DIS_REGION( 3 );
  DIS_REGION( 4 );
  SET_REGION( 5, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,        YES,    NO );
#endif

  // Regions #6 and #7 are banked

  DIS_REGION( 6 );
  DIS_REGION( 7 );
  // clang-format on
}

void mpu_init(void) {
  mpu_driver_t* drv = &g_mpu_driver;

  if (drv->initialized) {
    return;
  }

  irq_key_t irq_key = irq_lock();

  HAL_MPU_Disable();

  mpu_set_attributes();

  mpu_init_fixed_regions();

  drv->mode = MPU_MODE_DISABLED;
  drv->initialized = true;

  irq_unlock(irq_key);
}

mpu_mode_t mpu_get_mode(void) {
  mpu_driver_t* drv = &g_mpu_driver;

  if (!drv->initialized) {
    return MPU_MODE_DISABLED;
  }

  return drv->mode;
}

mpu_mode_t mpu_reconfig(mpu_mode_t mode) {
  mpu_driver_t* drv = &g_mpu_driver;

  if (!drv->initialized) {
    // Solves the issue when some IRQ handler tries to reconfigure
    // MPU before it is initialized
    return MPU_MODE_DISABLED;
  }

  irq_key_t irq_key = irq_lock();

  HAL_MPU_Disable();

  // Region #5 is banked

  // clang-format off
  switch (mode) {
    case MPU_MODE_SAES:
      SET_REGION( 5, PERIPH_BASE_NS,           SIZE_512M,          PERIPHERAL,  YES,   YES ); // Peripherals - SAES, TAMP
      break;
    default:
      SET_REGION( 5, GRAPHICS_START,           GRAPHICS_SIZE,      SRAM,  YES,    YES ); // Frame buffer or display interface
      break;
  }
  // clang-format on

  // Region #6 is banked

  // clang-format off
  switch (mode) {
    case MPU_MODE_DISABLED:
      break;
    case MPU_MODE_BOARDCAPS:
      //      REGION   ADDRESS                 SIZE                TYPE       WRITE   UNPRIV
      SET_REGION( 6, BOARDLOADER_START,        BOARDLOADER_SIZE,   FLASH_DATA,   NO,    NO );
      break;
    case MPU_MODE_BOOTUPDATE:
      SET_REGION( 6, BOOTLOADER_START,         BOOTLOADER_SIZE,    FLASH_DATA,  YES,    NO );
      break;
    case MPU_MODE_OTP:
      SET_REGION( 6, FLASH_OTP_BASE,           OTP_AND_ID_SIZE,    FLASH_DATA,   NO,    NO );
      break;
    case MPU_MODE_SECRET:
      SET_REGION( 6, SECRET_START,             SECRET_SIZE,        FLASH_DATA,  YES,    NO );
      break;
    case MPU_MODE_STORAGE:
      SET_REGION( 6, STORAGE_START,            STORAGE_SIZE,       FLASH_DATA,  YES,    NO );
      break;
    case MPU_MODE_ASSETS:
      SET_REGION( 6, ASSETS_START,             ASSETS_SIZE,        FLASH_DATA,  YES,    NO );
      break;
    case MPU_MODE_SAES:
      SET_REGION( 6, KERNEL_FLASH_U_START,     KERNEL_FLASH_U_SIZE,FLASH_CODE,   NO,   YES ); // Unprivileged kernal flash
      break;
    case MPU_MODE_APP:
      SET_REGION( 6, ASSETS_START,             ASSETS_SIZE,        FLASH_DATA,   NO,   YES );
      break;
    case MPU_MODE_DEFAULT:
    case MPU_MODE_FSMC_REGS:
    default:
      DIS_REGION( 6 );
      break;
  }
  // clang-format on

  // Region #7 is banked

  // clang-format off
  switch (mode) {
      //      REGION   ADDRESS                 SIZE                TYPE       WRITE   UNPRIV
    case MPU_MODE_SAES:
      SET_REGION( 7, KERNEL_RAM_U_START,       KERNEL_RAM_U_SIZE,  SRAM,        YES,   YES ); // Unprivileged kernel SRAM
      break;
    case MPU_MODE_APP:
      // DMA2D peripherals (Uprivileged, Read-Write, Non-Executable)
      SET_REGION( 7, 0x5002B000,               SIZE_3K,            PERIPHERAL,  YES,   YES );
      break;
    default:
      // All peripherals (Pivileged, Read-Write, Non-Executable)
      SET_REGION( 7, PERIPH_BASE_NS,           SIZE_512M,          PERIPHERAL,  YES,    NO );
      break;
  }
  // clang-format on

  if (mode != MPU_MODE_DISABLED) {
    HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);
  }

  mpu_mode_t prev_mode = drv->mode;
  drv->mode = mode;

  irq_unlock(irq_key);

  return prev_mode;
}

void mpu_restore(mpu_mode_t mode) { mpu_reconfig(mode); }

#endif  // KERNEL_MODE
