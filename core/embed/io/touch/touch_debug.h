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

/**
 * @brief Initialize the touch debug module.
 */
void touch_debug_init(void);

/**
 * @brief Deinitialize the touch debug module.
 */
void touch_debug_deinit(void);

/**
 * @brief Signal the start of a touch event at the given coordinates.
 *
 * @param x The x-coordinate of the touch event.
 * @param y The y-coordinate of the touch event.
 */
void touch_debug_start(uint32_t x, uint32_t y);

/**
 * @brief Signal the end of a touch event at the given coordinates.
 *
 * @param x The x-coordinate of the touch event.
 * @param y The y-coordinate of the touch event.
 */
void touch_debug_end(uint32_t x, uint32_t y);

/**
 * @brief Signal a click event at the given coordinates.
 *
 * @param x The x-coordinate of the click event.
 * @param y The y-coordinate of the click event.
 */
void touch_debug_click(uint32_t x, uint32_t y);

/**
 * @brief Advance to the next touch debug state.
 */
void touch_debug_next(void);

/**
 * @brief Check if touch debug is currently active.
 *
 * @return True if active, false otherwise.
 */
bool touch_debug_active(void);

/**
 * @brief Get the current touch debug state.
 *
 * @return The current state as a 32-bit unsigned integer.
 */
uint32_t touch_debug_get_state(void);
