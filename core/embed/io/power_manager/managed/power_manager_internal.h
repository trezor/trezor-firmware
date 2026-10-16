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

#include <trezor_bsp.h>
#include <trezor_types.h>

#include <io/pmic.h>
#include <io/power_manager.h>
#ifdef USE_RTC
// Only for rtc_event_id_t below; every RTC user in this module is USE_RTC-only.
#include <sys/rtc_scheduler.h>
#endif
#include <sys/systimer.h>

#include "../wireless/stwlc38/stwlc38.h"

#ifdef USE_CHARGER
// Charger extension to the core PMIC interface. Implemented only by
// charger-capable PMICs, so the policy may only reach for it - including for
// its current limits below - when USE_CHARGER is set.
#include "../pmic/pmic_charger.h"
#endif

// --- Policy constants -------------------------------------------------------
// Behaviour of the state machine itself. The same on every board; anything
// that depends on the board or the battery pack is a board tunable below.

#define PM_TIMER_PERIOD_MS 100
#define PM_SHUTDOWN_TIMEOUT_MS 15000
#define PM_STABILIZATION_TIMEOUT_MS 2000

// Timeout after which the device automatically transit from suspend to
// hibernation
#define PM_AUTO_HIBERNATE_TIMEOUT_S (2 * 60 * 60)  // 2 hours

// Battery disconnection detection (no cell of any chemistry sits this low)
#define PM_BATTERY_DISCONNECTED_THR_V 0.5f  // battery disconnection detection
#define PM_BATTERY_DISCONNECTED_REC_V \
  0.8f  // recovery from disconnect detection

// Battery-critical (brownout) thresholds live in the chemistry-specific gauge
// (see bat_eval_critical() in fuel_gauge/*), since the correct set/clear
// mechanism depends on the cell and the gauge's precision.

// Thermal controller switch, comment out to disable the thermal controller.
// The thermal controller limits the *charging* current by temperature, so it
// is only meaningful when a charger is present.
#ifdef USE_CHARGER
#define PM_ENABLE_TEMP_CONTROL
#endif

// Debounce between thermal-limit changes
#define PM_TEMP_CONTROL_IDLE_PERIOD_MS (2 * 60 * 1000)  // 2 minutes

// --- Board tunables ---------------------------------------------------------
// Supplied by the board header (<trezor_bsp.h>), because they describe the
// board and its battery pack rather than the policy. Required, not defaulted:
// a missing value is a build error naming it, not a silently inherited number
// from another product. See docs/core/embed-arch/power-manager.md.
//
//   BATTERY_LOW_SOC_PERCENT          SoC [%] at/below which power-save starts
//   PM_POWER_SAVE_BACKLIGHT_LIMIT    backlight cap in power-save mode (0-255)
//   PM_SUSPEND_CURRENT_MA            board drain in suspend [mA]     (USE_RTC)
//   PM_HIBERNATION_CURRENT_MA        board drain in hibernation [mA] (USE_RTC)
//   BATTERY_CHARGING_CURRENT_MAX_MA  pack's max charging current [mA]
//                                                                 (USE_CHARGER)
//   BATTERY_CHARGE_TEMP_BANDS        {max_temp_C, current factor} bands,
//                                    ascending                    (USE_CHARGER)

#ifndef BATTERY_LOW_SOC_PERCENT
#error "Board header must define BATTERY_LOW_SOC_PERCENT"
#endif
#ifndef PM_POWER_SAVE_BACKLIGHT_LIMIT
#error "Board header must define PM_POWER_SAVE_BACKLIGHT_LIMIT"
#endif
#ifdef USE_RTC
#ifndef PM_SUSPEND_CURRENT_MA
#error "Board header must define PM_SUSPEND_CURRENT_MA"
#endif
#ifndef PM_HIBERNATION_CURRENT_MA
#error "Board header must define PM_HIBERNATION_CURRENT_MA"
#endif
#endif
#ifdef USE_CHARGER
#ifndef BATTERY_CHARGING_CURRENT_MAX_MA
#error "Board header must define BATTERY_CHARGING_CURRENT_MAX_MA"
#endif
#ifndef BATTERY_CHARGE_TEMP_BANDS
#error "Board header must define BATTERY_CHARGE_TEMP_BANDS"
#endif
#endif

