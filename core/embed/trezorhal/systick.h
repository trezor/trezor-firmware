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

#ifndef TREZORHAL_SYSTICK_H
#define TREZORHAL_SYSTICK_H

#include <stdbool.h>
#include <stdint.h>

// Initializes systick subsystem
//
// Before calling this function, none of the other functions
// from this module should be called.
void systick_init(void);

// Deinitialize systick subsystem
//
// The function should be called before jumping to the
// next bootloader stage or firmware.
void systick_deinit(void);

// Updates systick subsystem with new system clock frequency
//
// The function should be called after the system clock frequency
// has been changed.
void systick_update_freq(void);

// ----------------------------------------------------------------------------
// Tick functions

// Number of ticks (milliseconds)
typedef uint32_t ticks_t;

// Returns number of ticks (milliseconds) since the system start.
//
// The returned value is a 32-bit unsigned integer that wraps
// around every 49.7 days.
ticks_t hal_ticks_ms(void);

// Helper function for building expiration time
#define ticks_timeout(timeout) (hal_ticks() + (timeout))

// Helper function for checking ticks expiration
//
// It copes with the wrap-around of the `ticks_t` type but
// still assumes that the difference between the two ticks
// is less than half of the `ticks_t` range.
#define ticks_expired(ticks) ((int32_t)(hal_ticks() - (ticks)) >= 0)

// ----------------------------------------------------------------------------
// Delay functions

// Waits for at least `ms` milliseconds
void hal_delay(uint32_t ms);

// Waits for at least `us` microseconds
void hal_delay_us(uint64_t us);

#endif  // TREZORHAL_SYSTICK_H
