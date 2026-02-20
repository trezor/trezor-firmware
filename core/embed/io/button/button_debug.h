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

#include <io/button.h>

/**
 * @brief Initialize the button debug module.
 */
void button_debug_init(void);

/**
 * @brief Deinitialize the button debug module.
 */
void button_debug_deinit(void);

/**
 * @brief Signal a click event for the given button.
 *
 * @param button The button that was clicked.
 */
void button_debug_click(button_t button);

/**
 * @brief Signal a press event for the given button.
 *
 * @param button The button that was pressed.
 */
void button_debug_press(button_t button);

/**
 * @brief Signal a release event for the given button.
 *
 * @param button The button that was released.
 */
void button_debug_release(button_t button);

/**
 * @brief Advance to the next button debug state.
 */
void button_debug_next(void);

/**
 * @brief Get the current button debug state.
 *
 * @return The current state as a 32-bit unsigned integer.
 */
uint32_t button_debug_get_state(void);
