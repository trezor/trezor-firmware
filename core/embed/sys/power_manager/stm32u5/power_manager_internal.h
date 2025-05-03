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

#include <sys/power_manager.h>
#include <sys/systimer.h>
#include <trezor_types.h>

#include "../fuel_gauge/fuel_gauge.h"
#include "../npm1300/npm1300.h"
#include "../stwlc38/stwlc38.h"

// Power manager thresholds & timings
#define PM_TIMER_PERIOD_MS 300
#define PM_BATTERY_SAMPLING_PERIOD_MS 100
#define PM_SHUTDOWN_TIMEOUT_MS 15000
#define PM_BATTERY_UNDERVOLT_THRESHOLD_V 3.0f
#define PM_BATTERY_UNDERVOLT_HYSTERESIS_V 0.5f
#define PM_BATTERY_LOW_THRESHOLD_V 3.15f
#define PM_BATTERY_LOW_RECOVERY_V 3.2f
#define PM_BATTERY_SAMPLING_BUF_SIZE 10

#define PM_WPC_CHARGE_CURR_STEP_MA 50
#define PM_WPC_CHARGE_CURR_STEP_TIMEOUT_MS 1000
#define PM_FUEL_GAUGE_R 3000.0f
#define PM_FUEL_GAUGE_Q 0.001f
#define PM_FUEL_GAUGE_R_AGGRESSIVE 3000.0f
#define PM_FUEL_GAUGE_Q_AGGRESSIVE 0.001f
#define PM_FUEL_GAUGE_P_INIT 0.1f

/* Power manager states */
#define PM_STATE_LIST(STATE) \
  STATE(HIBERNATE)           \
  STATE(CHARGING)            \
  STATE(STARTUP_REJECTED)    \
  STATE(SUSPEND)             \
  STATE(ULTRA_POWER_SAVE)    \
  STATE(SHUTTING_DOWN)       \
  STATE(POWER_SAVE)          \
  STATE(ACTIVE)

typedef enum {
#define STATE(name) PM_STATE_##name,
  PM_STATE_LIST(STATE)
#undef STATE
      PM_STATE_COUNT
} pm_internal_state_t;

// Power manager battery sampling data structure)
typedef struct {
  float vbat;      // Battery voltage [V]
  float ibat;      // Battery current [mA]
  float ntc_temp;  // NTC temperature [°C]
} pm_sampling_data_t;

// Power manager core driver structure
typedef struct {
  bool initialized;
  pm_internal_state_t state;

  // Fuel gauge
  fuel_gauge_state_t fuel_gauge;
  bool fuel_gauge_initialized;
  bool fuel_gauge_request_new_guess;
  pm_sampling_data_t bat_sampling_buf[PM_BATTERY_SAMPLING_BUF_SIZE];
  uint8_t bat_sampling_buf_tail_idx;
  uint8_t bat_sampling_buf_head_idx;
  uint8_t soc_ceiled;

  // Battery charging state
  bool charging_enabled;
  uint16_t charging_current_target_ma;
  uint32_t charging_target_timestamp;

  // Power source hardware state
  npm1300_report_t pmic_data;
  stwlc38_report_t wireless_data;
  uint32_t pmic_last_update_ms;
  bool pmic_measurement_ready;

  // Power source logical state
  bool usb_connected;
  bool wireless_connected;
  bool battery_low;
  bool battery_critical;

  // Power mode request flags
  bool request_suspend;
  bool request_hibernate;
  bool request_turn_on;
  bool shutdown_timer_elapsed;

  // Timers
  systimer_t* monitoring_timer;
  systimer_t* shutdown_timer;

  // Wakeup flags
  volatile pm_wakeup_flags_t wakeup_flags;

} pm_driver_t;

// State handler function definition
typedef struct {
  void (*enter)(pm_driver_t* drv);
  pm_internal_state_t (*handle)(pm_driver_t* drv);
  void (*exit)(pm_driver_t* drv);
} pm_state_handler_t;

// Shared global driver instance
extern pm_driver_t g_pm;

// Internal function declarations
void pm_monitor_power_sources(void);
void pm_process_state_machine(void);
void pm_pmic_data_ready(void* context, npm1300_report_t* report);
void pm_charging_controller(pm_driver_t* drv);
void pm_battery_sampling(float vbat, float ibat, float ntc_temp);
void pm_battery_initial_soc_guess(void);
void pm_store_power_manager_data(pm_driver_t* drv);
pm_status_t pm_control_hibernate(void);
void pm_control_suspend(void);
void pm_control_suspend(void);

// State handlers
pm_internal_state_t pm_handle_state_active(pm_driver_t* drv);
pm_internal_state_t pm_handle_state_power_save(pm_driver_t* drv);
pm_internal_state_t pm_handle_state_ultra_power_save(pm_driver_t* drv);
pm_internal_state_t pm_handle_state_shutting_down(pm_driver_t* drv);
pm_internal_state_t pm_handle_state_suspend(pm_driver_t* drv);
pm_internal_state_t pm_handle_state_startup_rejected(pm_driver_t* drv);
pm_internal_state_t pm_handle_state_charging(pm_driver_t* drv);
pm_internal_state_t pm_handle_state_hibernate(pm_driver_t* drv);

void pm_enter_active(pm_driver_t* drv);
void pm_enter_power_save(pm_driver_t* drv);
void pm_enter_shutting_down(pm_driver_t* drv);
void pm_exit_shutting_down(pm_driver_t* drv);
void pm_enter_suspend(pm_driver_t* drv);
void pm_enter_report_low_battery(pm_driver_t* drv);
void pm_enter_charging(pm_driver_t* drv);
void pm_exit_charging(pm_driver_t* drv);
void pm_enter_hibernate(pm_driver_t* drv);
