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

#ifndef TREZORHAL_FLASH_H
#define TREZORHAL_FLASH_H

#include <stdint.h>
#include <stdlib.h>

#include "flash_ll.h"
#include "secbool.h"

#ifndef TREZOR_EMULATOR
#include STM32_HAL_H
#endif

#ifdef STM32U5

#define FLASH_QUADWORD_WORDS (4)
#define FLASH_QUADWORD_SIZE (FLASH_QUADWORD_WORDS * sizeof(uint32_t))

#define FLASH_BURST_WORDS (8 * FLASH_QUADWORD_WORDS)
#define FLASH_BURST_SIZE (FLASH_BURST_WORDS * sizeof(uint32_t))

#endif

void flash_init(void);

#endif  // TREZORHAL_FLASH_H
