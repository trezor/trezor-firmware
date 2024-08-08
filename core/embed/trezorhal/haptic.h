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

#ifndef TREZORHAL_HAPTIC_H
#define TREZORHAL_HAPTIC_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
  // Effect at the start of a button press
  HAPTIC_BUTTON_PRESS = 0,
  // Effect at the and of hold-to-confirm action
  HAPTIC_HOLD_TO_CONFIRM = 1,
} haptic_effect_t;

#ifdef KERNEL_MODE

// Initializes the haptic driver
//
// The function initializes the GPIO pins and the hardware
// peripherals used by the haptic driver.
//
// Returns `true` if the initialization was successful.
bool haptic_init(void);

// Deinitializes the haptic driver
//
// The function deinitializes the hardware peripherals used by the
// haptic driver so the device can be eventually put into a low-power mode.
void haptic_deinit(void);

#endif  // KERNEL_MODE

// Enables or disables the haptic driver
//
// When the driver is disabled, it does not play any haptic effects
// and potentially can put the controller into a low-power mode.
//
// The driver is enabled by default (after initialization).
void haptic_set_enabled(bool enabled);

// Returns `true` if haptic driver is enabled
bool haptic_get_enabled(void);

// Tests the haptic driver, playing at maximum amplitude for the given duration
//
// This function is used during production testing to verify that the haptic
// motor is working correctly.
//
// Returns `true` if the test effect was successfully started.
bool haptic_test(uint16_t duration_ms);

// Plays one of haptic effects
//
// The function stops playing any currently running effect and
// starts playing the specified effect.
//
// Returns `true` if the effect was successfully started.
bool haptic_play(haptic_effect_t effect);

// Starts the haptic motor with a specified amplitude (in percent) for a
// specified duration (in milliseconds).
//
// The function stops playing any currently running effect and
// starts playing the specified effect.
//
// The function can be invoked repeatedly during the specified duration
// (`duration_ms`) to modify the amplitude dynamically, allowing
// the creation of customized haptic effects.
//
// Returns `true` if the effect was successfully started.
bool haptic_play_custom(int8_t amplitude_pct, uint16_t duration_ms);

#endif  // TREZORHAL_HAPTIC_H
