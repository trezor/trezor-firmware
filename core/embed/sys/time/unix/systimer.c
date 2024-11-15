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

#include <trezor_rtl.h>

#include <sys/systimer.h>

// systimer driver state
typedef struct {
  // Set if the driver is initialized
  bool initialized;
} systimer_driver_t;

static systimer_driver_t g_systimer_driver = {
    .initialized = false,
};

void systimer_init(void) {
  systimer_driver_t* drv = &g_systimer_driver;

  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(systimer_driver_t));
  drv->initialized = true;
}

void systimer_deinit(void) {
  systimer_driver_t* drv = &g_systimer_driver;

  drv->initialized = false;
}

// Timer driver is not fully implemented for unix platform
// since not neeeded for the emulator
