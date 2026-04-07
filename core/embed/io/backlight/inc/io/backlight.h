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

#define BACKLIGHT_MAX_LEVEL 255
#define BACKLIGHT_MIN_LEVEL 0

// Action to be taken when initializing or
// deinitializing the backlight driver
typedef enum {
  BACKLIGHT_RESET,
  BACKLIGHT_RETAIN,
} backlight_action_t;

// Initialize the backlight driver
//
// If the action is set to `BACKLIGHT_RESET`, the backlight level
// is set to zero level. If the action is set to `BACKLIGHT_RETAIN`,
// the backlight level is not changed (if possible).
//
// The `gamma_exp` parameter specifies the gamma_exp correction factor.
//
// Returns `true` if the initialization was successful.
bool backlight_init(backlight_action_t action, float gamma_exp);

// Deinitialize the backlight driver
//
// If the action is set to `BACKLIGHT_RESET`, the backlight driver
// is completely deinitialized. If the action is set to `BACKLIGHT_RETAIN`,
// the driver is deinitialized as much as possible but the backlight
// is kept on.
void backlight_deinit(backlight_action_t action);

// Requests the backlight level in range 0-255 and returns whether
// the function executed successfully or not. The requested level
// may be limited if it's above the max_level limit.
//
// If the backlight driver is not initialized, the function
// returns "False".
bool backlight_set(uint8_t val);

// Gets the backlight level in range 0-255
//
// Returns 0 if the backlight driver is not initialized.
uint8_t backlight_get(void);

// Set maximal backlight limit, limits the requested level to max_level value.
//
// Returns "False" if the backlight driver is not initialized.
bool backlight_set_max_level(uint8_t max_level);
