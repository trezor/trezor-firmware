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

#include "../battery.h"
#include "battery_emu.h"

// Emulator fuel gauge: the test owns the state of charge and the brownout
// verdict, so UI and device tests can walk the policy through its thresholds
// without a battery model. The estimator entry points accept measurements and
// ignore them; the OCV helpers return a plausible single-cell voltage.

typedef struct {
  bool initialized;
  bool locked;
  float soc;
  float P;
  bool critical;
} bat_emu_t;

static bat_emu_t g_bat_emu;

void bat_init(void) {
  bat_emu_t* drv = &g_bat_emu;
  memset(drv, 0, sizeof(*drv));
  drv->soc = 1.0f;
  drv->initialized = true;
}

ts_t bat_fg_set_soc(float soc, float P) {
  bat_emu_t* drv = &g_bat_emu;
  if (!drv->initialized) {
    return TS_ENOINIT;
  }
  drv->soc = soc;
  drv->P = P;
  drv->locked = true;
  return TS_OK;
}

ts_t bat_fg_feed_sample(float voltage_V, float current_mA, float temp_C) {
  (void)voltage_V;
  (void)current_mA;
  (void)temp_C;
  return g_bat_emu.initialized ? TS_OK : TS_ENOINIT;
}

ts_t bat_fg_initial_guess(void) {
  bat_emu_t* drv = &g_bat_emu;
  if (!drv->initialized) {
    return TS_ENOINIT;
  }
  drv->locked = true;
  return TS_OK;
}

bool bat_fg_is_locked(void) {
  return g_bat_emu.initialized && g_bat_emu.locked;
}

ts_t bat_fg_get_state(bat_fg_state_t* data) {
  bat_emu_t* drv = &g_bat_emu;
  if (!drv->initialized) {
    return TS_ENOINIT;
  }
  if (data == NULL) {
    return TS_EINVAL;
  }
  data->soc = drv->soc;
  data->soc_latched = drv->soc;
  data->P = drv->P;
  return TS_OK;
}

ts_t bat_fg_update(uint32_t dt_ms, float voltage_V, float current_mA,
                   float temp_C) {
  (void)dt_ms;
  (void)voltage_V;
  (void)current_mA;
  (void)temp_C;
  return g_bat_emu.initialized ? TS_OK : TS_ENOINIT;
}

ts_t bat_fg_compensate_soc(float* soc, uint32_t elapsed_s,
                           float avg_bat_current_mA, float avg_temp_C) {
  (void)soc;  // the test sets the SoC; nothing to compensate
  (void)elapsed_s;
  (void)avg_bat_current_mA;
  (void)avg_temp_C;
  return g_bat_emu.initialized ? TS_OK : TS_ENOINIT;
}

bool bat_eval_critical(bool currently_critical, float voltage_V,
                       float current_mA, float temp_C) {
  (void)currently_critical;
  (void)voltage_V;
  (void)current_mA;
  (void)temp_C;
  return g_bat_emu.critical;
}

float bat_fetch_cycle_increment(void) { return 0.0f; }

// A linear stand-in for the cell's OCV curve: 3.0 V empty, 3.6 V full.
float bat_soc_to_ocv(float soc, float temp_C, bool discharging_mode) {
  (void)temp_C;
  (void)discharging_mode;
  return 3.0f + 0.6f * soc;
}

float bat_meas_to_ocv(float voltage_V, float current_mA, float temp_C) {
  (void)current_mA;
  (void)temp_C;
  return voltage_V;
}

// --- Emulator knobs ----------------------------------------------------------

void bat_emu_set_soc(float soc) {
  bat_emu_t* drv = &g_bat_emu;
  if (soc < 0.0f) {
    soc = 0.0f;
  }
  if (soc > 1.0f) {
    soc = 1.0f;
  }
  drv->soc = soc;
  drv->locked = true;
}

void bat_emu_set_critical(bool critical) { g_bat_emu.critical = critical; }
