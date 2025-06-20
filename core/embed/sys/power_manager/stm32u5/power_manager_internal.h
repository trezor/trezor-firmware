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

#include <sys/pmic.h>
#include <sys/power_manager.h>
#include <sys/systimer.h>
#include <trezor_types.h>

#include "../fuel_gauge/fuel_gauge.h"
#include "../stwlc38/stwlc38.h"

// Power manager thresholds & timings
#define PM_TIMER_PERIOD_MS 300
#define PM_BATTERY_SAMPLING_PERIOD_MS 100
#define PM_SHUTDOWN_TIMEOUT_MS 15000
#define PM_BATTERY_UNDERVOLT_THR_V 3.0f
#define PM_BATTERY_UNDERVOLT_RECOVERY_THR_V 3.1f
#define PM_BATTERY_UNDERVOLT_RECOVERY_WPC_THR_V 3.2f
#define PM_BATTERY_LOW_THRESHOLD_SOC 15
#define PM_SOC_LIMIT_HYSTERESIS 5
#define PM_BATTERY_CHARGING_CURRENT_MAX PMIC_CHARGING_LIMIT_MAX
#define PM_BATTERY_CHARGING_CURRENT_MIN PMIC_CHARGING_LIMIT_MIN
#define PM_BATTERY_SAMPLING_BUF_SIZE 10

// Fuel gauge extended kalman filter parameters
#define PM_FUEL_GAUGE_R 2000.0f
#define PM_FUEL_GAUGE_Q 0.001f
#define PM_FUEL_GAUGE_R_AGGRESSIVE 1000.0f
#define PM_FUEL_GAUGE_Q_AGGRESSIVE 0.001f
#define PM_FUEL_GAUGE_P_INIT 0.1f

// Power manager battery sampling data structure
typedef struct {
  float vbat;      // Battery voltage [V]
  float ibat;      // Battery current [mA]
  float ntc_temp;  // NTC temperature [°C]
} pm_sampling_data_t;

// Power manager core driver structure
typedef struct {
  bool initialized;
  bool state_machine_stabilized;
  pm_power_status_t state;

  // Fuel gauge
  fuel_gauge_state_t fuel_gauge;
  bool fuel_gauge_initialized;
  pm_sampling_data_t bat_sampling_buf[PM_BATTERY_SAMPLING_BUF_SIZE];
  uint8_t bat_sampling_buf_tail_idx;
  uint8_t bat_sampling_buf_head_idx;
  uint8_t soc_ceiled;
  uint8_t soc_limit;
  bool soc_limit_reached;

  // Battery charging state
  bool charging_enabled;
  uint16_t charging_current_target_ma;
  uint16_t charging_current_max_limit_ma;

  // Power source hardware state
  pmic_report_t pmic_data;
  stwlc38_report_t wireless_data;
  uint32_t pmic_last_update_ms;
  uint32_t pmic_sampling_period_ms;
  bool pmic_measurement_ready;

  // Power source logical state
  bool usb_connected;
  bool wireless_connected;
  bool battery_low;
  bool battery_critical;

  // Power mode request flags
  bool request_suspend;
  bool request_exit_suspend;
  bool request_hibernate;
  bool request_turn_on;
  bool shutdown_timer_elapsed;

  // Timers
  systimer_t* monitoring_timer;
  systimer_t* shutdown_timer;

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

// Battery initial state of charge guess function. This function use the sampled
// battery data to guess the initial state of charge in case its unknown.
void pm_battery_initial_soc_guess(void);
