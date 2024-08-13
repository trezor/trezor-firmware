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

#ifndef TREZORHAL_MONOCTR
#define TREZORHAL_MONOCTR

#ifdef KERNEL_MODE

// Monoctr module provides monotonic counter functionality

#define MONOCTR_MAX_VALUE 63

#include <stdint.h>
#include "secbool.h"

typedef enum {
  MONOCTR_BOOTLOADER_VERSION = 0,
  MONOCTR_FIRMWARE_VERSION = 1,
} monoctr_type_t;

// Write a new value to the monotonic counter
// Returns sectrue on success, when value is lower than the current value
// the write fails and returns secfalse
secbool monoctr_write(monoctr_type_t type, uint8_t value);

// Read the current value of the monotonic counter
secbool monoctr_read(monoctr_type_t type, uint8_t* value);

#endif  // KERNEL_MODE

#endif
