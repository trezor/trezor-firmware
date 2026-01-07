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

typedef enum {
  // Effect at the start of a button press
  HAPTIC_BUTTON_PRESS = 0,
  // Effect at the end of hold-to-confirm action
  HAPTIC_HOLD_TO_CONFIRM = 1,
  // Bootloader entry
  HAPTIC_BOOTLOADER_ENTRY = 2,
  // Power on
  HAPTIC_POWER_ON = 3,
} haptic_effect_t;

#ifdef KERNEL_MODE

/**
 * @brief Initializes the haptic driver
 *
 * The function initializes the GPIO pins and the hardware
 * peripherals used by the haptic driver.
 *
 * @return TS_OK if the initialization was successful
 */
ts_t __wur haptic_init(void);

/**
 * @brief Deinitializes the haptic driver
 *
 * The function deinitializes the hardware peripherals used by the
 * haptic driver.
 */
void haptic_deinit(void);

#endif  // KERNEL_MODE

/**
 * @brief Enables/disables the haptic driver
 *
 * @param enabled If `true`, enables the haptic driver; if `false`, disables it
 * @return TS_OK if the operation was successful
 */
ts_t haptic_set_enabled(bool enabled);

/**
 * @brief Gets tha haptic driver enable state
 *
 * @return true if the haptic driver is enabled
 */
bool haptic_get_enabled(void);

/**
 * @brief Plays selected haptic effect
 *
 * The function stops playing any currently running effect and
 * starts playing the specified effect.
 *
 * @return TS_OK if the effect was successfully started
 */
ts_t haptic_play(haptic_effect_t effect);

/**
 * @brief Resonates the haptic motor with specified amplitude (in percent) and
 * duration (in milliseconds)
 *
 * The function can be invoked repeatedly during the specified duration
 * (`duration_ms`) to modify the amplitude dynamically, allowing
 * the creation of customized haptic effects.
 *
 * @return TS_OK if the effect was successfully started
 */
ts_t haptic_play_custom(int8_t amplitude_pct, uint16_t duration_ms);
