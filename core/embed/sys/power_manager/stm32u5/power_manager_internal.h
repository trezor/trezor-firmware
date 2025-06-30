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

#define PM_SELF_DISG_RATE_HIBERNATION_MA 0.004f
#define PM_SELF_DISG_RATE_SUSPEND_MA 0.032f

// Fuel gauge extended kalman filter parameters
#define PM_FUEL_GAUGE_R 2000.0f
#define PM_FUEL_GAUGE_Q 0.001f
#define PM_FUEL_GAUGE_R_AGGRESSIVE 1000.0f
#define PM_FUEL_GAUGE_Q_AGGRESSIVE 0.001f
#define PM_FUEL_GAUGE_P_INIT 0.1f

// Timeout after which the device automatically transit from suspend to
// hibernation
#define PM_AUTO_HIBERNATE_TIMEOUT_S (24 * 60 * 60)  // 24 hours

#define PM_SUSPENDED_CHARGING_TIMEOUT_S 60
#define PM_STABILIZATION_TIMEOUT_MS 2000

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

  // Set if the driver was requested to suspend background operations.
  // IF so, the driver waits until the last operation is finished,
  // then enters suspended mode.
  bool suspending;

  // Set if the driver's background operations are suspended.
  bool suspended;

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
  bool woke_up_from_suspend;
  bool suspended_charging;

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

  // Timers and timestamps
  systimer_t* monitoring_timer;
  systimer_t* shutdown_timer;
  uint32_t suspend_timestamp;
  uint32_t last_active_timestamp;
  uint32_t time_in_suspend_s;

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

// Battery initial state of charge guess function. This function uses the
// sampled battery data to guess the initial state of charge in case its
// unknown.
void pm_battery_initial_soc_guess(void);

// Store power manager data to backup RAM
pm_status_t pm_store_data_to_backup_ram(void);

// Direct coulomb counter compensation of the SoC based on the battery current,
// temp and elapsed time, this function is used to compensate the fuel gauge
// estimation during the periods where the EKF could not be used, such as
// suspend or hibernation.
void pm_compensate_fuel_gauge(float* soc, uint32_t elapsed_s,
                              float battery_current_mah, float bat_temp_c);

// Schedule the RTC wakeup when going into suspend mode.
// Return false if the driver was not initialized or the RTC timestamp is
// not available.
bool pm_schedule_rtc_wakeup(void);
