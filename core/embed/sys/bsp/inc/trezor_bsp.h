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

#ifndef TREZOR_BSP_H
#define TREZOR_BSP_H

// Trezor 'board support package' (BSP) header file that includes
// all necessary headers for the specific board including STM32 HAL and
// pin definitions.
//
// This file should be only included by driver implementations and
// should not be included by application code.

#include TREZOR_BOARD

#ifndef TREZOR_EMULATOR
#include STM32_HAL_H
#endif

#endif  // TREZOR_BOARD_H
