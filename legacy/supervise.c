/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2018 Jochen Hoenicke <hoenicke@gmail.com>
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

#include "supervise.h"
#include <libopencm3/stm32/flash.h>
#include <stdint.h>
#if !EMULATOR
#include <vendor/libopencm3/include/libopencmsis/core_cm3.h>
#endif
#include "memory.h"

#if !EMULATOR

static void svhandler_flash_unlock(void) {
  flash_wait_for_last_operation();
  flash_clear_status_flags();
  flash_unlock();
}

static void svhandler_flash_program(uint32_t psize) {
  /* Wait for any write operation to complete. */
  flash_wait_for_last_operation();
  /* check program size argument */
  if (psize != FLASH_CR_PROGRAM_X8 && psize != FLASH_CR_PROGRAM_X16 &&
      psize != FLASH_CR_PROGRAM_X32 && psize != FLASH_CR_PROGRAM_X64)
    return;
  FLASH_CR = (FLASH_CR & ~(FLASH_CR_PROGRAM_MASK << FLASH_CR_PROGRAM_SHIFT)) |
             (psize << FLASH_CR_PROGRAM_SHIFT);
  FLASH_CR |= FLASH_CR_PG;
}

static void svhandler_flash_erase_sector(uint16_t sector) {
  /* we only allow erasing storage sectors 2 and 3. */
  if (sector < FLASH_STORAGE_SECTOR_FIRST ||
      sector > FLASH_STORAGE_SECTOR_LAST) {
    return;
  }
  flash_erase_sector(sector, FLASH_CR_PROGRAM_X32);
}

static uint32_t svhandler_flash_lock(void) {
  /* Wait for any write operation to complete. */
  flash_wait_for_last_operation();
  /* Disable writes to flash. */
  FLASH_CR &= ~FLASH_CR_PG;
  /* lock flash register */
  FLASH_CR |= FLASH_CR_LOCK;
  /* return flash status register */
  return FLASH_SR;
}

static void __attribute__((noreturn)) svhandler_reboot_to_bootloader(void) {
  *STAY_IN_BOOTLOADER_FLAG_ADDR = STAY_IN_BOOTLOADER_FLAG;
  scb_reset_system();
}

extern volatile uint32_t system_millis;

void svc_handler_main(uint32_t *stack) {
  uint8_t svc_number = ((uint8_t *)stack[6])[-2];
  switch (svc_number) {
    case SVC_FLASH_UNLOCK:
      svhandler_flash_unlock();
      break;
    case SVC_FLASH_PROGRAM:
      svhandler_flash_program(stack[0]);
      break;
    case SVC_FLASH_ERASE:
      svhandler_flash_erase_sector(stack[0]);
      break;
    case SVC_FLASH_LOCK:
      stack[0] = svhandler_flash_lock();
      break;
    case SVC_TIMER_MS:
      stack[0] = system_millis;
      break;
    case SVC_REBOOT_TO_BOOTLOADER:
      svhandler_reboot_to_bootloader();
      break;
    default:
      stack[0] = 0xffffffff;
      break;
  }
}

#endif
