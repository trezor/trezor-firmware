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

#ifdef SECURE_MODE

#include <trezor_types.h>

// Monoctr module provides monotonic counter functionality

#define MONOCTR_MAX_VALUE 63

/**
 * @brief Enum representing the types of available monotonic counters.
 */
typedef enum {
  MONOCTR_BOOTLOADER_VERSION = 0,
  MONOCTR_FIRMWARE_VERSION = 1,
  MONOCTR_SECMON_VERSION = 2,
} monoctr_type_t;

/**
 * @brief Initializes the monotonic counter module.
 *
 * This function should be called before any other operations on the monotonic
 * counter.
 */
void monoctr_init(void);

/**
 * @brief Write a new value to the monotonic counter
 *
 * @param type The type of the monotonic counter to write to.
 * @param value The new value to write to the monotonic counter.
 *              Maximum value is defined by MONOCTR_MAX_VALUE.
 *
 * @return Returns sectrue on success when value is not lower than the current
 *         value. If the write fails, returns secfalse.
 * */
secbool monoctr_write(monoctr_type_t type, uint8_t value);

/**
 * @brief Read the current value of the monotonic counter
 *
 * @param type The type of the monotonic counter to read from.
 * @param value Pointer to store the current value of the monotonic counter.
 *
 * @return Returns sectrue on success, or secfalse if the read fails.
 */
secbool monoctr_read(monoctr_type_t type, uint8_t* value);

#endif  // SECURE_MODE
