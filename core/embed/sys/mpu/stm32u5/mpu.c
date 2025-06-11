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

// Turning off the stack protector for this file significantly improves
// the performance of the syscall dispatching and interrupt handling.
#pragma GCC optimize("no-stack-protector")

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <rtl/sizedefs.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <util/image.h>

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
    ENSURE_ALIGNMENT(start, 32);                             \
    ENSURE_ALIGNMENT(size, 32);                              \
    SET_REGRUN(region, start, size, type, write, unpriv);    \
  } while (0)

// `SET_REGION` variant without static assert that can be used when
// start or size are not compile-time constants
#define SET_REGRUN(region, start, size, type, write, unpriv) \
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

#define STORAGE_SIZE NORCOW_SECTOR_SIZE* STORAGE_AREAS_COUNT
_Static_assert(NORCOW_SECTOR_SIZE == STORAGE_1_MAXSIZE, "norcow misconfigured");
_Static_assert(NORCOW_SECTOR_SIZE == STORAGE_2_MAXSIZE, "norcow misconfigured");

// PERIPH_SIZE covers secure peripherals only (+16MB of FMC1)
// PERIPH_SIZE_EXT covers both secure and non-secure peripherals (+16MB of FMC1)
// The extended size is used in a special case - MPU_MODE_OTP - when access
// to non-secure FLASH controller registers is required.

#ifdef STM32U585xx
// On STM32U585, we need to add an additional 16M for FMC1 which
// follows the peripherals in the memory map.

#define PERIPH_SIZE (SIZE_256M + SIZE_16M)
#define PERIPH_SIZE_EXT (SIZE_512M + SIZE_16M)
#else
#define PERIPH_SIZE SIZE_256M
#define PERIPH_SIZE_EXT SIZE_512M
#endif

#define OTP_AND_ID_SIZE 0x800

#ifdef SECMON
extern uint32_t _codelen;
#define SECMON_START FIRMWARE_START_S
#define SECMON_SIZE (uint32_t) & _codelen
#endif

#ifdef KERNEL
extern uint32_t _kernel_flash_start;
extern uint32_t _kernel_flash_end;

#ifdef USE_SECMON_LAYOUT
#define KERNEL_START ((uint32_t) & _kernel_flash_start)
#else
#define KERNEL_START FIRMWARE_START
#endif

#define KERNEL_END ((uint32_t) & _kernel_flash_end)
#define KERNEL_SIZE (KERNEL_END - KERNEL_START)
#endif  // KERNEL

typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Current mode
  mpu_mode_t mode;
  // Address of the active framebuffer
  // (if set to 0, the framebuffer is not accessible)
  uint32_t active_fb_addr;
  // Size of the framebuffer in bytes
  size_t active_fb_size;

} mpu_driver_t;

mpu_driver_t g_mpu_driver = {
    .initialized = false,
    .mode = MPU_MODE_DISABLED,
};

static inline void mpu_disable(void) {
  __DMB();
  SCB->SHCSR &= ~SCB_SHCSR_MEMFAULTENA_Msk;
  MPU->CTRL = 0;
}

static inline void mpu_enable(void) {
  MPU->CTRL = LL_MPU_CTRL_HARDFAULT_NMI | MPU_CTRL_ENABLE_Msk;
  SCB->SHCSR |= SCB_SHCSR_MEMFAULTENA_Msk;
  __DSB();
  __ISB();
}

static void mpu_init_fixed_regions(void) {
  // Regions #0 to #4 are fixed for all targets

  // clang-format off
#if defined(BOARDLOADER)
  //   REGION    ADDRESS                   SIZE                 TYPE       WRITE   UNPRIV
  SET_REGION( 0, BOARDLOADER_START,        BOARDLOADER_MAXSIZE, FLASH_CODE,   NO,    NO );
  SET_REGION( 1, MAIN_RAM_START,           MAIN_RAM_SIZE,       SRAM,        YES,    NO );
  SET_REGION( 2, BOOTLOADER_START,         BOOTLOADER_MAXSIZE,  FLASH_DATA,  YES,    NO );
  SET_REGION( 3, FIRMWARE_START,           FIRMWARE_MAXSIZE,    FLASH_DATA,  YES,    NO );
  SET_REGION( 4, AUX1_RAM_START,           AUX1_RAM_SIZE,       SRAM,        YES,    NO );
#elif defined(BOOTLOADER)
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, BOOTLOADER_START,         BOOTLOADER_MAXSIZE, FLASH_CODE,   NO,    NO );
  SET_REGION( 1, MAIN_RAM_START,           MAIN_RAM_SIZE,      SRAM,        YES,    NO );
  SET_REGION( 2, FIRMWARE_START,           FIRMWARE_MAXSIZE,   FLASH_DATA,  YES,    NO );
  DIS_REGION( 3 );
  SET_REGION( 4, AUX1_RAM_START,           AUX1_RAM_SIZE ,     SRAM,        YES,    NO );
