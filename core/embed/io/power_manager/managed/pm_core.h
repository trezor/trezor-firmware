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

#include <io/pmic.h>
#include <io/power_manager.h>

// Pure core of the managed power-manager policy.
//
// Everything in here is a function of (core state, inputs, time): the power
// state machine, the per-sample pipeline (power sources, brownout, fuel gauge,
// charging), recovery snapshot/restore and the requests (suspend, hibernate,
// turn on). It never touches hardware, timers, locks, backup RAM, the RTC or
// telemetry. Instead each step returns a `pm_actions_t` that the glue in
// power_manager.c carries out. Time arrives as a millisecond tick from the
// glue, and elapsed real time (for self-discharge compensation) as seconds.
//
// That is what makes it testable: a host test links this core against a fake
// fuel gauge and a fake charger, feeds it samples with a fake clock, and checks
// the states it reaches and the actions it asks for.
//
// The only globals the core reaches for are the fuel gauge (battery.h), which
// is itself pure computation on its own state.

// --- Policy constants --------------------------------------------------------
// Behaviour of the state machine itself, the same on every board. Anything
// that depends on the board or the battery pack arrives in pm_config_t.

// Nominal sampling period; the first sample's dt before a real one is known
#define PM_TIMER_PERIOD_MS 100
// Time spent in SHUTTING_DOWN before giving up and hibernating
#define PM_SHUTDOWN_TIMEOUT_MS 15000
// Battery disconnection detection (no cell of any chemistry sits this low)
#define PM_BATTERY_DISCONNECTED_THR_V 0.5f
#define PM_BATTERY_DISCONNECTED_REC_V 0.8f
// Ambient temperature assumed for self-discharge compensation
#define PM_COMPENSATION_TEMP_C 25.0f

// Board tunables for the core, filled by the glue from the board header.
typedef struct {
  // SoC [%] at or below which the device enters power-save mode
  uint8_t low_soc_percent;
  // Backlight cap applied in power-save mode (0-255)
  uint8_t power_save_backlight;
  // Average battery drain of the board in each low-power mode [mA], used to
  // compensate the fuel gauge for the time spent there
  float suspend_current_ma;
  float hibernation_current_ma;
} pm_config_t;

// One charging-current derating band: below `max_temp_c` the charger may use
// `current_factor` of the pack's maximum.
typedef struct {
  float max_temp_c;
  float current_factor;
} pm_temp_band_t;

// Charger leaf state. Owned and interpreted by power_charging[_none].c; the
// shared core only stores it.
typedef struct {
  // configuration (from the leaf)
  uint16_t current_max_ma;      // pack's maximum charging current
  uint16_t limit_min_ma;        // smallest limit the charger accepts
  const pm_temp_band_t* bands;  // derating bands, ascending
  size_t band_count;

  // requests from the public API
  bool enabled;
  uint8_t soc_target;
  uint16_t max_limit_ma;

  // controller state
  uint16_t target_ma;
  bool soc_target_reached;
  float target_ocv_tau;

  // thermal limiter
  uint16_t temp_limit_ma;
  uint32_t temp_next_ms;
  bool temp_control_active;

  // charging-limited detector
  bool limited_latched;
  uint32_t limited_start_ms;
} pm_charging_t;

// Core state.
typedef struct {
  pm_config_t cfg;

  // time, as told by the glue
  uint32_t now_ms;
  uint32_t last_sample_ms;
  bool has_sample;

  // state machine
  pm_power_status_t state;
  bool request_suspend;
  bool request_exit_suspend;
  bool request_hibernate;
  bool request_turn_on;
  uint32_t shutdown_deadline_ms;

  // Set once a sample has been processed with the fuel gauge locked, i.e. the
  // reported state is meaningful. Cleared by pm_core_resume().
  bool stabilized;

  // latest sample and what the pipeline derived from it
  pmic_report_t pmic;
  bool usb_connected;
  bool wireless_connected;
  bool battery_disconnected;
  bool battery_low;
  bool battery_critical;
  bool fully_charged;
  float battery_ocv;
  uint8_t soc_ceiled;

  // resume-from-suspend bookkeeping
  bool woke_up_from_suspend;
  uint32_t time_in_suspend_s;

  pm_charging_t chg;
} pm_core_t;

// Per-sample inputs from the glue.
typedef struct {
  pmic_report_t pmic;
  // Wireless charger delivering power (false on boards without one)
  bool wireless_connected;
} pm_sample_t;

