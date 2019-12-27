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

#ifndef __SUPERVISE_H__
#define __SUPERVISE_H__

#include <stdint.h>

#if !EMULATOR

#define SVC_FLASH_UNLOCK 0
#define SVC_FLASH_ERASE 1
#define SVC_FLASH_PROGRAM 2
#define SVC_FLASH_LOCK 3
#define SVC_TIMER_MS 4

/* Unlocks flash.  This function needs to be called before programming
 * or erasing. Multiple calls of flash_program and flash_erase can
 * follow and should be completed with flash_lock().
 */
inline void svc_flash_unlock(void) {
  __asm__ __volatile__("svc %0" ::"i"(SVC_FLASH_UNLOCK) : "memory");
}

/* Enable flash write operations.
 * @param program_size (8-bit, 16-bit, 32-bit or 64-bit)
 *       should be one of the FLASH_CR_PROGRAM_X.. constants
 */
inline void svc_flash_program(uint32_t program_size) {
  register uint32_t r0 __asm__("r0") = program_size;
  __asm__ __volatile__("svc %0" ::"i"(SVC_FLASH_PROGRAM), "r"(r0) : "memory");
}

/* Erase a flash sector.
 * @param sector sector number 0..11
 *    (this only allows erasing meta sectors 2 and 3 though).
 */
inline void svc_flash_erase_sector(uint8_t sector) {
  register uint32_t r0 __asm__("r0") = sector;
  __asm__ __volatile__("svc %0" ::"i"(SVC_FLASH_ERASE), "r"(r0) : "memory");
}

/* Lock flash after programming or erasing.
 * @return flash status register (FLASH_SR)
 */
inline uint32_t svc_flash_lock(void) {
  register uint32_t r0 __asm__("r0");
  __asm__ __volatile__("svc %1" : "=r"(r0) : "i"(SVC_FLASH_LOCK) : "memory");
  return r0;
}

inline uint32_t svc_timer_ms(void) {
  register uint32_t r0 __asm__("r0");
  __asm__ __volatile__("svc %1" : "=r"(r0) : "i"(SVC_TIMER_MS) : "memory");
  return r0;
}

#else

extern void svc_flash_unlock(void);
extern void svc_flash_program(uint32_t program_size);
extern void svc_flash_erase_sector(uint16_t sector);
extern uint32_t svc_flash_lock(void);
extern uint32_t svc_timer_ms(void);

#endif

#endif
