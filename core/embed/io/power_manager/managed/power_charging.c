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

// Charger leaf of the managed power-manager policy for a PMIC with a charger:
// the charging controller, the thermal (charging-current) limiter, the
// charging-limited detector and the leaf's part of the public charging API.
// Built only when the selected PMIC has a charger (USE_CHARGER); boards
// without one build power_charging_none.c instead.
//
// Pure, like the rest of pm_core: it decides and records the decision in
// pm_actions_t. The two exceptions are marked below: pm_charging_init() asks
// the charger driver for its minimum limit once, and pm_charging_apply() is
// the glue that carries the decision to the charger.

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <math.h>

#include "../fuel_gauge/battery.h"
#include "../pmic/pmic_charger.h"
#include "pm_core.h"

// --- Board tunables this leaf needs ------------------------------------------
// See the board-tunables section in power_manager_internal.h.
#ifndef BATTERY_CHARGING_CURRENT_MAX_MA
#error "Board header must define BATTERY_CHARGING_CURRENT_MAX_MA"
#endif
#ifndef BATTERY_CHARGE_TEMP_BANDS
#error "Board header must define BATTERY_CHARGE_TEMP_BANDS"
#endif

// Thermal controller switch, comment out to disable the thermal controller.
#define PM_ENABLE_TEMP_CONTROL

// Debounce between thermal-limit changes
#define PM_TEMP_CONTROL_IDLE_PERIOD_MS (2 * 60 * 1000)  // 2 minutes

// Temperature controller LUT: the battery pack's charging-current derating
// bands, supplied by the board header.
static const pm_temp_band_t temp_bands[] = BATTERY_CHARGE_TEMP_BANDS;

#ifdef PM_ENABLE_TEMP_CONTROL
static void pm_temperature_controller(pm_core_t* core);
#endif

void pm_charging_init(pm_core_t* core) {
  pm_charging_t* chg = &core->chg;

  memset(chg, 0, sizeof(*chg));

  chg->current_max_ma = BATTERY_CHARGING_CURRENT_MAX_MA;
  // The one driver query in the leaf: the smallest limit this charger takes.
  chg->limit_min_ma = pmic_charging_limit_min();
  chg->bands = temp_bands;
  chg->band_count = ARRAY_LENGTH(temp_bands);

  // Enable charging by default to max current, no SoC target
  chg->enabled = true;
  chg->soc_target = 100;
  chg->max_limit_ma = chg->current_max_ma;
  chg->temp_limit_ma = chg->current_max_ma;
}

bool pm_charging_active(const pm_core_t* core) {
  const pm_charging_t* chg = &core->chg;
  return chg->enabled && !core->fully_charged && !chg->soc_target_reached &&
         (core->usb_connected || core->wireless_connected);
}

void pm_charging_update_limited(pm_core_t* core) {
  pm_charging_t* chg = &core->chg;

  // "Charging limited" = the charger sits in its constant-current phase but
  // delivers noticeably less than the target current for a sustained period
  // (weak supply, cable, ...). Assert after the predicate holds continuously
  // for FILTER_ASSERT_MS; clear immediately when it breaks or charging stops.
  const float MAX_DIFF_MA = 15;  // tolerance below target current
  const uint32_t FILTER_ASSERT_MS = 5000;

  bool predicate = false;
  if (pm_charging_active(core) && core->pmic.ibat_valid) {
    float iabs_ma = fabsf(core->pmic.ibat);  // ibat < 0 => charging
    predicate =
        core->pmic.cc_phase && (iabs_ma < (chg->target_ma - MAX_DIFF_MA));
  }

  if (predicate) {
    uint32_t now = core->now_ms;
    if (chg->limited_start_ms == 0U) {
      chg->limited_start_ms = now;
    } else if (!chg->limited_latched &&
               (now - chg->limited_start_ms) >= FILTER_ASSERT_MS) {
      chg->limited_latched = true;
    }
  } else {
    chg->limited_start_ms = 0U;
    chg->limited_latched = false;
  }
}

