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

#include "../../powerctl/npm1300/npm1300.h"
#include "../../powerctl/stwlc38/stwlc38.h"

// Power manager thresholds & timings
#define POWER_MANAGER_TIMER_PERIOD_MS 300
#define POWER_MANAGER_SHUTDOWN_TIMEOUT_MS 15000
#define POWER_MANAGER_BATTERY_UNDERVOLT_THRESHOLD_V 3.0f
#define POWER_MANAGER_BATTERY_UNDERVOLT_HYSTERESIS_V 0.5f
#define POWER_MANAGER_BATTERY_LOW_THRESHOLD_V 3.15f
#define POWER_MANAGER_BATTERY_LOW_RECOVERY_V 3.2f
#define POWER_MANAGER_WPC_CHARGE_CURR_STEP_MA 50
#define POWER_MANAGER_WPC_CHARGE_CURR_STEP_TIMEOUT_MS 1000

// Event flag manipulation macros
#define PM_SET_EVENT(flags, event) ((flags) |= (event))
#define PM_CLEAR_EVENT(flags, event) ((flags) &= ~(event))
#define PM_CLEAR_ALL_EVENTS(flags) ((flags) = 0)

// Power manager core driver structure
typedef struct {
  bool initialized;
  power_manager_state_t state;
  power_manager_event_t event_flags;

  // Battery charging state
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
} power_manager_driver_t;

// State handler function definition
typedef struct {
  void (*enter)(power_manager_driver_t* drv);
  power_manager_state_t (*handle)(power_manager_driver_t* drv);
  void (*exit)(power_manager_driver_t* drv);
} power_manager_state_handler_t;

// Shared global driver instance
extern power_manager_driver_t g_power_manager;

// Internal function declarations
void pm_monitor_power_sources(void);
void pm_process_state_machine(void);
void pm_pmic_data_ready(void* context, npm1300_report_t* report);
void pm_charging_controller(power_manager_driver_t* drv);

// State handlers
power_manager_state_t pm_handle_state_active(power_manager_driver_t* drv);
power_manager_state_t pm_handle_state_power_save(power_manager_driver_t* drv);
power_manager_state_t pm_handle_state_ultra_power_save(
    power_manager_driver_t* drv);
power_manager_state_t pm_handle_state_shutting_down(
    power_manager_driver_t* drv);
power_manager_state_t pm_handle_state_suspend(power_manager_driver_t* drv);
power_manager_state_t pm_handle_state_report_low_battery(
    power_manager_driver_t* drv);
power_manager_state_t pm_handle_state_charging(power_manager_driver_t* drv);
power_manager_state_t pm_handle_state_hibernate(power_manager_driver_t* drv);

void pm_enter_active(power_manager_driver_t* drv);
void pm_enter_power_save(power_manager_driver_t* drv);
void pm_enter_shutting_down(power_manager_driver_t* drv);
void pm_exit_shutting_down(power_manager_driver_t* drv);
void pm_enter_suspend(power_manager_driver_t* drv);
void pm_enter_report_low_battery(power_manager_driver_t* drv);
void pm_enter_charging(power_manager_driver_t* drv);
void pm_exit_charging(power_manager_driver_t* drv);
void pm_enter_hibernate(power_manager_driver_t* drv);
