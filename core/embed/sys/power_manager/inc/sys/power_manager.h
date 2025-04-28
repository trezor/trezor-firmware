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

#define POWER_MANAGER_STARTUP_PRESS_MS 1000

/* Power manager states */
#define POWER_MANAGER_STATE_LIST(STATE) \
  STATE(HIBERNATE)                      \
  STATE(CHARGING)                       \
  STATE(REPORT_LOW_BATTERY)             \
  STATE(SUSPEND)                        \
  STATE(ULTRA_POWER_SAVE)               \
  STATE(SHUTTING_DOWN)                  \
  STATE(POWER_SAVE)                     \
  STATE(ACTIVE)

typedef enum {
#define STATE(name) POWER_MANAGER_STATE_##name,
  POWER_MANAGER_STATE_LIST(STATE)
#undef STATE
      POWER_MANAGER_STATE_COUNT
} power_manager_state_t;

/* API return status codes */
typedef enum {
  POWER_MANAGER_OK = 0,
  POWER_MANAGER_NOT_INITIALIZED,
  POWER_MANAGER_REQUEST_REJECTED,
  POWER_MANAGER_ERROR
} power_manager_status_t;

/* Power system events */
typedef enum {
  POWER_MANAGER_EVENT_NONE = 0,
  POWER_MANAGER_EVENT_STATE_CHANGED = 1,
  POWER_MANAGER_EVENT_USB_CONNECTED = 1 << 1,
  POWER_MANAGER_EVENT_USB_DISCONNECTED = 1 << 2,
  POWER_MANAGER_EVENT_WIRELESS_CONNECTED = 1 << 3,
  POWER_MANAGER_EVENT_WIRELESS_DISCONNECTED = 1 << 4,
  POWER_MANAGER_EVENT_BATTERY_LOW = 1 << 5,
  POWER_MANAGER_EVENT_BATTERY_CRITICAL = 1 << 6,
  POWER_MANAGER_EVENT_ERROR = 1 << 7
} power_manager_event_t;

/* Power system report */
typedef struct {
  bool usb_connected;
  bool wireless_charger_connected;
  float system_voltage_v;
  float battery_voltage_v;
  float battery_current_ma;
  float battery_temp_c;
  float pmic_temp_c;
  float wireless_rectifier_voltage_v;
  float wireless_output_voltage_v;
  float wireless_current_ma;
  float wireless_temp_c;
} power_manager_report_t;

/* Public API functions */
power_manager_status_t power_manager_init(power_manager_state_t initial_state);
void power_manager_deinit(void);
power_manager_status_t power_manager_get_events(power_manager_event_t* event);
power_manager_status_t power_manager_get_state(power_manager_state_t* state);
const char* power_manager_get_state_name(power_manager_state_t state);
power_manager_status_t power_manager_suspend(void);
power_manager_status_t power_manager_hibernate(void);
power_manager_status_t power_manager_turn_on(void);
power_manager_status_t power_manager_get_report(power_manager_report_t* report);
power_manager_status_t power_manager_charging_enable(void);
power_manager_status_t power_manager_charging_disable(void);