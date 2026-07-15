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

#include <io/pmic.h>
#include <io/power_manager.h>
#include <sys/systick.h>

#include "../power_manager_poll.h"

#ifdef KERNEL_MODE

// Minimal power_manager implementation for boards whose only power-management
// hardware is a GPIO power latch (soft power switch), exposed through the PMIC
// interface (see power_latch/power_latch.c). It provides the full
// power_manager API on top of that PMIC:
//
//   - "hibernate" / power off  -> pmic_enter_shipmode() (release the latch)
//   - "turn on" / init         -> pmic_init() (engage the latch)
//
// There is no battery gauge, charger or wireless input, so the reported state
// is a fixed "externally powered, active" and all charging/report calls are
// no-ops. This mirrors how the npm1300 backend implements the same interface.

// Time allowed for the supply rail to collapse after the latch is released in
// pm_hibernate(), before treating the request as rejected. This is a passive
// discharge of the rail's bulk capacitance (not a hardware ship-mode), so it
// needs generous margin over the observed collapse time.
#define PM_HIBERNATE_COLLAPSE_MS 2000

static bool g_initialized = false;
static bool g_suspended = false;

pm_status_t pm_init(bool inherit_state) {
  (void)inherit_state;

  // Engage the latch so the device stays powered once the button is released.
  pmic_init();

  if (!pm_poll_init()) {
    return PM_ERROR;
  }

  g_initialized = true;
  g_suspended = false;
  return PM_OK;
}

void pm_deinit(void) {
  pm_poll_deinit();
  g_initialized = false;
}

pm_status_t pm_hibernate(void) {
  if (!g_initialized) {
    return PM_NOT_INITIALIZED;
  }

  // Release the latch to cut the power supply and turn the device off. On a
  // self-powered device the supply collapses (after the bulk capacitance
  // discharges) and execution never reaches the return below. If the device is
  // kept alive by an external power source the latch has no effect, so -
  // mirroring the npm1300 backend's ship-mode contract - pm_hibernate() never
  // returns PM_OK and reports PM_REQUEST_REJECTED on fall-through.
  pmic_enter_shipmode();

  // Wait long enough for the rail to actually collapse before concluding the
  // request was rejected; the bulk caps can hold the supply up for a while.
  systick_delay_ms(PM_HIBERNATE_COLLAPSE_MS);

  // If we are still running, power was not actually cut.
  return PM_REQUEST_REJECTED;
}

pm_status_t pm_turn_on(void) {
  // Ensure the latch is engaged.
  pmic_init();
  return PM_OK;
}

pm_status_t pm_suspend(wakeup_flags_t* wakeup_reason) {
  // No low-power/suspend support on latch-only boards yet; the device simply
  // stays active.
  if (wakeup_reason != NULL) {
    *wakeup_reason = 0;
  }
  return PM_OK;
}

pm_status_t pm_get_state(pm_state_t* state) {
  if (state == NULL) {
    return PM_ERROR;
  }
  memset(state, 0, sizeof(*state));
  // Latch-only boards are treated as always powered and active. There is no
  // fuel gauge, charger or NTC, but we can report the measured cell voltage.
  state->power_status = PM_STATE_ACTIVE;
  state->charging_status = PM_BATTERY_IDLE;
  state->usb_connected = false;
  state->wireless_connected = false;
  state->ntc_connected = false;
  state->soc = 0;
  state->battery_temp = 0.0f;

  pmic_report_t pmic = {0};
  if (pmic_measure_sync(&pmic)) {
    state->battery_connected = true;
    state->battery_ocv = pmic.vbat;
  } else {
    state->battery_connected = false;
    state->battery_ocv = 0.0f;
  }
  return PM_OK;
}

pm_status_t pm_get_report(pm_report_t* report) {
  if (report == NULL) {
    return PM_ERROR;
  }
  memset(report, 0, sizeof(*report));
  report->power_state = PM_STATE_ACTIVE;

  pmic_report_t pmic = {0};
  if (pmic_measure_sync(&pmic)) {
    report->battery_voltage_v = pmic.vbat;
    report->system_voltage_v = pmic.vsys;
  }
  return PM_OK;
}

pm_status_t pm_charging_enable(void) { return PM_OK; }
pm_status_t pm_charging_disable(void) { return PM_OK; }
pm_status_t pm_charging_set_max_current(uint16_t current_ma) {
  (void)current_ma;
  return PM_OK;
}
pm_status_t pm_set_soc_target(uint8_t target) {
  (void)target;
  return PM_OK;
}

bool pm_is_charging(void) { return false; }
bool pm_usb_is_connected(void) { return false; }

bool pm_driver_suspend(void) {
  g_suspended = true;
  return true;
}
bool pm_driver_resume(void) {
  g_suspended = false;
  return true;
}
bool pm_driver_is_suspended(void) { return g_suspended; }

#endif  // KERNEL_MODE
