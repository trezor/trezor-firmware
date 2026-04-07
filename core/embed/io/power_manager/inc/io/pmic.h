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

#pragma once

#include <trezor_types.h>

// Charging current limits
// - range of pmic is 32-800mA
// - used battery limit is 180mA
#define PMIC_CHARGING_LIMIT_MIN 32       // mA
#define PMIC_CHARGING_LIMIT_MAX 180      // mA
#define PMIC_CHARGING_LIMIT_DEFAULT 180  // mA

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
  // (for debugging purposes, see the datasheet)
  uint8_t ibat_meas_status;
  // BCHGCHARGESTATUS register value
  // (for debugging purposes, see the datasheet)
  uint8_t charge_status;
  uint8_t charge_err;
  uint8_t charge_sensor_err;
  uint8_t buck_status;
  uint8_t usb_status;
  // NTC disconnection flag
  bool ntc_disconnected;
  // battery disconnected flag
  bool battery_disconnected;
  // Charging phase flags decoded from charge_status
  // - cc_phase: Constant-Current phase (charge_status bit 3)
  // - cv_phase: Constant-Voltage phase (charge_status bit 5)
  bool cc_phase;
  bool cv_phase;
} pmic_report_t;

typedef void (*pmic_report_callback_t)(void* context, pmic_report_t* report);

// Initializes PMIC driver
bool pmic_init(void);

// Deinitializes  PMIC driver
void pmic_deinit(void);

// Suspends driver activity so the CPU can enter low-power mode.
//
// Suspending may take some time if the driver is currently
// performing an operation. Caller may check the status by
// pmic_is_suspended().
bool pmic_suspend(void);

// Resumes the driver operation after it has been suspended.
bool pmic_resume(void);

// Checks whether the driver is suspended.
bool pmic_is_suspended(void);

// Gets the cause of the last restart
uint8_t pmic_restart_cause(void);

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
bool pmic_enter_shipmode(void);

// Starts the asynchronous measurement
//
// The measurement is started as soon as possible and finished in
// hundreds of milliseconds. The result is reported using the callback.
//
// The function returns `false` if the measurement cannot be started
// (e.g. because the previous measurement is still in progress or
// the the driver is not initialized).
bool pmic_measure(pmic_report_callback_t callback, void* context);

// Synchroneous version of the `pmic_measure` function.
//
// Use only for testing purposes, as it blocks the execution until
// the measurement is done.
//
// Returns `true` if the measurement was successful and the report
// is stored in the `report` structure.
bool pmic_measure_sync(pmic_report_t* report);

// Enables or disables the charging.
//
// The function returns `false` if the operation cannot be performed.
bool pmic_set_charging(bool enable);

// Sets the charging current limit [mA].
//
// The current value must be in the range defined by the
// `NPM1300_CHARGING_LIMIT_MIN` and `NPM1300_CHARGING_LIMIT_MAX` constants.
//
// The function returns `false` if the operation cannot be performed.
bool pmic_set_charging_limit(int i_charge);

// Gets the charging current limit [mA].
int pmic_get_charging_limit(void);

typedef enum {
  PMIC_BUCK_MODE_AUTO,
  PMIC_BUCK_MODE_PWM,
  PMIC_BUCK_MODE_PFM,
} pmic_buck_mode_t;

// Set the buck voltage regulator mode
bool pmic_set_buck_mode(pmic_buck_mode_t buck_mode);

// Clears all battery charger errors.
bool pmic_clear_charger_errors(void);
