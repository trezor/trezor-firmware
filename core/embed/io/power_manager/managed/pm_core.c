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

#include "../fuel_gauge/battery.h"
#include "pm_core.h"

// --- Lifecycle ---------------------------------------------------------------

void pm_core_reset(pm_core_t* core) { memset(core, 0, sizeof(*core)); }

void pm_core_init(pm_core_t* core, const pm_config_t* cfg, bool inherit_state,
                  const pm_recovery_data_t* recovery, uint32_t elapsed_s) {
  core->cfg = *cfg;

  if (recovery != NULL) {
    float soc = recovery->soc;

    // Compensate the recovered SoC for the time the device was off.
    if (elapsed_s > 0) {
      bat_fg_compensate_soc(&soc, elapsed_s, core->cfg.hibernation_current_ma,
                            PM_COMPENSATION_TEMP_C);
    }

    core->battery_critical = recovery->bat_critical;
    bat_fg_set_soc(soc, recovery->P);
  } else {
    bat_fg_initial_guess();
  }

  if (inherit_state) {
    // Inherit the state the bootloader left in the recovery data. Without
    // recovery data start in POWER_SAVE, the lowest active state.
    core->state = (recovery != NULL) ? recovery->bootloader_exit_state
                                     : PM_STATE_POWER_SAVE;
  } else {
    // Start in the lowest state and wait for the boot sequence to finish
    // (PM_REQ_TURN_ON).
    core->state = PM_STATE_HIBERNATE;
  }

  pm_charging_init(core);
}

void pm_core_recovery(const pm_core_t* core, pm_recovery_data_t* recovery) {
  bat_fg_state_t fg_state;
  bat_fg_get_state(&fg_state);

  recovery->soc = fg_state.soc;
  recovery->P = fg_state.P;
  recovery->bat_critical = core->battery_critical;
  recovery->bootloader_exit_state = core->state;
}

void pm_core_resume(pm_core_t* core, uint32_t elapsed_s) {
  core->woke_up_from_suspend = true;
  core->time_in_suspend_s = elapsed_s;
  core->stabilized = false;
}

// --- Sample pipeline ---------------------------------------------------------

static void pm_core_parse_power_sources(pm_core_t* core,
                                        const pm_sample_t* sample,
                                        pm_actions_t* actions) {
  if (core->pmic.vbus_present != core->usb_connected) {
    core->usb_connected = core->pmic.vbus_present;
    actions->power_source_changed = true;
  }

  if (sample->wireless_connected != core->wireless_connected) {
    core->wireless_connected = sample->wireless_connected;
    actions->power_source_changed = true;
  }

  // Battery-critical (brownout) evaluation.
  //
  // Brownout is a safety concern and is kept out of the fuel-gauge precision
  // budget: USB present means we are externally powered, so never
  // brownout-critical; otherwise the decision (including hysteresis and the
  // set/clear thresholds) is delegated to the chemistry-specific gauge, which
  // knows what its cell and precision can actually support. See
  // bat_eval_critical().
  if (core->usb_connected) {
    core->battery_critical = false;
  } else {
    core->battery_critical =
        bat_eval_critical(core->battery_critical, core->pmic.vbat,
                          core->pmic.ibat, core->pmic.ntc_temp);
  }
}

