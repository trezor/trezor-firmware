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

#include <stdbool.h>
#include <stdint.h>

#include "irq.h"
#include "model.h"
#include "mpu.h"

#include "stm32f4xx_ll_cortex.h"

#ifdef KERNEL_MODE

// http://infocenter.arm.com/help/topic/com.arm.doc.dui0552a/BABDJJGF.html
#define MPU_RASR_ATTR_FLASH_CODE (MPU_RASR_C_Msk)
#define MPU_RASR_ATTR_FLASH_DATA (MPU_RASR_C_Msk | MPU_RASR_XN_Msk)
#define MPU_RASR_ATTR_SRAM (MPU_RASR_C_Msk | MPU_RASR_S_Msk | MPU_RASR_XN_Msk)
#define MPU_RASR_ATTR_PERIPH (MPU_RASR_B_Msk | MPU_RASR_S_Msk | MPU_RASR_XN_Msk)

#define SET_REGION(region, start, size, mask, attr, access) \
  do {                                                      \
    uint32_t _enable = MPU_RASR_ENABLE_Msk;                 \
    uint32_t _size = LL_MPU_REGION_##size;                  \
    uint32_t _mask = (mask) << MPU_RASR_SRD_Pos;            \
    uint32_t _attr = MPU_RASR_ATTR_##attr;                  \
    uint32_t _access = LL_MPU_REGION_##access;              \
    MPU->RNR = region;                                      \
    MPU->RBAR = (start) & ~0x1F;                            \
    MPU->RASR = _enable | _size | _mask | _attr | _access;  \
  } while (0)

#define DIS_REGION(region) \
  do {                     \
    MPU->RNR = region;     \
    MPU->RBAR = 0;         \
    MPU->RASR = 0;         \
  } while (0)

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

#define SRAM_SIZE (192 * 1024)

#define KERNEL_STACK_START (CCMDATARAM_BASE)
#define KERNEL_CCMRAM_START (CCMDATARAM_END + 1 - KERNEL_CCMRAM_SIZE)
#define KERNEL_SRAM_START (SRAM1_BASE + SRAM_SIZE - KERNEL_SRAM_SIZE)

#define KERNEL_CCMRAM_FB_START (KERNEL_CCMRAM_START - KERNEL_FRAMEBUFFER_SIZE)