// What the glue has to carry out after a core step. Zero means nothing.
typedef struct {
  // A locked-gauge sample was processed: the snapshot is current, the recovery
  // data should be persisted.
  bool sample_complete;
  // An external power source appeared or disappeared (notify listeners).
  bool power_source_changed;
  // Apply the backlight cap (entering ACTIVE / POWER_SAVE).
  bool set_backlight;
  uint8_t backlight_level;
  // Put the PMIC into ship mode (re-hibernate while already hibernated).
  bool enter_shipmode;
  // Persist the recovery data and power the device off (entered HIBERNATE).
  bool power_off;

  // Charger leaf: reconcile the charger with the controller's decision.
  // Only meaningful when `apply_charging` is set; see pm_charging_apply().
  bool apply_charging;
  bool charging_on;
  uint16_t charging_limit_ma;
  bool clear_charger_errors;
} pm_actions_t;

// Requests the public API turns into state-machine inputs.
typedef enum {
  PM_REQ_SUSPEND,
  PM_REQ_EXIT_SUSPEND,
  PM_REQ_HIBERNATE,
  PM_REQ_TURN_ON,
} pm_request_t;

// --- Lifecycle ---------------------------------------------------------------

// Zeroes the core. Must precede the first sample; the glue may then start
// sampling before pm_core_init() configures the policy (samples taken in
// between only prime the fuel gauge).
void pm_core_reset(pm_core_t* core);

// Configures the core. `recovery` is the persisted state from the previous
// run or NULL when none is available; `elapsed_s` is how long the device was
// off since that snapshot (0 when unknown or not applicable), used to
// compensate the recovered SoC for the hibernation drain. With `inherit_state`
// the state machine resumes where the bootloader left it; otherwise it starts
// in HIBERNATE and waits for PM_REQ_TURN_ON.
//
// The fuel gauge must be initialized (bat_init()) before this call.
void pm_core_init(pm_core_t* core, const pm_config_t* cfg, bool inherit_state,
                  const pm_recovery_data_t* recovery, uint32_t elapsed_s);

// Fills the recovery snapshot (everything except the version and timestamp,
// which the glue adds).
void pm_core_recovery(const pm_core_t* core, pm_recovery_data_t* recovery);

// Tells the core the device is back from suspend after `elapsed_s` seconds.
// The next sample compensates the gauge for the suspend drain instead of
// running the estimator; the reported state is not meaningful until then.
void pm_core_resume(pm_core_t* core, uint32_t elapsed_s);

// --- Stepping ----------------------------------------------------------------

// Processes one PMIC sample at time `now_ms` and runs the state machine.
void pm_core_sample(pm_core_t* core, const pm_sample_t* sample, uint32_t now_ms,
                    pm_actions_t* actions);

// Feeds a request into the state machine at time `now_ms`.
void pm_core_request(pm_core_t* core, pm_request_t request, uint32_t now_ms,
                     pm_actions_t* actions);

// Runs the state machine at time `now_ms` until it settles. Used by the two
// steps above; exposed for the charging API, which may change the inputs.
void pm_core_run_state_machine(pm_core_t* core, uint32_t now_ms,
                               pm_actions_t* actions);

// --- Queries -----------------------------------------------------------------

// Pure snapshot of the reported state.
void pm_core_get_state(const pm_core_t* core, pm_state_t* state);

// True when the battery thermistor reads as a fault. A board without an NTC
// never reports one (see pmic_report_t::ntc_present).
static inline bool pm_core_ntc_fault(const pm_core_t* core) {
  return core->pmic.ntc_present && core->pmic.ntc_disconnected;
}

// Wrap-safe "has `deadline_ms` passed at `now_ms`" for 32-bit tick counters.
static inline bool pm_core_deadline_passed(uint32_t now_ms,
                                           uint32_t deadline_ms) {
  return (int32_t)(now_ms - deadline_ms) >= 0;
}

// --- Charger leaf ------------------------------------------------------------
// Implemented by exactly one of power_charging.c (PMIC with a charger) and
// power_charging_none.c (no charger), selected by build.rs. The shared core
// calls these unconditionally.

// Sets the leaf's configuration and defaults. The one place the leaf may ask
// the charger driver anything (its minimum limit).
void pm_charging_init(pm_core_t* core);

// Charging controller: decides the charger's current limit and enable state
// from the latest sample and records the decision in `actions`.
void pm_charging_step(pm_core_t* core, pm_actions_t* actions);

// True while the policy is actively charging the battery: charging enabled,
// an external source present, and neither the full-charge nor the SoC-target
// stop condition reached.
bool pm_charging_active(const pm_core_t* core);

// Advances the "charging limited" detector from the latest sample.
void pm_charging_update_limited(pm_core_t* core);

// Public-API requests, pure: they only change the leaf state. Each returns
// false when the request cannot be honoured (no charger, out of range).
bool pm_charging_set_enabled(pm_core_t* core, bool enabled);
bool pm_charging_set_max_limit(pm_core_t* core, uint16_t current_ma);
bool pm_charging_set_soc_target(pm_core_t* core, uint8_t target);

// Carries out the charging part of `actions` on the charger hardware. The
// leaf's only hardware-facing function besides the init query.
void pm_charging_apply(const pm_actions_t* actions);
