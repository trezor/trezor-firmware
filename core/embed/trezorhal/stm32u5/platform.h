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

#ifndef TREZORHAL_STM32_H
#define TREZORHAL_STM32_H

#include STM32_HAL_H
#include <stdint.h>

#define FLASH_QUADWORD_WORDS (4)
#define FLASH_QUADWORD_SIZE (FLASH_QUADWORD_WORDS * sizeof(uint32_t))

#define FLASH_BURST_WORDS (8 * FLASH_QUADWORD_WORDS)
#define FLASH_BURST_SIZE (FLASH_BURST_WORDS * sizeof(uint32_t))

typedef enum {
  CLOCK_160_MHZ = 0,
} clock_settings_t;

void set_core_clock(clock_settings_t settings);
void ensure_compatible_settings(void);
void drop_privileges(void);

// the following functions are defined in util.s
void memset_reg(volatile void *start, volatile void *stop, uint32_t val);
void jump_to(uint32_t address);
void jump_to_with_flag(uint32_t address, uint32_t register_flag);

extern uint32_t __stack_chk_guard;

// this deletes all secrets and SRAM2 where stack is located
// to prevent stack smashing error, do not return from function calling this
static inline void __attribute__((always_inline)) delete_secrets(void) {
  // Disable SAES peripheral clock, so that we don't get tamper events
  __HAL_RCC_SAES_CLK_DISABLE();

  // Erase all
  TAMP->CR2 |= TAMP_CR2_BKERASE;
}

void check_oem_keys(void);

#endif  // TREZORHAL_STM32_H
