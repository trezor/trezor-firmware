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
//
// Returns `true` if the status was successfully retrieved.
bool powerctl_get_status(powerctl_status_t* status);

// Enters low-power mode
//
// In low-power mode, the CPU retains its state, including SRAM content.
// The device can be woken by pressing the power button and will continue
// operation from the point where it was suspended.
void powerctl_suspend(void);

// Enters Hibernate mode.
//
// In Hibernate mode, the CPU is powered off, and only the VBAT domain remains
// active. The device can be woken by pressing the power button, triggering
// a full boot sequence.
//
// Hibernate mode can only be entered if the device is not connected to a USB or
// wireless charger. If the device is charging, the function returns `true`,
// and the device state remains unchanged. If the function succeeds, it does
// not return.
//
// Returns `false` if the operation fails (likely due to uninitialized power
// management).
bool powerctl_hibernate(void);

#endif  // TREZORHAL_POWERCTL_H
