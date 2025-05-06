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

typedef enum {
  PM_WAKEUP_FLAG_BUTTON = 0x1 << 0,  // Button pressed
  PM_WAKEUP_FLAG_WPC    = 0x1 << 1,  // Wireless power charging event
  PM_WAKEUP_FLAG_BLE    = 0x1 << 2,  // Bluetooth connection event
  PM_WAKEUP_FLAG_NFC    = 0x1 << 3,  // NFC event
  PM_WAKEUP_FLAG_USB    = 0x1 << 4,  // USB event
  PM_WAKEUP_FLAG_TIMER  = 0x1 << 5,  // Timer event
} pm_wakeup_flags_t;

/* API return status codes */
typedef enum {
  PM_OK = 0,
  PM_NOT_INITIALIZED,
  PM_REQUEST_REJECTED,
  PM_ERROR,
} pm_status_t;

typedef enum {
  PM_BATTERY_IDLE = 0,
  PM_BATTERY_DISCHARGING,
  PM_BATTERY_CHARGING,
} pm_charging_status_t;

typedef enum {
  PM_POWER_MODE_ACTIVE,
  PM_POWER_MODE_POWER_SAVE,
  PM_POWER_MODE_SHUTTING_DOWN,
  PM_POWER_MODE_NOT_INITIALIZED,
} pm_power_mode_t;

/* Power system events */
typedef enum {
  PM_EVENT_NONE = 0,
  PM_EVENT_STATE_CHANGED = 1,
  PM_EVENT_USB_CONNECTED = 1 << 1,
  PM_EVENT_USB_DISCONNECTED = 1 << 2,
  PM_EVENT_WIRELESS_CONNECTED = 1 << 3,
  PM_EVENT_WIRELESS_DISCONNECTED = 1 << 4,
  PM_EVENT_ENTERED_MODE_ACTIVE = 1 << 5,
  PM_EVENT_ENTERED_MODE_POWER_SAVE = 1 << 6,
  PM_EVENT_ENTERED_MODE_SHUTTING_DOWN = 1 << 7,
  PM_EVENT_SOC_UPDATED = 1 << 8,
} pm_event_t;

typedef struct {
  bool usb_connected;
  bool wireless_connected;
  pm_charging_status_t charging_status;
  pm_power_mode_t power_mode;
  uint8_t soc;
} pm_state_t;

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
pm_status_t pm_init(bool inherit_state);
void pm_deinit(void);
pm_status_t pm_get_events(pm_event_t* event_flags);
pm_status_t pm_get_state(pm_state_t* state);
pm_status_t pm_suspend(void);
pm_status_t pm_hibernate(void);
pm_status_t pm_turn_on(void);
pm_status_t pm_get_report(pm_report_t* report);
pm_status_t pm_charging_enable(void);
pm_status_t pm_charging_disable(void);
pm_status_t pm_store_data_to_backup_ram(void);
pm_status_t pm_wait_until_active(uint32_t timeout_ms);
pm_status_t pm_wakeup_flags_set(pm_wakeup_flags_t flags);
pm_status_t pm_wakeup_flags_reset(void);
pm_status_t pm_wakeup_flags_get(pm_wakeup_flags_t* flags);

