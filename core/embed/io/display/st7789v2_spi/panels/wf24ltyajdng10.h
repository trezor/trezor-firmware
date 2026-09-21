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

#ifndef WF24LTYAJDNG10_H_
#define WF24LTYAJDNG10_H_

#include "../display_driver.h"

// GPIO setup for the IM[2:0] mode-select pins. Latched at reset, so must run
// before the reset pulse - called from display_init() in display_driver.c.
void wf24ltyajdng10_select_interface_mode(void);

// ILI9341V register init sequence for this panel. Called (over SPI, after
// reset) from display_init() in display_driver.c.
void wf24ltyajdng10_init_seq(display_driver_t *drv);

// Sets MADCTL for the given orientation (0/90/180/270). Called from
// display_set_orientation() in display_driver.c.
void wf24ltyajdng10_rotate(display_driver_t *drv, int angle);

#endif  // WF24LTYAJDNG10_H_
