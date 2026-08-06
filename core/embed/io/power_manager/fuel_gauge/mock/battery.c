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

#ifdef KERNEL_MODE

#include <trezor_rtl.h>

#include "../battery.h"

// Mock fuel gauge for boards that have no gauged battery (e.g. a latch board
// whose only power hardware is a soft power switch). It satisfies the
// fuel_gauge/battery.h interface with trivial behaviour: the cell is always
// reported as full and healthy, mirroring how such a board is treated as
// "always adequately powered". There is no estimator, so `P` is ignored and the
// OCV-curve helpers - which are only exercised by the charger precharge
// controller (compiled out when USE_CHARGER is off) - return passthrough
// values.

// Nominal open-circuit voltage reported by bat_soc_to_ocv() when it is queried
// at all. Not physically meaningful; this gauge is used on boards without a
// charger, so the value never drives a real decision.
#define BAT_MOCK_NOMINAL_OCV_V 3.7f

// State-of-charge handed back by bat_fg_get_state(). Defaults to full and is
// overwritten verbatim by bat_fg_set_soc() so a set/get round-trip (used by the
// backup-RAM recovery path) is consistent.
static float g_soc = 1.0f;

void bat_init(void) { g_soc = 1.0f; }

ts_t bat_fg_set_soc(float soc, float P) {
  (void)P;
  g_soc = soc;
  return TS_OK;
}

ts_t bat_fg_feed_sample(float voltage_V, float current_mA, float temp_C) {
  (void)voltage_V;
  (void)current_mA;
  (void)temp_C;
  return TS_OK;
}

ts_t bat_fg_initial_guess(void) { return TS_OK; }

bool bat_fg_is_locked(void) { return true; }

ts_t bat_fg_get_state(bat_fg_state_t* data) {
  if (data == NULL) {
    return TS_EINVAL;
  }
  data->soc = g_soc;
  data->soc_latched = g_soc;
  data->P = 0.0f;
  return TS_OK;
}

ts_t bat_fg_update(uint32_t dt_ms, float voltage_V, float current_mA,
                   float temp_C) {
  (void)dt_ms;
  (void)voltage_V;
  (void)current_mA;
  (void)temp_C;
  return TS_OK;
}

ts_t bat_fg_compensate_soc(float* soc, uint32_t elapsed_s,
                           float avg_bat_current_mA, float avg_temp_C) {
  (void)soc;  // leave the caller's SoC unchanged - nothing to compensate
  (void)elapsed_s;
  (void)avg_bat_current_mA;
  (void)avg_temp_C;
  return TS_OK;
}

bool bat_eval_critical(bool currently_critical, float voltage_V,
                       float current_mA, float temp_C) {
  (void)currently_critical;
  (void)voltage_V;
  (void)current_mA;
  (void)temp_C;
  // No gauged battery - never assert the brownout-critical condition. The
  // external-power override is handled by the caller.
  return false;
}

float bat_fetch_cycle_increment(void) { return 0.0f; }

float bat_soc_to_ocv(float soc, float temp_C, bool discharging_mode) {
  (void)soc;
  (void)temp_C;
  (void)discharging_mode;
  return BAT_MOCK_NOMINAL_OCV_V;
}

float bat_meas_to_ocv(float voltage_V, float current_mA, float temp_C) {
  (void)current_mA;
  (void)temp_C;
  return voltage_V;
}

#endif
