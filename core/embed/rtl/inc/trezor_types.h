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

#ifndef TREZOR_TYPES_H
#define TREZOR_TYPES_H

// `trezor_types.h` consolidates commonly needed includes for interface
// header files and provides essential types required in most files.
//
// Avoid adding additional includes here unless absolutely necessary,
// as it may pollute the global namespace across the project.

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "rtl/secbool.h"

#endif  // TREZOR_TYPES_H
