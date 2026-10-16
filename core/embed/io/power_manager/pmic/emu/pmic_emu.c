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

#include "../pmic_charger.h"
#include "pmic_emu.h"

// Range of charging-current limits the emulated charger accepts [mA]; the
// npm1300's, so the T3W1 emulator behaves like the T3W1.
#define PMIC_EMU_CHARGING_LIMIT_MIN 32
#define PMIC_EMU_CHARGING_LIMIT_MAX 800

typedef struct {
  bool initialized;
  pmic_report_t report;
  bool charging;
  int charging_limit_ma;
} pmic_emu_t;

static pmic_emu_t g_pmic_emu;

// A healthy single cell on battery power, discharging gently.
static const pmic_report_t pmic_emu_default_report = {
    .vbat = 3.7f,
    .vsys = 3.7f,
    .ibat = 50.0f,
    .ntc_temp = 20.0f,
    .die_temp = 25.0f,
    .ibat_valid = true,
    .ntc_present = true,
    .vbus_present = false,
    .ntc_disconnected = false,
    .battery_disconnected = false,
};

bool pmic_init(void) {
  pmic_emu_t* drv = &g_pmic_emu;
  memset(drv, 0, sizeof(*drv));
  drv->report = pmic_emu_default_report;
  drv->charging_limit_ma = PMIC_EMU_CHARGING_LIMIT_MIN;
  drv->initialized = true;
  return true;
}

void pmic_deinit(void) { g_pmic_emu.initialized = false; }

// The emulated chip has no background work to pause.
bool pmic_suspend(void) { return true; }
bool pmic_resume(void) { return true; }
bool pmic_is_suspended(void) { return true; }

uint8_t pmic_restart_cause(void) { return 0; }

// Ship mode is the policy's last word before the device powers off; on the
// host the power manager's glue exits the process, so there is nothing to do.
bool pmic_enter_shipmode(void) { return g_pmic_emu.initialized; }

bool pmic_measure(pmic_report_callback_t callback, void* context) {
  pmic_emu_t* drv = &g_pmic_emu;
  if (!drv->initialized) {
    return false;
  }
  // A measurement completes at once
  pmic_report_t report = drv->report;
  if (callback != NULL) {
    callback(context, &report);
  }
  return true;
}

bool pmic_measure_sync(pmic_report_t* report) {
  pmic_emu_t* drv = &g_pmic_emu;
  if (!drv->initialized) {
    return false;
  }
  *report = drv->report;
  return true;
}

// --- Charger extension -------------------------------------------------------

bool pmic_set_charging(bool enable) {
  g_pmic_emu.charging = enable;
  return true;
}

bool pmic_set_charging_limit(int i_charge) {
  if (i_charge < PMIC_EMU_CHARGING_LIMIT_MIN ||
      i_charge > PMIC_EMU_CHARGING_LIMIT_MAX) {
    return false;
  }
  g_pmic_emu.charging_limit_ma = i_charge;
  return true;
}

int pmic_get_charging_limit(void) { return g_pmic_emu.charging_limit_ma; }

bool pmic_clear_charger_errors(void) {
  g_pmic_emu.report.charger_fault = false;
  return true;
}

int pmic_charging_limit_min(void) { return PMIC_EMU_CHARGING_LIMIT_MIN; }

// --- Emulator knobs ----------------------------------------------------------

pmic_report_t* pmic_emu_inputs(void) { return &g_pmic_emu.report; }

bool pmic_emu_charging_on(void) { return g_pmic_emu.charging; }

int pmic_emu_charging_limit_ma(void) { return g_pmic_emu.charging_limit_ma; }