static void mpu_init_fixed_regions(void) {
  // Regions #0 to #4 are fixed for all targets

#ifdef BOARDLOADER
  // clang-format off
  // Code in the Flash Bank #1 (Unprivileged, Read-Only, Executable)
  // Subregion: 48KB = 64KB except 2/8 at end
  SET_REGION( 0, BOARDLOADER_START,     SIZE_64KB,  0xC0, FLASH_CODE, PRIV_RO_URO );
  // Rest of the code in the Flash Bank #1 (Unprivileged, Read-Only)
  // Subregion: 896KB = 1024KB except 1/8 at start
  SET_REGION( 1, FLASH_BASE,            SIZE_1MB,   0x01, FLASH_DATA, FULL_ACCESS );
  // Rest of the code in the Flash Bank #2 (Unprivileged, Read-Only)
  // Subregion: 896KB = 1024KB except 1/8 at start
  SET_REGION( 2, FLASH_BASE + 0x100000, SIZE_1MB,   0x01, FLASH_DATA, FULL_ACCESS );
  // All CCMRAM (Unprivileged, Read-Write, Non-Executable)
  SET_REGION( 3, CCMDATARAM_BASE,       SIZE_64KB,  0x00, SRAM,       FULL_ACCESS );
  // All SRAM (Unprivileged, Read-Write, Non-Executable)
  // Subregion:  192KB = 256KB except 2/8 at end
  SET_REGION( 4, SRAM_BASE,             SIZE_256KB, 0xC0, SRAM,       FULL_ACCESS );
  // clang-format on
#endif
#ifdef BOOTLOADER
  // clang-format off
  // Bootloader code in the Flash Bank #1 (Unprivileged, Read-Only, Executable)
  // Subregion: 128KB = 1024KB except 2/8 at start
  SET_REGION( 0, BOOTLOADER_START,      SIZE_128KB, 0x00, FLASH_CODE, PRIV_RO_URO );
  // Kernel/coreapp code in the Flash Bank #1 (Unprivileged, Read-Only)
  // Subregion: 768KB = 1024KB except 2/8 at start
  SET_REGION( 1, FLASH_BASE,            SIZE_1MB,   0x03, FLASH_DATA, FULL_ACCESS );
  // Kernel/coreapp code in the Flash Bank #2 (Unprivileged, Read-Only)
  // Subregion: 896KB = 1024KB except 1/8 at start
  SET_REGION( 2, FLASH_BASE + 0x100000, SIZE_1MB,   0x01, FLASH_DATA, FULL_ACCESS );
  // All CCMRAM (Unprivileged, Read-Write, Non-Executable)
  SET_REGION( 3, CCMDATARAM_BASE,       SIZE_64KB,  0x00, SRAM,       FULL_ACCESS );
  // All SRAM (Unprivileged, Read-Write, Non-Executable)
  // Subregion:  192KB = 256KB except 2/8 at end
  SET_REGION( 4, SRAM_BASE,             SIZE_256KB, 0xC0, SRAM,       FULL_ACCESS );
  // clang-format on
#endif
#ifdef KERNEL
  // clang-format off
  // Code in the Flash Bank #1 (Unprivileged, Read-Only, Executable)
  // Subregion: 768KB = 1024KB except 2/8 at start
  SET_REGION( 0, FLASH_BASE,            SIZE_1MB,   0x03, FLASH_CODE, PRIV_RO_URO );
  // Code in the Flash Bank #2 (Unprivileged, Read-Only, Executable)
  // Subregion: 896KB = 1024KB except 1/8 at start
  SET_REGION( 1, FLASH_BASE + 0x100000, SIZE_1MB,   0x01, FLASH_CODE, PRIV_RO_URO );
  // All CCMRAM (Unprivileged, Read-Write, Non-Executable)
  SET_REGION( 2, CCMDATARAM_BASE,       SIZE_64KB,  0x00, SRAM,       FULL_ACCESS );
  // All SRAM (Unprivileged, Read-Write, Non-Executable)
  // Subregion:  192KB = 256KB except 2/8 at end
  SET_REGION( 3, SRAM_BASE,             SIZE_256KB, 0xC0, SRAM,       FULL_ACCESS );
  // Kernel CCMRAM (Privileged, Read-Write, Non-Executable)
  // SubRegion: 8KB at the beginning + 16KB at the end of 64KB CCMRAM
  SET_REGION( 4, CCMDATARAM_BASE,       SIZE_64KB,  0x3E, SRAM,       PRIV_RW );
  // clang-format on
#endif
#ifdef FIRMWARE
  // clang-format off
  // Code in the Flash Bank #1 (Unprivileged, Read-Only, Executable)
  // Subregion: 768KB = 1024KB except 2/8 at start
  SET_REGION( 0, FLASH_BASE,            SIZE_1MB,   0x03, FLASH_CODE, PRIV_RO_URO );
  // Code in the Flash Bank #2 (Unprivileged, Read-Only, Executable)
  // Subregion: 896KB = 1024KB except 1/8 at start
  SET_REGION( 1, FLASH_BASE + 0x100000, SIZE_1MB,   0x01, FLASH_CODE, PRIV_RO_URO );
  // All CCMRAM (Unprivileged, Read-Write, Non-Executable)
  SET_REGION( 2, CCMDATARAM_BASE,       SIZE_64KB,  0x00, SRAM,       FULL_ACCESS );
  // All SRAM (Unprivileged, Read-Write, Non-Executable)
  // Subregion:  192KB = 256KB except 2/8 at end
  SET_REGION( 3, SRAM_BASE,             SIZE_256KB, 0xC0, SRAM,       FULL_ACCESS );
  DIS_REGION( 4 );
  // clang-format on
#endif
#ifdef TREZOR_PRODTEST
  // clang-format off
  // Code in the Flash Bank #1 (Unprivileged, Read-Only, Executable)
  // Subregion: 768KB = 1024KB except 2/8 at start
  SET_REGION( 0, FLASH_BASE,            SIZE_1MB,   0x03, FLASH_CODE, PRIV_RO_URO );
  // Code in the Flash Bank #2 (Unprivileged, Read-Only, Executable)
  // Subregion: 896KB = 1024KB except 1/8 at start
  SET_REGION( 1, FLASH_BASE + 0x100000, SIZE_1MB,   0x01, FLASH_CODE, PRIV_RO_URO );
  // All CCMRAM (Unprivileged, Read-Write, Non-Executable)
  SET_REGION( 2, CCMDATARAM_BASE,       SIZE_64KB,  0x00, SRAM,       FULL_ACCESS );
  // All SRAM (Unprivileged, Read-Write, Non-Executable)
  // Subregion:  192KB = 256KB except 2/8 at end
  SET_REGION( 3, SRAM_BASE,             SIZE_256KB, 0xC0, SRAM,       FULL_ACCESS );
  // Firmware header (Unprivileged, Read-Write, Non-Executable)
  // (used in production test to invalidate the firmware)
  SET_REGION( 4, FIRMWARE_START,        SIZE_1KB,   0x00, FLASH_DATA, PRIV_RW_URO );
  // clang-format on
#endif

  // Regions #5 to #7 are banked
  DIS_REGION(5);
  DIS_REGION(6);
  DIS_REGION(7);
}

