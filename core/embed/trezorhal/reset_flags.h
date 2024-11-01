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

#ifndef TREZORHAL_RESET_FLAGS_H
#define TREZORHAL_RESET_FLAGS_H

#include <trezor_types.h>

#ifdef KERNEL_MODE

// Checks if the CPU reset flags indicate an expected type of reset.
secbool reset_flags_check(void);

// Clear the CPU register that holds the reset flags.
void reset_flags_reset(void);

#endif  // KERNEL_MODE

#endif  // TREZORHAL_RESET_FLAGS_H
