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
#include <string.h>
#include <vendor/libopencm3/include/libopencmsis/core_cm3.h>
#include "bitmaps.h"
#include "bl_check.h"
#include "layout.h"
#include "memory.h"
#include "memzero.h"
#include "norcow_config.h"
#include "oled.h"
#include "rng.h"
#include "setup.h"
#include "supervise.h"
#include "timer.h"
#include "util.h"

// legacy storage magic
#define LEGACY_STORAGE_SECTOR 2
static const uint32_t META_MAGIC_V10 = 0x525a5254;  // 'TRZR'

// norcow storage magic
static const uint32_t NORCOW_MAGIC = 0x3243524e;  // 'NRC2'
static const uint8_t norcow_sectors[NORCOW_SECTOR_COUNT] = NORCOW_SECTORS;

/** Flash program word operation extracted from libopencm3,
 * so it can run from RAM
 */
static void __attribute__((noinline, section(".data")))
_flash_program_word(uint32_t address, uint32_t data) {
  // Wait for flash controller to be ready
  while ((FLASH_SR & FLASH_SR_BSY) == FLASH_SR_BSY)
    ;

  // Set program word width
  FLASH_CR &= ~(FLASH_CR_PROGRAM_MASK << FLASH_CR_PROGRAM_SHIFT);
  FLASH_CR |= FLASH_CR_PROGRAM_X32 << FLASH_CR_PROGRAM_SHIFT;

  // Enable writes to flash
  FLASH_CR |= FLASH_CR_PG;

  // Program the word
  MMIO32(address) = data;

  // Wait for flash controller to be ready
  while ((FLASH_SR & FLASH_SR_BSY) == FLASH_SR_BSY)
    ;

  // Disable writes to flash
  FLASH_CR &= ~FLASH_CR_PG;
}

static void __attribute__((noinline, section(".data")))
invalidate_firmware(void) {
  // Flash unlock
  FLASH_KEYR = FLASH_KEYR_KEY1;
  FLASH_KEYR = FLASH_KEYR_KEY2;

  // Erase the first firmware word
  // (we don't need full erasure, this speeds up the whole process)
  _flash_program_word(FLASH_FWHEADER_START, 0);

  // Flash lock
  FLASH_CR |= FLASH_CR_LOCK;
}

void __attribute__((noinline, noreturn, section(".data"))) reboot_device(void) {
  __disable_irq();
  *STAY_IN_BOOTLOADER_FLAG_ADDR = STAY_IN_BOOTLOADER_FLAG;
  SCB_AIRCR = SCB_AIRCR_VECTKEY | SCB_AIRCR_SYSRESETREQ;
  while (1)
    ;
}

/** Entry point of RAM shim that deletes old FW, storage and reboot */
void __attribute__((noinline, noreturn, section(".data")))
invalidate_firmware_and_reboot(void) {
  invalidate_firmware();
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
  check_and_replace_bootloader(false);

  secbool storage_initialized = secfalse;

  // check legacy storage
  uint32_t *magic = (uint32_t *)flash_get_address(LEGACY_STORAGE_SECTOR, 0,
                                                  sizeof(META_MAGIC_V10));
  if (*magic == META_MAGIC_V10) {
    storage_initialized = sectrue;
  }

  if (storage_initialized == secfalse) {
    // check norcow storage
    for (uint8_t i = 0; i < NORCOW_SECTOR_COUNT; i++) {
      magic = (uint32_t *)flash_get_address(norcow_sectors[i], 0,
                                            sizeof(NORCOW_MAGIC));
      if (*magic == NORCOW_MAGIC) {
        storage_initialized = sectrue;
        break;
      }
    }
  }

  if (sectrue == storage_initialized) {
    // Storage probably contains a seed so leave the firmware intact.
    // Invalidating it would cause the bootloader to wipe the storage before
    // installing the target firmware. User will need to confirm installation.
    reboot_device();
  } else {
    // New device. Invalidate the intermediate firmware so that after reboot
    // the bootloader will install the target firmware without asking for user
    // confirmation.
    invalidate_firmware_and_reboot();
  }

  return 0;
}