void mpu_init(void) {
  mpu_driver_t* drv = &g_mpu_driver;

  if (drv->initialized) {
    return;
  }

  irq_key_t irq_key = irq_lock();

  HAL_MPU_Disable();

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

void mpu_set_unpriv_fb(void* addr, size_t size) {
  // Not implemented on STM32F4
}

// STM32F4xx memory map
//
// 0x08000000  2MB    FLASH
// 0x10000000  64KB   CCMRAM
// 0x1FFF7800  528B   OTP
// 0x20000000  192KB  SRAM
// 0x40000000  512MB  PERIPH

// STM32F4xx flash layout
//
// 0x08000000  4x 16KB  (BANK #1)
// 0x08010000  1x 64KB  (BANK #1)
// 0x08020000  7x 128KB (BANK #1)
// 0x08100000  4x 16KB  (BANK #2)
// 0x08110000  1x 64KB  (BANK #3)
// 0x08120000  7x 128KB (BANK #4)

mpu_mode_t mpu_reconfig(mpu_mode_t mode) {
  mpu_driver_t* drv = &g_mpu_driver;

  if (!drv->initialized) {
    // Solves the issue when some IRQ handler tries to reconfigure
    // MPU before it is initialized
    return MPU_MODE_DISABLED;
  }

  irq_key_t irq_key = irq_lock();

  HAL_MPU_Disable();

  // Region #5 and #6 are banked

  // clang-format off
  switch (mode) {
#if !defined(BOARDLOADER)
    case MPU_MODE_BOARDCAPS:
      DIS_REGION( 5 );
      // Boardloader (Privileged, Read-Only, Non-Executable)
      // Subregion: 48KB = 64KB except 2/8 at end
      SET_REGION( 6, FLASH_BASE,           SIZE_64KB,  0xC0, FLASH_DATA, PRIV_RO );
      break;
#endif

#if !defined(BOARDLOADER) && !defined(BOOTLOADER)
    case MPU_MODE_BOOTUPDATE:
      DIS_REGION( 5 );
      // Bootloader (Privileged, Read-Write, Non-Executable)
      SET_REGION( 6, FLASH_BASE + 0x20000, SIZE_128KB, 0x00, FLASH_DATA, PRIV_RW );
      break;
#endif

    case MPU_MODE_OTP:
      DIS_REGION( 5 );
      // OTP (Privileged, Read-Write, Non-Executable)
      SET_REGION( 6, FLASH_OTP_BASE,        SIZE_1KB,  0x00, FLASH_DATA, FULL_ACCESS );
      break;

    case MPU_MODE_FSMC_REGS:
      DIS_REGION( 5 );
      // FSMC Control Registers (Privileged, Read-Write, Non-Executable)
      // 0xA0000000 = FMSC_R_BASE (not defined in used headers)
      SET_REGION( 6, 0xA0000000,            SIZE_4KB,  0x00, FLASH_DATA, FULL_ACCESS );
      break;

    case MPU_MODE_FLASHOB:
      SET_REGION( 5, 0x1FFFC000,            SIZE_1KB,  0x00, FLASH_DATA, PRIV_RO );
      SET_REGION( 6, 0x1FFEC000,            SIZE_1KB,  0x00, FLASH_DATA, PRIV_RO );
      break;

    case MPU_MODE_STORAGE:
      // Storage in the Flash Bank #1 (Privileged, Read-Write, Non-Executable)
      SET_REGION( 5, FLASH_BASE + 0x10000,  SIZE_64KB, 0x00, FLASH_DATA, PRIV_RW );
      // Storage in the Flash Bank #2 (Privileged, Read-Write, Non-Executable)
      SET_REGION( 6, FLASH_BASE + 0x110000, SIZE_64KB, 0x00, FLASH_DATA, PRIV_RW );
      break;

    case MPU_MODE_KERNEL_SRAM:
      DIS_REGION( 5 );
      // Kernel data in DMA accessible SRAM (Privileged, Read-Write, Non-Executable)
      // (overlaps with unprivileged SRAM region)
      SET_REGION( 6, SRAM_BASE,             SIZE_1KB,  0x00, SRAM, PRIV_RW );
      break;

    case MPU_MODE_UNUSED_FLASH:
      // Unused Flash Area #1 (Privileged, Read-Write, Non-Executable)
      SET_REGION( 5, FLASH_BASE + 0x00C000, SIZE_16KB, 0x00, FLASH_DATA, PRIV_RW );
      // Unused Flash Area #2 (Privileged, Read-Write, Non-Executable)
      SET_REGION( 6, FLASH_BASE + 0x10C000, SIZE_16KB, 0x00, FLASH_DATA, PRIV_RW );
      break;

#ifdef USE_OPTIGA
    // with optiga, we use the secret sector, and assets area is smaller
    case MPU_MODE_SECRET:
      DIS_REGION( 5 );
      // Secret sector in Bank #2 (Privileged, Read-Write, Non-Executable)
      SET_REGION( 6, FLASH_BASE + 0x100000, SIZE_16KB, 0x00, FLASH_DATA, PRIV_RW );
      break;

    case MPU_MODE_ASSETS:
      DIS_REGION( 5 );
      // Assets (Privileged, Read-Write, Non-Executable)
      // Subregion: 32KB = 64KB except 2/8 at start and 2/8 at end
      SET_REGION( 6, FLASH_BASE + 0x104000, SIZE_64KB, 0xC3, FLASH_DATA, PRIV_RW );
      break;

    case MPU_MODE_APP:
      // Kernel data in DMA accessible SRAM (Privileged, Read-Write, Non-Executable)
      // (overlaps with unprivileged SRAM region)
      SET_REGION( 5, SRAM_BASE,             SIZE_1KB,  0x00, SRAM, PRIV_RW );
      // Assets (Unprivileged, Read-Only, Non-Executable)
      // Subregion: 32KB = 64KB except 2/8 at start and 2/8 at end
      SET_REGION( 6, FLASH_BASE + 0x104000, SIZE_64KB, 0xC3, FLASH_DATA, PRIV_RO_URO );
      break;

#else
    // without optiga, we use additional sector for assets area
    case MPU_MODE_ASSETS:
      DIS_REGION( 5 );
      // Assets (Privileged, Read-Write, Non-Executable)
      // Subregion: 48KB = 64KB except 2/8 at end
      SET_REGION( 6, FLASH_BASE + 0x100000, SIZE_64KB, 0xC0, FLASH_DATA, PRIV_RW );
      break;

    case MPU_MODE_APP:
      // Kernel data in DMA accessible SRAM (Privileged, Read-Write, Non-Executable)
      // (overlaps with unprivileged SRAM region)
      SET_REGION( 5, SRAM_BASE,             SIZE_1KB,  0x00, SRAM, PRIV_RW );
      // Assets (Unprivileged, Read-Only, Non-Executable)
      // Subregion: 48KB = 64KB except 2/8 at end
      SET_REGION( 6, FLASH_BASE + 0x100000, SIZE_64KB, 0xC0, FLASH_DATA, PRIV_RO_URO );
      break;

#endif

    default:
      DIS_REGION( 5 );
      DIS_REGION( 6 );
      break;
  }
  // clang-format on

  // Region #7 is banked

  // clang-format off
  switch (mode) {
#ifdef TREZOR_MODEL_DISC1
    default:
      // All Peripherals (Unprivileged, Read-Write, Non-Executable)
      // SDRAM
      SET_REGION( 7, 0x00000000,            SIZE_4GB,  0xBB, SRAM,     FULL_ACCESS );
    break;
#else
    case MPU_MODE_APP:
      // Dma2D (Unprivileged, Read-Write, Non-Executable)
      // 3KB = 4KB except 1/4 at end
      SET_REGION( 7, 0x4002B000,            SIZE_4KB,  0xC0, PERIPH,     FULL_ACCESS );
      break;
    default:
      // All Peripherals (Privileged, Read-Write, Non-Executable)
      SET_REGION( 7, PERIPH_BASE,           SIZE_1GB,  0x00, PERIPH,     PRIV_RW );
      break;
#endif
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
