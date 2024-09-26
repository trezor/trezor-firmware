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

#ifndef TREZORHAL_PLATFORM_H
#define TREZORHAL_PLATFORM_H

#include <stdint.h>

#include STM32_HAL_H
#include "error_handling.h"

#define FLASH_QUADWORD_WORDS (4)
#define FLASH_QUADWORD_SIZE (FLASH_QUADWORD_WORDS * sizeof(uint32_t))

#define FLASH_BURST_WORDS (8 * FLASH_QUADWORD_WORDS)
#define FLASH_BURST_SIZE (FLASH_BURST_WORDS * sizeof(uint32_t))

typedef enum {
  CLOCK_160_MHZ = 0,
} clock_settings_t;

void set_core_clock(clock_settings_t settings);

// the following functions are defined in util.s
void memset_reg(volatile void *start, volatile void *stop, uint32_t val);
void jump_to(uint32_t address);
void jump_to_with_flag(uint32_t address, uint32_t register_flag);

extern uint32_t __stack_chk_guard;

void check_oem_keys(void);

// HAL status code helpers
static inline ts_t hal_status_to_ts(HAL_StatusTypeDef hal_status) {
  switch (hal_status) {
    case HAL_OK:
      return TS_OK;
    case HAL_BUSY:
      return TS_ERROR_BUSY;
    case HAL_TIMEOUT:
      return TS_ERROR_TIMEOUT;
    default:
      return TS_ERROR;
  }
}

#define TS_CHECK_HAL_OK(status) TS_CHECK_OK(hal_status_to_ts(status))

#endif  // TREZORHAL_PLATFORM_H