#elif defined(KERNEL)
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGRUN( 0, KERNEL_START,             KERNEL_SIZE,        FLASH_CODE,   NO,    NO ); // Kernel Code
  SET_REGION( 1, MAIN_RAM_START,           MAIN_RAM_SIZE,      SRAM,        YES,    NO ); // Kernel RAM
  DIS_REGION( 2 ); // reserved for applets
  DIS_REGION( 3 ); // reserved for applets
  DIS_REGION( 4 ); // reserved for applets

#elif defined(FIRMWARE)
  //   REGION    ADDRESS                   SIZE                TYPE       WRITE   UNPRIV
  SET_REGION( 0, FIRMWARE_START,           FIRMWARE_MAXSIZE,   FLASH_CODE,   NO,    NO );
  SET_REGION( 1, MAIN_RAM_START,           MAIN_RAM_SIZE,      SRAM,        YES,    NO );
  DIS_REGION( 2 );
  DIS_REGION( 3 );
  SET_REGION( 4, AUX1_RAM_START,           AUX1_RAM_SIZE,      SRAM,        YES,    NO );
#elif defined(TREZOR_PRODTEST)
  SET_REGION( 0, FIRMWARE_START,           1024,               FLASH_DATA,  YES,    NO );
  SET_REGION( 1, FIRMWARE_START + 1024,    FIRMWARE_MAXSIZE - 1024, FLASH_CODE,   NO,    NO );
  SET_REGION( 2, MAIN_RAM_START,           MAIN_RAM_SIZE,     SRAM,        YES,    NO );
  DIS_REGION( 3 );
  SET_REGION( 4, AUX1_RAM_START,           AUX1_RAM_SIZE,     SRAM,        YES,    NO );

#elif defined(SECMON)
  SET_REGRUN( 0, SECMON_START,             SECMON_SIZE,       FLASH_CODE,   NO,    NO );
  SET_REGION( 1, SECMON_RAM_START,         SECMON_RAM_SIZE,   SRAM,        YES,    NO );
  SET_REGION( 2, MAIN_RAM_START,           MAIN_RAM_SIZE,     SRAM,        YES,    NO );
  SET_REGION( 3, FIRMWARE_START,           FIRMWARE_MAXSIZE,  FLASH_DATA,  YES,    NO );
  SET_REGION( 4, AUX1_RAM_START,           AUX1_RAM_SIZE,     SRAM,        YES,    NO );
#else
  #error "Unknown build target"
#endif

  // Regions #5 to #7 are banked

  DIS_REGION( 5 );
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

  mpu_disable();

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

void mpu_set_active_applet(applet_layout_t* layout) {
  mpu_driver_t* drv = &g_mpu_driver;

  if (!drv->initialized) {
    return;
  }

  irq_key_t irq_key = irq_lock();

  mpu_disable();

  if (layout != NULL) {
    // clang-format off
    if (layout->code1.start != 0 && layout->code1.size != 0) {
      SET_REGRUN( 2, layout->code1.start, layout->code1.size, FLASH_CODE, NO, YES );
    } else {
      DIS_REGION( 2 );
    }

    if (layout->data1.start != 0 && layout->data1.size != 0) {
      SET_REGRUN( 3, layout->data1.start, layout->data1.size, SRAM, YES, YES );
    } else {
      DIS_REGION( 3 );
    }

    if (layout->data2.start != 0 && layout->data2.size != 0) {
      SET_REGRUN( 4, layout->data2.start, layout->data2.size, SRAM, YES, YES );
    } else {
      DIS_REGION( 4 );
    }
    // clang-format on
  } else {
    DIS_REGION(2);
    DIS_REGION(3);
    DIS_REGION(4);
  }

  if (drv->mode != MPU_MODE_DISABLED) {
    mpu_enable();
  }

  irq_unlock(irq_key);
}

void mpu_set_active_fb(const void* addr, size_t size) {
  mpu_driver_t* drv = &g_mpu_driver;

  if (!drv->initialized) {
    return;
  }

  irq_key_t lock = irq_lock();

  drv->active_fb_addr = (uint32_t)addr;
  drv->active_fb_size = size;

  irq_unlock(lock);

  mpu_reconfig(drv->mode);
}

bool mpu_inside_active_fb(const void* addr, size_t size) {
  mpu_driver_t* drv = &g_mpu_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t lock = irq_lock();

  bool result =
      ((uintptr_t)addr + size >= (uintptr_t)addr) &&  // overflow check
      ((uintptr_t)addr >= drv->active_fb_addr) &&
      ((uintptr_t)addr + size <= drv->active_fb_addr + drv->active_fb_size);

  irq_unlock(lock);

  return result;
}

