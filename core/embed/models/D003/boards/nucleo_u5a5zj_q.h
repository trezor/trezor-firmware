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

// Board definition for the NUCLEO-U5A5ZJ-Q development board (STM32U5A5ZJ).
//
// This is a headless development target: the board has no display, touch
// panel or SD-card hardware. Only the bare essentials needed to bring up the
// boot chain (boardloader -> bootloader) and communicate over USB are defined
// here. Peripheral pin mappings (LEDs, button, UART) can be added as the
// bring-up progresses.

#ifndef NUCLEO_U5A5ZJ_Q_H_
#define NUCLEO_U5A5ZJ_Q_H_

// The Nucleo board is powered from the ST-LINK USB at 3.3 V.
#define VDD_3V3 1

#endif  // NUCLEO_U5A5ZJ_Q_H_
