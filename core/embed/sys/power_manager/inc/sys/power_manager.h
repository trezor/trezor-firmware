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

#define POWER_MANAGER_STATE_LIST(STATE) \
  STATE(ACTIVE)                         \
  STATE(POWER_SAVE)                     \
  STATE(ULTRA_POWER_SAVE)               \
  STATE(SHUTTING_DOWN)                  \
  STATE(SUSPEND)                        \
  STATE(CHARGING)                       \
  STATE(HIBERNATE)

typedef enum {
#define STATE(name) POWER_MANAGER_STATE_##name,
  POWER_MANAGER_STATE_LIST(STATE)
#undef STATE
      POWER_MANAGER_STATE_COUNT
} power_manager_state_t;

typedef enum {
  POWER_MANAGER_OK = 0,
  POWER_MANAGER_NOT_INITIALIZED,
  POWER_MANAGER_REQUEST_REJECTED,
} power_manager_status_t;

typedef struct {
  bool usb_connected;
  bool wlc_connected;
  float vsys_voltage_V;
  float battery_voltage_V;
  float battery_current_mA;
  float battery_temp_deg;
  float pmic_die_temp_deg;
  float wlc_vrect_V;
  float wlc_vout_V;
  float wlc_current_mA;
  float wlc_die_temp_deg;
} power_manager_report_t;

// typedef enum {
//   POWER_MANAGER_STATE_ACTIVE,
//   POWER_MANAGER_STATE_POWER_SAVE,
//   POWER_MANAGER_STATE_ULTRA_POWER_SAVE,
//   POWER_MANAGER_STATE_SHUTTING_DOWN,
//   POWER_MANAGER_STATE_SUSPEND,
//   POWER_MANAGER_STATE_CHARGING,
//   POWER_MANAGER_STATE_HIBERNATE,
// } power_manager_state_t;

typedef enum {
  POWER_MANAGER_EVENT_NONE = 0,
  POWER_MANAGER_STATE_CHANGED = 1,
  POWER_MANAGER_USB_CONNECTED = 1 << 1,
  POWER_MANAGER_USB_DISCONNECTED = 1 << 2,
  POWER_MANAGER_WLC_CONNECTED = 1 << 3,
  POWER_MANAGER_WLC_DISCONNECTED = 1 << 4,
  POWER_MANAGER_ERROR = 1 << 5,
} power_manager_event_t;

power_manager_status_t power_manager_init(void);

void power_manager_deinit(void);

power_manager_status_t power_manager_get_events(power_manager_event_t* event);

power_manager_status_t power_manager_get_state(power_manager_state_t* state);

power_manager_status_t power_manager_suspend(void);

power_manager_status_t power_manager_hibernate(void);

power_manager_status_t power_manager_get_report(power_manager_report_t* report);

const char* power_manager_get_state_name(power_manager_state_t state);
