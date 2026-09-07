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

#ifndef MI0200AET1_H_
#define MI0200AET1_H_

#include "../display_driver.h"

// Unlike the mi0240agt5cp1f sibling panel, this module's IM[2:0] mode-select
// pins are not wired to the MCU at all ("no IM pins used"), so there is no
// mi0200aet1_select_interface_mode() - the interface mode is presumably
// fixed by strapping on the MI0240EGP-C1_OB adapter board itself.

// ST7789V2 register init sequence for this panel. Called (over SPI, after
// reset) from display_init() in display_driver.c.
void mi0200aet1_init_seq(display_driver_t *drv);

// Sets MADCTL for the given orientation (0/90/180/270). Called from
// display_set_orientation() in display_driver.c.
void mi0200aet1_rotate(display_driver_t *drv, int angle);

#endif  // MI0200AET1_H_
