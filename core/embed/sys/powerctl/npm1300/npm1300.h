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

#ifndef TREZORHAL_NPM1300_H
#define TREZORHAL_NPM1300_H

#include <trezor_types.h>

// Charging current limits
// - range of np1300 is 32-800mA
// - used battery limit is 180mA
#define NPM1300_CHARGING_LIMIT_MIN 32       // mA
#define NPM1300_CHARGING_LIMIT_MAX 180      // mA
#define NPM1300_CHARGING_LIMIT_DEFAULT 180  // mA

typedef struct {
  // Battery voltage [V]
  float vbat;
  // System voltage [V]
  float vsys;
  // Battery current [mA]
  // - positive value means discharging
  // - negative value means charging
  float ibat;
  // NTC temperature [°C]
  float ntc_temp;
  // Die temperature [°C]
  float die_temp;
  // IBAT_MEAS_STATUS register value
  // (for debugging purposes, see the NPM1300 datasheet)
  uint8_t ibat_meas_status;
  // BUCKSTATUS register value
  // (for debugging purposes, see the NPM1300 datasheet)
  uint8_t buck_status;

} npm1300_report_t;

typedef void (*npm1300_report_callback_t)(void* context,
                                          npm1300_report_t* report);

// Initializes NPM1300 PMIC driver
bool npm1300_init(void);

// Deinitializes NPM1300 PMIC driver
void npm1300_deinit(void);

// Gets the cause of the last restart
uint8_t npm1300_restart_cause(void);

// Switches the device to ship mode.
//
// In tge ship mode, the CPU is powered off, and only the VBAT domain remains
// active. The device can be woken by pressing the power button, triggering
// a full boot sequence.
//
// Ship mode can only be entered if the device is not connected to a USB or
// wireless charger. If the device is charging, the function returns `true`,
// and the device state remains unchanged.
//
// If the function succeeds, the device will not be powered off immediately,
// but after some time (typically a few milliseconds).
//
// Returns `false` if the operation fails (likely due to uninitialized power
// management).
bool npm1300_enter_shipmode(void);

// Starts the asynchronous measurement
//
// The measurement is started as soon as possible and finished in
// hundreds of milliseconds. The result is reported using the callback.
//
// The function returns `false` if the measurement cannot be started
// (e.g. because the previous measurement is still in progress or
// the the driver is not initialized).
bool npm1300_measure(npm1300_report_callback_t callback, void* context);

// Synchroneous version of the `pmic_measure` function.
//
// Use only for testing purposes, as it blocks the execution until
// the measurement is done.
//
// Returns `true` if the measurement was successful and the report
// is stored in the `report` structure.
bool npm1300_measure_sync(npm1300_report_t* report);

// Enables or disables the charging.
//
// The function returns `false` if the operation cannot be performed.
bool npm1300_set_charging(bool enable);

// Sets the charging current limit [mA].
//
// The current value must be in the range defined by the
// `NPM1300_CHARGING_LIMIT_MIN` and `NPM1300_CHARGING_LIMIT_MAX` constants.
//
// The function returns `false` if the operation cannot be performed.
bool npm1300_set_charging_limit(int i_charge);

// Gets the charging current limit [mA].
int npm1300_get_charging_limit(void);

typedef enum {
  NPM1300_BUCK_MODE_AUTO,
  NPM1300_BUCK_MODE_PWM,
  NPM1300_BUCK_MODE_PFM,
} npm1300_buck_mode_t;

// Set the buck voltage regulator mode
bool npm1300_set_buck_mode(npm1300_buck_mode_t buck_mode);

#endif  // TREZORHAL_NPM1300_H
