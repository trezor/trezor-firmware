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

#ifndef TREZORHAL_STM32F4_STARTUP_INIT_H
#define TREZORHAL_STM32F4_STARTUP_INIT_H

#ifdef TREZOR_MODEL_T

typedef enum {
  CLOCK_180_MHZ = 0,
  CLOCK_168_MHZ = 1,
  CLOCK_120_MHZ = 2,
} clock_settings_t;

// Alters core clock frequency
void set_core_clock(clock_settings_t settings);

#endif

#endif  // TREZORHAL_STM32F4_STARTUP_INIT_H