mpu_mode_t mpu_reconfig(mpu_mode_t mode) {
  mpu_driver_t* drv = &g_mpu_driver;

  if (!drv->initialized) {
    // Solves the issue when some IRQ handler tries to reconfigure
    // MPU before it is initialized
    return MPU_MODE_DISABLED;
  }

  irq_key_t irq_key = irq_lock();

  mpu_disable();

  // Region #5 is banked

  // clang-format off
  switch (mode) {
    case MPU_MODE_APP_SAES:
    case MPU_MODE_APP:
      if (drv->active_fb_addr != 0) {
        SET_REGRUN( 5, drv->active_fb_addr,    drv->active_fb_size,   SRAM,        YES,    YES ); // Frame buffer
      } else {
        DIS_REGION( 5 );
      }
      break;
    default:
      if (drv->active_fb_addr != 0) {
        SET_REGRUN( 5, drv->active_fb_addr,    drv->active_fb_size,   SRAM,        YES,    NO ); // Frame buffer
      } else {
        DIS_REGION( 5 );
      }
      break;
  }
  // clang-format on

  // Region #6 is banked

  // clang-format off
  switch (mode) {
    case MPU_MODE_DISABLED:
      break;
#if !defined(BOARDLOADER)
    case MPU_MODE_BOARDCAPS:
      //      REGION   ADDRESS                 SIZE                TYPE       WRITE   UNPRIV
      SET_REGION( 6, BOARDLOADER_START,        BOARDLOADER_MAXSIZE,FLASH_DATA,   NO,    NO );
      break;
#endif
#if !defined(BOOTLOADER) && !defined(BOARDLOADER)
    case MPU_MODE_BOOTUPDATE:
      SET_REGION( 6, BOOTLOADER_START,         BOOTLOADER_MAXSIZE, FLASH_DATA,  YES,    NO );
      break;
#endif
    case MPU_MODE_OTP:
      SET_REGION( 6, FLASH_OTP_BASE,           OTP_AND_ID_SIZE,    FLASH_DATA,  YES,    NO );
      break;
    case MPU_MODE_SECRET:
      SET_REGION( 6, SECRET_START,             SECRET_MAXSIZE,     FLASH_DATA,  YES,    NO );
      break;
    case MPU_MODE_STORAGE:
      SET_REGION( 6, STORAGE_1_START,          STORAGE_SIZE,       FLASH_DATA,  YES,    NO );
      break;
    case MPU_MODE_ASSETS:
      SET_REGION( 6, ASSETS_START,             ASSETS_MAXSIZE,     FLASH_DATA,  YES,    NO );
      break;
    case MPU_MODE_APP_SAES:
    case MPU_MODE_APP:
      SET_REGION( 6, ASSETS_START,             ASSETS_MAXSIZE,     FLASH_DATA,   NO,   YES );
      break;
    case MPU_MODE_BOOTARGS:
      SET_REGION( 6, BOOTARGS_START,           BOOTARGS_SIZE,      SRAM,        YES,    NO );
      break;
    default:
      // By default, the kernel needs to have the same access to assets as the app
      SET_REGION( 6, ASSETS_START,             ASSETS_MAXSIZE,     FLASH_DATA,   NO,    NO );
      break;
  }
  // clang-format on

  // Region #7 is banked

  // clang-format off
  switch (mode) {
      //      REGION   ADDRESS                 SIZE                TYPE       WRITE   UNPRIV
#ifdef KERNEL
    case MPU_MODE_APP_SAES:
      SET_REGION( 7, PERIPH_BASE,              PERIPH_SIZE,        PERIPHERAL,  YES,    YES ); // Peripherals - SAES, TAMP
      break;
#endif
    case MPU_MODE_OTP:
      // Write to OTP requires access to non-secure FLASH controller
      // (so we extended the peripheral region to cover it)
      SET_REGION( 7, PERIPH_BASE_NS,           PERIPH_SIZE_EXT,    PERIPHERAL,  YES,    NO );
      break;
    default:
      // All peripherals (Privileged, Read-Write, Non-Executable)
      SET_REGION( 7, PERIPH_BASE,              PERIPH_SIZE,        PERIPHERAL,  YES,    NO );
      break;
  }
  // clang-format on

  if (mode != MPU_MODE_DISABLED) {
    mpu_enable();
  }

  mpu_mode_t prev_mode = drv->mode;
  drv->mode = mode;

  irq_unlock(irq_key);

  return prev_mode;
}

void mpu_restore(mpu_mode_t mode) { mpu_reconfig(mode); }

#endif  // KERNEL_MODE
