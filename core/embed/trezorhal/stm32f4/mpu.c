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

/*
#define MPU_SUBREGION_DISABLE(X) ((X) << MPU_RASR_SRD_Pos)

void mpu_config_boardloader(void) {
  // nothing to be done
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
*/
/*
void mpu_config_firmware_initial(void) {}

void mpu_config_firmware(void) {
  // Disable MPU
  HAL_MPU_Disable();

  // Note: later entries overwrite previous ones
*/
/*
    // Boardloader (0x08000000 - 0x0800FFFF, 64 KiB, read-only, execute never)
    MPU->RBAR = FLASH_BASE | MPU_REGION_NUMBER0;
    MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
   LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_PRIV_RO_URO | MPU_RASR_XN_Msk;
*/
/*
  // Bootloader (0x08020000 - 0x0803FFFF, 128 KiB, read-only)
  MPU->RNR = MPU_REGION_NUMBER0;
  MPU->RBAR = FLASH_BASE + 0x20000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_128KB | LL_MPU_REGION_PRIV_RO_URO;

  // Storage#1 (0x08010000 - 0x0801FFFF, 64 KiB, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER1;
  MPU->RBAR = FLASH_BASE + 0x10000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;

#ifdef USE_OPTIGA
  // Translations + Storage#2 - secret (0x08104000 - 0x0811FFFF, 112 KiB,
  // read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER2;
  MPU->RBAR = FLASH_BASE + 0x100000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_128KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk | MPU_SUBREGION_DISABLE(0x01);
#else
  // Translations + Storage#2 (0x08100000 - 0x0811FFFF, 128 KiB, read-write,
  // execute never)
  MPU->RNR = MPU_REGION_NUMBER2;
  MPU->RBAR = FLASH_BASE + 0x100000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_128KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;
#endif

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

void mpu_config_prodtest_initial(void) {}

void mpu_config_prodtest(void) {
  // Disable MPU
  HAL_MPU_Disable();

  // Note: later entries overwrite previous ones

  //  // Boardloader (0x08000000 - 0x0800BFFF, 48 KiB, read-only, execute never)
  //  MPU->RNR = MPU_REGION_NUMBER0;
  //  MPU->RBAR = FLASH_BASE;
  //  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
  //              LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_PRIV_RO_URO |
  //              MPU_RASR_XN_Msk | MPU_SUBREGION_DISABLE(0xC0);

  // Secret area (0x08100000 - 0x08103FFF, 16 KiB, read-write, execute never)
  //  MPU->RNR = MPU_REGION_NUMBER0;
  //  MPU->RBAR = FLASH_BASE + 0x100000;
  //  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
  //              LL_MPU_REGION_SIZE_16KB | LL_MPU_REGION_FULL_ACCESS |
  //              MPU_RASR_XN_Msk;

  // Bootloader (0x08020000 - 0x0803FFFF, 64 KiB, read-only)
  MPU->RNR = MPU_REGION_NUMBER1;
  MPU->RBAR = FLASH_BASE + 0x20000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_PRIV_RO_URO;

  // Firmware (0x08040000 - 0x080FFFFF, 6 * 128 KiB = 1024 KiB except 2/8 at
  // start = 768 KiB, read-only)
  MPU->RNR = MPU_REGION_NUMBER2;
  MPU->RBAR = FLASH_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_1MB | LL_MPU_REGION_FULL_ACCESS |
              MPU_SUBREGION_DISABLE(0x03);

  // Firmware extra (0x08120000 - 0x081FFFFF, 7 * 128 KiB = 1024 KiB except 1/8
  // at start = 896 KiB, read-only)
  MPU->RNR = MPU_REGION_NUMBER3;
  MPU->RBAR = FLASH_BASE + 0x100000;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_1MB | LL_MPU_REGION_FULL_ACCESS |
              MPU_SUBREGION_DISABLE(0x01);

  // SRAM (0x20000000 - 0x2002FFFF, 192 KiB = 256 KiB except 2/8 at end,
  // read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER4;
  MPU->RBAR = SRAM_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_SRAM |
              LL_MPU_REGION_SIZE_256KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk | MPU_SUBREGION_DISABLE(0xC0);

#ifdef USE_SDRAM
  // Peripherals (0x40000000 - 0x5FFFFFFF, read-write, execute never)
  // SDRAM (0xC0000000 - 0xDFFFFFFF, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER5;
  MPU->RBAR = 0;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_PERIPH |
              LL_MPU_REGION_SIZE_4GB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk | MPU_SUBREGION_DISABLE(0xBB);
#else
  // Peripherals (0x40000000 - 0x5FFFFFFF, read-write, execute never)
  // External RAM (0x60000000 - 0x7FFFFFFF, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER5;
  MPU->RBAR = PERIPH_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_PERIPH |
              LL_MPU_REGION_SIZE_1GB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;
#endif

#if defined STM32F427xx || defined STM32F429xx
  // CCMRAM (0x10000000 - 0x1000FFFF, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER6;
  MPU->RBAR = CCMDATARAM_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_SRAM |
              LL_MPU_REGION_SIZE_64KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;
#elif STM32F405xx
  // no CCMRAM
#else
#error Unsupported MCU
#endif

  // OTP (0x1FFF7800 - 0x1FFF7C00, read-write, execute never)
  MPU->RNR = MPU_REGION_NUMBER7;
  MPU->RBAR = FLASH_OTP_BASE;
  MPU->RASR = MPU_RASR_ENABLE_Msk | MPU_RASR_ATTR_FLASH |
              LL_MPU_REGION_SIZE_1KB | LL_MPU_REGION_FULL_ACCESS |
              MPU_RASR_XN_Msk;

  // Enable MPU
  HAL_MPU_Enable(LL_MPU_CTRL_HARDFAULT_NMI);

  __asm__ volatile("dsb");
  __asm__ volatile("isb");
}
*/

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
  // Regions #0 to #4 are fixed for all targets

