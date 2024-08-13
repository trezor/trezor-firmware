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

#ifdef KERNEL_MODE

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

#endif  // KERNEL_MODE

// ----------------------------------------------------------------------------
// Tick functions

// Returns number of system clock cycles since the system start.
//
// Read monotonic counter with high resolution (Cortex-M SysTick clock)
// (On 160MHz CPU, 1 cycles is 1 / 160MHz = 6.25ns)
uint64_t systick_cycles(void);

// Returns number of microseconds since the system start.
uint64_t systick_us(void);

// Returns number of ticks (milliseconds) since the system start.
//
// The returned value is a 32-bit unsigned integer that wraps
// around every 49.7 days.
uint32_t systick_ms(void);

// Converts microseconds to system clock cycles
uint64_t systick_us_to_cycles(uint64_t us);

// Number of ticks (milliseconds)
typedef uint32_t ticks_t;

//
#define ticks() systick_ms()

// Helper function for building expiration time
#define ticks_timeout(timeout) (systick_ms() + (timeout))

// Helper function for checking ticks expiration
//
// It copes with the wrap-around of the `ticks_t` type but
// still assumes that the difference between the two ticks
// is less than half of the `ticks_t` range.
#define ticks_expired(ticks) ((int32_t)(systick_ms() - (ticks)) >= 0)

// ----------------------------------------------------------------------------
// Delay functions

// Waits for at least `ms` milliseconds
void systick_delay_ms(uint32_t ms);

// Waits for at least `us` microseconds
void systick_delay_us(uint64_t us);

// legacy functions

static inline uint32_t hal_ticks_ms(void) { return systick_ms(); }
static inline void hal_delay(uint32_t ms) { systick_delay_ms(ms); }
static inline void hal_delay_us(uint64_t us) { systick_delay_us(us); }

#endif  // TREZORHAL_SYSTICK_H
