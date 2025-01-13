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

#ifndef TREZORHAL_BUTTON_H
#define TREZORHAL_BUTTON_H

#include <trezor_types.h>

// Button event is packed 32-bit value
//
//  31    24 23                       0
// |--------|-------------------------|
// |  event |       button identifier |
// |--------|-------------------------|
//
//

// Button events
#define BTN_EVT_DOWN (1U << 24)
#define BTN_EVT_UP (1U << 25)

// Button identifiers
typedef enum {
  BTN_LEFT = 0,
  BTN_RIGHT = 1,
  BTN_POWER = 2,
} button_t;

#ifdef KERNEL_MODE

// Initializes button driver
//
// Returns true in case of success, false otherwise
bool button_init(void);

// Deinitializes button driver
void button_deinit(void);

#endif  // KERNEL_MODE

// Get the last button event
//
// It's expected there's just one consumer of the button events,
// e.g. the main loop
//
// Returns 0 if no event is available
uint32_t button_get_event(void);

// Checks if the specified button is currently pressed
//
// The current implementation returns the state of the button at the time
// `button_get_event()` was called. In the future, we may fix this limitation.
// For now, `button_get_event()` must be called before `button_is_down()`.
bool button_is_down(button_t button);

#endif  // TREZORHAL_BUTTON_H
