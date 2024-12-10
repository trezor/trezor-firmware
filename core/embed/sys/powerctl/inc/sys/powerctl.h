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

#ifndef TREZORHAL_POWERCTL_H
#define TREZORHAL_POWERCTL_H

// Initializes power control module.
//
// Returns true if the initialization was successful.
bool powerctl_init(void);

// Deinitializes power control module.
void powerctl_deinit(void);

typedef enum {
  POWER_SOURCE_BATT,
  POWER_SOURCE_USB,
  POWER_SOURCE_WIRELESS,
} power_source_t;

typedef struct {
  // Current power source
  power_source_t power_source;
  // Set if charging is active
  bool charging;
  // Battery charge level in percents
  // (or -1 if the battery level is unknown)
  int charge_level;
  // Set if the temperature is too low
  bool low_temperature;
  // Set if the temperature is too high
  bool high_temperature;
} powerctl_status_t;

// Gets the current power status.
void powerctl_get_status(powerctl_status_t* status);

// Enters low-power mode
//
void powerctl_suspend(void);

#endif  // TREZORHAL_POWERCTL_H