void pm_charging_step(pm_core_t* core, pm_actions_t* actions) {
  pm_charging_t* chg = &core->chg;

  if (!chg->enabled) {
    // Charging is disabled
    if (chg->target_ma != 0) {
      chg->target_ma = 0;
    } else {
      // No action required
      return;
    }
  } else if (core->usb_connected) {
    chg->target_ma = chg->current_max_ma;
  } else if (core->wireless_connected) {
    chg->target_ma = chg->current_max_ma;
  } else {
    // Charging enabled but no external power source, clear charging target
    chg->target_ma = 0;
  }

  // charging current software limit
  if (chg->target_ma > chg->max_limit_ma) {
    chg->target_ma = chg->max_limit_ma;
  }

#ifdef PM_ENABLE_TEMP_CONTROL
  pm_temperature_controller(core);
#endif

  if (pm_core_ntc_fault(core)) {
    // Never charge a cell whose temperature we cannot see.
    chg->target_ma = 0;
  }

  if (chg->soc_target == 100) {
    chg->soc_target_reached = false;
  } else if (fabsf((-core->pmic.ibat) - (float)chg->target_ma) <= 20.0f) {
    // Translate SoC target to charging voltage via battery model
    float target_ocv_voltage_v =
        bat_soc_to_ocv(chg->soc_target / 100.0f, core->pmic.ntc_temp, false);

    float battery_ocv_v =
        bat_meas_to_ocv(core->pmic.vbat, core->pmic.ibat, core->pmic.ntc_temp);

    chg->target_ocv_tau = (chg->target_ocv_tau * 0.95f) +
                          (battery_ocv_v * 0.05f);  // Exponential smoothing

    if (chg->target_ocv_tau > target_ocv_voltage_v) {
      // current voltage is within tight bounds of target voltage,
      // we may also force SoC estimate to target value.
      if (chg->target_ocv_tau < target_ocv_voltage_v + 0.15f) {
        bat_fg_state_t fg_state;
        bat_fg_get_state(&fg_state);
        bat_fg_set_soc((chg->soc_target / 100.0f) - 0.0001f, fg_state.P);
      }

      chg->soc_target_reached = true;
    }
  } else if (core->soc_ceiled < chg->soc_target) {
    chg->soc_target_reached = false;
  }

  if (chg->soc_target_reached) {
    chg->target_ma = 0;
  }

  // Record the decision; the glue reconciles the charger with it.
  actions->apply_charging = true;
  actions->charging_limit_ma = chg->target_ma;
  actions->charging_on = (chg->target_ma != 0);
  actions->clear_charger_errors =
      actions->charging_on && core->pmic.charger_fault;
}

#ifdef PM_ENABLE_TEMP_CONTROL

static void pm_temperature_controller(pm_core_t* core) {
  pm_charging_t* chg = &core->chg;

  if (pm_core_deadline_passed(core->now_ms, chg->temp_next_ms)) {
    uint16_t temp_limit_ma = 0;  // Default to safety limit
    for (size_t i = 0; i < chg->band_count; ++i) {
      if (core->pmic.ntc_temp < chg->bands[i].max_temp_c) {
        temp_limit_ma =
            (uint16_t)(chg->current_max_ma * chg->bands[i].current_factor);
        break;
      }
    }

    // If the temperature limit has changed, update the limit and reset the
    // debounce timer
    if (chg->temp_limit_ma != temp_limit_ma) {
      chg->temp_limit_ma = temp_limit_ma;
      chg->temp_next_ms = core->now_ms + PM_TEMP_CONTROL_IDLE_PERIOD_MS;
    }
  }

  if (chg->target_ma > chg->temp_limit_ma) {
    // Limit the charging current by temperature controller
    chg->target_ma = chg->temp_limit_ma;
    chg->temp_control_active = true;
  } else {
    chg->temp_control_active = false;
  }
}

#endif  // PM_ENABLE_TEMP_CONTROL

// --- Public-API requests -----------------------------------------------------

bool pm_charging_set_enabled(pm_core_t* core, bool enabled) {
  core->chg.enabled = enabled;
  return true;
}

bool pm_charging_set_max_limit(pm_core_t* core, uint16_t current_ma) {
  pm_charging_t* chg = &core->chg;

  if (current_ma > chg->current_max_ma || current_ma < chg->limit_min_ma) {
    return false;
  }

  chg->max_limit_ma = current_ma;
  return true;
}

bool pm_charging_set_soc_target(pm_core_t* core, uint8_t target) {
  core->chg.soc_target = target;
  return true;
}

// --- Glue: carry the decision to the charger ---------------------------------

void pm_charging_apply(const pm_actions_t* actions) {
  if (!actions->apply_charging) {
    return;
  }

  if (actions->charging_limit_ma != pmic_get_charging_limit()) {
    pmic_set_charging_limit(actions->charging_limit_ma);
  }

  if (!actions->charging_on) {
    pmic_set_charging(false);
  } else {
    // Clear and release charger if it has any errors
    if (actions->clear_charger_errors) {
      pmic_clear_charger_errors();
    }
    pmic_set_charging(true);
  }
}

#endif  // KERNEL_MODE
