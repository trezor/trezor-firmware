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

#ifndef TREZOR_HAL_TAMPER_H
#define TREZOR_HAL_TAMPER_H

#include <stdint.h>

#ifdef KERNEL_MODE

// Tamper module enables the internal tamper detection on STM32 microcontroller
// as well as external tamper input if it's available on the device

// Initializes the tamper detection
void tamper_init(void);

// Triggers one of internal tampers.
// The function is intended for experimentation with internal tamper mechanism
// Use TAMP_CR1_xxx constants to as a parameter
// Only TAMP_CR1_ITAMP5E (RTC) and TAMP_CR1_ITAMP8E (monotonic counter)
// are supported
void tamper_test(uint32_t tamper_type);

#endif  // KERNEL_MODE

#endif  // TREZOR_HAL_TAMPER_H
