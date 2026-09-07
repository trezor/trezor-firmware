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

#ifndef MI0240AGT5CP1F_H_
#define MI0240AGT5CP1F_H_

#include "../display_driver.h"

// GPIO setup for the IM[2:0] mode-select pins. Latched at reset, so must run
// before the reset pulse - called from display_init() in display_driver.c.
void mi0240agt5cp1f_select_interface_mode(void);

// ST7789V2 register init sequence for this panel. Called (over SPI, after
// reset) from display_init() in display_driver.c.
void mi0240agt5cp1f_init_seq(display_driver_t *drv);

// Sets MADCTL for the given orientation (0/90/180/270). Called from
// display_set_orientation() in display_driver.c.
void mi0240agt5cp1f_rotate(display_driver_t *drv, int angle);

#endif  // MI0240AGT5CP1F_H_