void pm_core_sample(pm_core_t* core, const pm_sample_t* sample, uint32_t now_ms,
                    pm_actions_t* actions) {
  memset(actions, 0, sizeof(*actions));

  // Time since the previous sample drives the estimator
  uint32_t dt_ms =
      core->has_sample ? (now_ms - core->last_sample_ms) : PM_TIMER_PERIOD_MS;
  core->now_ms = now_ms;
  core->last_sample_ms = now_ms;
  core->has_sample = true;
  core->pmic = sample->pmic;

  // Battery disconnection, voltage based with hysteresis
  core->battery_disconnected =
      (core->pmic.vbat < PM_BATTERY_DISCONNECTED_THR_V) ||
      (core->battery_disconnected &&
       core->pmic.vbat < PM_BATTERY_DISCONNECTED_REC_V);

  pm_core_parse_power_sources(core, sample, actions);

  pm_charging_step(core, actions);
  pm_charging_update_limited(core);

  core->battery_ocv =
      bat_meas_to_ocv(core->pmic.vbat, core->pmic.ibat, core->pmic.ntc_temp);

  if (!bat_fg_is_locked()) {
    // Fuel gauge not locked yet, battery SoC not available, just sample the
    // battery data into the circular buffer.
    bat_fg_feed_sample(core->pmic.vbat, core->pmic.ibat, core->pmic.ntc_temp);
    return;
  }

  bat_fg_state_t fg_state;

  if (core->woke_up_from_suspend) {
    // Use the board's known drain to compensate the fuel gauge for the suspend
    // period instead of running the estimator over a gap. The period may be
    // long and the temperature may vary, so use the average ambient one.
    //
    // TODO: a single drain figure for every suspend; in practice it varies
    // with what stays active. Neglected for now since suspend is short-lived.
    if (core->time_in_suspend_s > 0) {
      bat_fg_get_state(&fg_state);
      bat_fg_compensate_soc(&fg_state.soc, core->time_in_suspend_s,
                            core->cfg.suspend_current_ma,
                            PM_COMPENSATION_TEMP_C);
      bat_fg_set_soc(fg_state.soc, fg_state.P);
    }
    core->woke_up_from_suspend = false;
  } else {
    bat_fg_update(dt_ms, core->pmic.vbat, core->pmic.ibat, core->pmic.ntc_temp);
  }

  // Charger reports termination: the battery is full.
  if (core->pmic.charge_complete) {
    // Force fuel gauge to 100%, keep the covariance
    core->fully_charged = true;
    bat_fg_get_state(&fg_state);
    bat_fg_set_soc(1.0f, fg_state.P);
  } else if (core->pmic.ibat > 0) {
    core->fully_charged = false;
  }

  // Ceil the float soc to user-friendly integer
  bat_fg_get_state(&fg_state);
  core->soc_ceiled = (uint8_t)(fg_state.soc_latched * 100 + 0.999f);

  // Low-battery threshold
  if (core->soc_ceiled <= core->cfg.low_soc_percent && !core->battery_low) {
    core->battery_low = true;
  } else if (core->soc_ceiled > core->cfg.low_soc_percent &&
             core->battery_low) {
    core->battery_low = false;
  }

  // Process state machine with updated battery and power source information
  pm_core_run_state_machine(core, now_ms, actions);

  actions->sample_complete = true;
  core->stabilized = true;
}

// --- Requests ----------------------------------------------------------------

void pm_core_request(pm_core_t* core, pm_request_t request, uint32_t now_ms,
                     pm_actions_t* actions) {
  memset(actions, 0, sizeof(*actions));

  switch (request) {
    case PM_REQ_SUSPEND:
      core->request_suspend = true;
      break;
    case PM_REQ_EXIT_SUSPEND:
      core->request_exit_suspend = true;
      break;
    case PM_REQ_HIBERNATE:
      core->request_hibernate = true;
      break;
    case PM_REQ_TURN_ON:
      core->request_turn_on = true;
      break;
  }

  pm_core_run_state_machine(core, now_ms, actions);
}

// --- Queries -----------------------------------------------------------------

void pm_core_get_state(const pm_core_t* core, pm_state_t* state) {
  state->usb_connected = core->usb_connected;
  state->wireless_connected = core->wireless_connected;
  // A board without a thermistor has nothing to be disconnected.
  state->ntc_connected = !pm_core_ntc_fault(core);

  if (pm_charging_active(core)) {
    state->charging_status = PM_BATTERY_CHARGING;
  } else if (!core->pmic.ibat_valid) {
    // No current sense: on battery and not charging means discharging.
    state->charging_status = PM_BATTERY_DISCHARGING;
  } else if (core->pmic.ibat > 0.0f) {
    state->charging_status = PM_BATTERY_DISCHARGING;
  } else {
    state->charging_status = PM_BATTERY_IDLE;
  }

  state->charging_limited = core->chg.limited_latched;
  state->battery_connected = !core->battery_disconnected;
  state->power_status = core->state;
  state->soc = core->soc_ceiled;
  state->battery_temp = core->pmic.ntc_temp;
  state->battery_ocv = core->battery_ocv;
  state->temp_control_active = core->chg.temp_control_active;
}

#endif  // KERNEL_MODE