#ifdef BOARDLOADER
  // clang-format off
  // Code in the Flash Bank #1 (Unprivileged, Read-Only, Executable)
  // Subregion: 48KB = 64KB except 2/8 at end
  SET_REGION( 0, BOARDLOADER_START,     SIZE_2MB,   0xC0, FLASH_CODE, PRIV_RO_URO );
  DIS_REGION( 1 );
  // All CCMRAM (Unprivileged, Read-Write, Non-Executable)
  SET_REGION( 2, CCMDATARAM_BASE,       SIZE_64KB,  0x00, SRAM,       FULL_ACCESS );
  // All SRAM (Unprivileged, Read-Write, Non-Executable)
  // Subregion:  192KB = 256KB except 2/8 at end
  SET_REGION( 3, SRAM_BASE,             SIZE_256KB, 0xC0, SRAM,       FULL_ACCESS );
  // Kernel RAM (Privileged, Read-Write, Non-Executable)
  // SET_REGION( 4, ...,                   SIZE_xxx,   0xXX, ATTR_SRAM,   PRIV_RW );
  DIS_REGION( 4 );
  // clang-format on
#endif
#ifdef BOOTLOADER
  // clang-format off
  // Code in the Flash Bank #1 (Unprivileged, Read-Only, Executable)
  // Subregion: 128KB = 1024KB except 2/8 at start
  SET_REGION( 0, BOARDLOADER_START,      SIZE_2MB,   0x00, FLASH_CODE, PRIV_RO_URO );
  DIS_REGION( 1 );
  // All CCMRAM (Unprivileged, Read-Write, Non-Executable)
  SET_REGION( 2, CCMDATARAM_BASE,       SIZE_64KB,  0x00, SRAM,       FULL_ACCESS );
  // All SRAM (Unprivileged, Read-Write, Non-Executable)
  // Subregion:  192KB = 256KB except 2/8 at end
  SET_REGION( 3, SRAM_BASE,             SIZE_256KB, 0xC0, SRAM,       FULL_ACCESS );
  // Kernel RAM (Privileged, Read-Write, Non-Executable)
  // SET_REGION( 4, ...,                   SIZE_xxx,   0xXX, ATTR_SRAM,   PRIV_RW );
  DIS_REGION( 4 );
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
  // Kernel RAM (Privileged, Read-Write, Non-Executable)
  // SET_REGION( 4, ...,                   SIZE_xxx,   0xXX, ATTR_SRAM,   PRIV_RW );
  DIS_REGION( 4 );
  // clang-format on
#endif
#ifdef FIRMWARE
  // TODO
#endif
#ifdef PRODTEST
  // TODO
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
    case MPU_MODE_BOARDCAPS:
      DIS_REGION( 5 );
      // Boardloader (Privileged, Read-Only, Non-Executable)
      // Subregion: 48KB = 64KB except 2/8 at end
      SET_REGION( 6, FLASH_BASE,           SIZE_64KB,  0xC0, FLASH_DATA, PRIV_RO );
      break;

    case MPU_MODE_BOOTUPDATE:
      DIS_REGION( 5 );
      // Bootloader (Privileged, Read-Write, Non-Executable)
      SET_REGION( 6, FLASH_BASE + 0x20000, SIZE_128KB, 0x00, FLASH_DATA, PRIV_RW );
      break;

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
      SET_REGION( 6, FLASH_BASE + 0x108000, SIZE_32KB, 0x00, FLASH_DATA, PRIV_RW );
      break;

    case MPU_MODE_APP:
      // Unused (maybe privileged kernel code in the future)
      DIS_REGION( 5 );
      // Assets (Unprivileged, Read-Only, Non-Executable)
      SET_REGION( 6, FLASH_BASE + 0x108000, SIZE_32KB, 0x00, FLASH_DATA, PRIV_RO_URO );
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
      // Unused (maybe privileged kernel code in the future)
      DIS_REGION( 5 );
      // Assets (Unprivileged, Read-Only, Non-Executable)
      // Subregion: 48KB = 64KB except 2/8 at end
      SET_REGION( 6, FLASH_BASE + 0x100000, SIZE_64KB, 0xC0, FLASH_DATA, PRIV_RO_URO );
      break;

#endif

    case MPU_MODE_STORAGE:
      // Storage in the Flash Bank #1 (Privileged, Read-Write, Non-Executable)
      SET_REGION( 5, FLASH_BASE + 0x10000,  SIZE_64KB, 0x00, FLASH_DATA, PRIV_RW );
      // Storage in the Flash Bank #2 (Privileged, Read-Write, Non-Executable)
      SET_REGION( 6, FLASH_BASE + 0x110000, SIZE_64KB, 0x00, FLASH_DATA, PRIV_RW );
      break;



    case MPU_MODE_DEFAULT:
    default:
      DIS_REGION( 5 );
      DIS_REGION( 6 );
      break;
  }
  // clang-format on

  // Region #7 is banked

  // clang-format off
  switch (mode) {
    case MPU_MODE_APP:
      // Dma2D (Unprivileged, Read-Write, Non-Executable)
      // 3KB = 4KB except 1/4 at end
      SET_REGION( 7, 0x4002B000,            SIZE_4KB,  0xC0, PERIPH,     FULL_ACCESS );
      break;
    default:
      // All Peripherals (Privileged, Read-Write, Non-Executable)
      SET_REGION( 7, PERIPH_BASE,           SIZE_1GB,  0x00, PERIPH,     PRIV_RW );
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
