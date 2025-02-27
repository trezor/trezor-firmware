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

#pragma once

#include <trezor_types.h>

#ifdef KERNEL_MODE

// Tamper module enables the internal tamper detection on STM32 microcontroller
// as well as external tamper input if it's available on the device

// Initializes the tamper detection
bool tamper_init(void);

// Get status of external tamper inputs
uint8_t tamper_external_read(void);

// Enable external tamper inputs
void tamper_external_enable(void);

#endif  // KERNEL_MODE
