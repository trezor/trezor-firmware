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

#ifdef SECURE_MODE

#include <sec/tamper.h>

// STM32H5 tamper: BRING-UP MOCK.
//
// TODO(H5): implement the real tamper driver. The STM32H5 TAMP peripheral and
// the internal-tamper source map (ITAMP1..13: voltage/temperature/LSE/RTC
// overflow/SWD access/ADC watchdog/monotonic counter/crypto fault/IWDG) differ
// from the STM32U5, and the surrounding PWR/RCC registers (backup domain,
// PWR->BDCR1 MONEN, RCC PWR clock enable, RTC clock selection) are H5-specific.
// This mock leaves tamper detection DISABLED so bring-up cannot spuriously trip
// a tamper reset; it must be replaced with a proper RM0517-based configuration
// before this model provides any physical-attack protection.

bool tamper_init(void) { return true; }

uint8_t tamper_external_read(void) { return 0; }

void tamper_external_enable(void) {}

void tamper_external_disable(void) {}

#endif  // SECURE_MODE
