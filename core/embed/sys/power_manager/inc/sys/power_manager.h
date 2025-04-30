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
} pm_state_t;

/* API return status codes */
typedef enum {
  PM_OK = 0,
  PM_NOT_INITIALIZED,
  PM_REQUEST_REJECTED,
  PM_ERROR
} pm_status_t;

/* Power system events */
typedef enum {
  PM_EVENT_NONE = 0,
  PM_EVENT_STATE_CHANGED = 1,
  PM_EVENT_USB_CONNECTED = 1 << 1,
  PM_EVENT_USB_DISCONNECTED = 1 << 2,
  PM_EVENT_WIRELESS_CONNECTED = 1 << 3,
  PM_EVENT_WIRELESS_DISCONNECTED = 1 << 4,
  PM_EVENT_BATTERY_LOW = 1 << 5,
  PM_EVENT_BATTERY_CRITICAL = 1 << 6,
  PM_EVENT_ERROR = 1 << 7
} pm_event_t;

/* Power system report */
typedef struct {
  bool usb_connected;
  bool wireless_charger_connected;
  float system_voltage_v;
  float battery_voltage_v;
  float battery_current_ma;
  float battery_temp_c;
  float battery_soc;
  float battery_soc_latched;
  float pmic_temp_c;
  float wireless_rectifier_voltage_v;
  float wireless_output_voltage_v;
  float wireless_current_ma;
  float wireless_temp_c;
} pm_report_t;

/* Public API functions */
pm_status_t pm_init(pm_state_t initial_state);
void pm_deinit(void);
pm_status_t pm_get_events(pm_event_t* event_flag);
pm_status_t pm_get_state(pm_state_t* state);
const char* pm_get_state_name(pm_state_t state);
pm_status_t pm_suspend(void);
pm_status_t pm_hibernate(void);
pm_status_t pm_turn_on(void);
pm_status_t pm_get_report(pm_report_t* report);
pm_status_t pm_charging_enable(void);
pm_status_t pm_charging_disable(void);