// Power manager core driver structure
typedef struct {
  bool initialized;
  bool state_machine_stabilized;
  pm_power_status_t state;

  // Set if the driver was requested to suspend background operations.
  // IF so, the driver waits until the last operation is finished,
  // then enters suspended mode.
  bool suspending;

  // Set if the driver's background operations are suspended.
  bool suspended;

  uint8_t soc_ceiled;
  uint8_t soc_target;
  bool soc_target_reached;
  float target_battery_ocv_v_tau;
  float battery_ocv;

  // Battery charging state
  bool charging_enabled;
  uint16_t i_chg_target_ma;
  uint16_t i_chg_max_limit_ma;

  // Charging-limited detection filter state
  // - charging_limited_latched: current filtered state exposed to pm_state_t
  // - charging_limited_start_ms: timestamp when low-current-in-CC predicate
  //   started being true (0 when not timing)
  bool charging_limited_latched;
  uint32_t charging_limited_start_ms;

  // battery disconnection detection, voltage based
  bool battery_disconnected;

#ifdef PM_ENABLE_TEMP_CONTROL
  // Temp controller
  uint32_t temp_control_timeout;
  uint16_t i_chg_temp_limit_ma;
  bool temp_control_active;
#endif

  // Power source hardware state
  pmic_report_t pmic_data;
  stwlc38_report_t wireless_data;
  uint64_t pmic_last_update_us;
  uint32_t pmic_sampling_period_ms;
  bool pmic_measurement_ready;
  bool woke_up_from_suspend;

  // Power source logical state
  bool usb_connected;
  bool wireless_connected;
  bool fully_charged;
  bool battery_low;
  bool battery_critical;

  // Power mode request flags
  bool request_suspend;
  bool request_exit_suspend;
  bool request_hibernate;
  bool request_turn_on;
  bool shutdown_timer_elapsed;

  // Timers and timestamps
  systimer_t* monitoring_timer;
  systimer_t* shutdown_timer;
  uint32_t suspend_timestamp;
  uint32_t last_active_timestamp;
  uint32_t time_in_suspend_s;
#ifdef USE_RTC
  rtc_event_id_t autohibernate_event_id;
#endif

} pm_driver_t;

// State handler function definition
typedef struct {
  void (*enter)(pm_driver_t* drv);
  pm_power_status_t (*handle)(pm_driver_t* drv);
  void (*exit)(pm_driver_t* drv);
} pm_state_handler_t;

// Shared global driver instance
extern pm_driver_t g_pm;

// Power manager monitoring function called periodically to process data from
// PMIC and WLC, run fuel gauge, run charging controller and stimulates
// internal state machine.
void pm_monitor_power_sources(void);

// Power manager state machine automat driving internal state machine
// transitions.
void pm_process_state_machine(void);

// PMIC callback function called when PMIC measurement acquisition is ready.
void pm_pmic_data_ready(void* context, pmic_report_t* report);

// Power manager charging controller function called periodically from
// pm_monitor_power_sources() to control the charging current and state.
void pm_charging_controller(pm_driver_t* drv);

// True when the battery thermistor reads as a fault. A board without an NTC
// never reports one (see pmic_report_t::ntc_present).
static inline bool pm_ntc_fault(const pm_driver_t* drv) {
  return drv->pmic_data.ntc_present && drv->pmic_data.ntc_disconnected;
}

// Store power manager data to backup RAM
pm_status_t pm_store_data_to_backup_ram(void);

#ifdef USE_RTC
// Schedule the RTC wakeup when going into suspend mode.
// Return false if the driver was not initialized or the RTC timestamp is
// not available.
bool pm_schedule_rtc_wakeup(void);
#endif
