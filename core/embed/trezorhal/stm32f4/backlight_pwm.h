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

#ifndef TREZORHAL_BACKLIGHT_H
#define TREZORHAL_BACKLIGHT_H

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
void backlight_pwm_init(backlight_action_t action);

// Deinitialize the backlight driver
//
// If the action is set to `BACKLIGHT_RESET`, the backlight driver
// is completely deinitialized. If the action is set to `BACKLIGHT_RETAIN`,
// the driver is deinitialized as much as possible but the backlight
// is kept on.
void backlight_pwm_deinit(backlight_action_t action);

// Sets the backlight level in range 0-255 and returns the actual level set.
//
// If the level is outside the range, the function has no effect
// and just returns the actual level set. If the backlight driver
// is not initialized, the function returns 0.
int backlight_pwm_set(int val);

// Gets the backlight level in range 0-255
//
// Returns 0 if the backlight driver is not initialized.
int backlight_pwm_get(void);

#endif  // TREZORHAL_BACKLIGHT_H
