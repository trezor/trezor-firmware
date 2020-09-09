/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "trezor.h"
#include <libopencm3/stm32/desig.h>
#include <libopencm3/stm32/flash.h>
#include <vendor/libopencm3/include/libopencmsis/core_cm3.h>
#include "bitmaps.h"
#include "bl_check.h"
#include "layout.h"
#include "memory.h"
#include "memzero.h"
#include "oled.h"
#include "rng.h"
#include "setup.h"
#include "timer.h"
#include "util.h"

/** Sector erase operation extracted from libopencm3 - flash_erase_sector
 * so it can run from RAM
 */
static void __attribute__((noinline, section(".data")))
erase_sector(uint8_t sector, uint32_t psize) {
  // Wait for flash controller to be ready
  while ((FLASH_SR & FLASH_SR_BSY) == FLASH_SR_BSY)
    ;
  // Set program word width
  FLASH_CR &= ~(FLASH_CR_PROGRAM_MASK << FLASH_CR_PROGRAM_SHIFT);
  FLASH_CR |= psize << FLASH_CR_PROGRAM_SHIFT;

  /* Sector numbering is not contiguous internally! */
  if (sector >= 12) {
    sector += 4;
  }

  FLASH_CR &= ~(FLASH_CR_SNB_MASK << FLASH_CR_SNB_SHIFT);
  FLASH_CR |= (sector & FLASH_CR_SNB_MASK) << FLASH_CR_SNB_SHIFT;
  FLASH_CR |= FLASH_CR_SER;
  FLASH_CR |= FLASH_CR_STRT;

  // Wait for flash controller to be ready
  while ((FLASH_SR & FLASH_SR_BSY) == FLASH_SR_BSY)
    ;
  FLASH_CR &= ~FLASH_CR_SER;
  FLASH_CR &= ~(FLASH_CR_SNB_MASK << FLASH_CR_SNB_SHIFT);
}

static void __attribute__((noinline, section(".data")))
erase_firmware_and_storage(void) {
  // Flash unlock
  FLASH_KEYR = FLASH_KEYR_KEY1;
  FLASH_KEYR = FLASH_KEYR_KEY2;

  // Erase storage sectors to prevent firmware downgrade to vulnerable version
  for (int i = FLASH_STORAGE_SECTOR_FIRST; i <= FLASH_STORAGE_SECTOR_LAST;
       i++) {
    erase_sector(i, FLASH_CR_PROGRAM_X32);
  }

  // Erase firmware sectors
  for (int i = FLASH_CODE_SECTOR_FIRST; i <= FLASH_CODE_SECTOR_LAST; i++) {
    erase_sector(i, FLASH_CR_PROGRAM_X32);
  }

  // Flash lock
  FLASH_CR |= FLASH_CR_LOCK;
}

void __attribute__((noinline, noreturn, section(".data"))) reboot_device(void) {
  __disable_irq();
  SCB_AIRCR = SCB_AIRCR_VECTKEY | SCB_AIRCR_SYSRESETREQ;
  while (1)
    ;
}

/** Entry point of RAM shim that deletes old FW, storage and reboot */
void __attribute__((noinline, noreturn, section(".data")))
erase_fw_and_reboot(void) {
  erase_firmware_and_storage();
  reboot_device();

  for (;;)
    ;  // never reached, but compiler would generate error
}

int main(void) {
  setupApp();
  __stack_chk_guard = random32();  // this supports compiler provided
                                   // unpredictable stack protection checks
  oledInit();
  if (is_mode_unprivileged()) {
    layoutDialog(&bmp_icon_warning, NULL, NULL, NULL, "Cannot update", NULL,
                 NULL, "Unprivileged mode", "Unsigned firmware", NULL);
    shutdown();
  }

  mpu_config_off();  // needed for flash writable, RAM RWX
  timer_init();
  check_bootloader(false);

  layoutDialog(&bmp_icon_warning, NULL, NULL, NULL, "Erasing old data", NULL,
               NULL, "DO NOT UNPLUG", "YOUR TREZOR!", NULL);
  oledRefresh();

  // from this point the execution is from RAM instead of flash
  erase_fw_and_reboot();

  return 0;
}
