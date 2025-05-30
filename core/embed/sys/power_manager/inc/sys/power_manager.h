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

/* Power manager wakeup flags */
typedef enum {
  PM_WAKEUP_FLAG_BUTTON = 0x1 << 0,  // Button pressed
  PM_WAKEUP_FLAG_WPC = 0x1 << 1,     // Wireless power charging event
  PM_WAKEUP_FLAG_BLE = 0x1 << 2,     // Bluetooth connection event
  PM_WAKEUP_FLAG_NFC = 0x1 << 3,     // NFC event
  PM_WAKEUP_FLAG_USB = 0x1 << 4,     // USB event
  PM_WAKEUP_FLAG_TIMER = 0x1 << 5,   // Timer event
} pm_wakeup_flags_t;

/* power manager status codes */
typedef enum {
  PM_OK = 0,
  PM_NOT_INITIALIZED,
  PM_REQUEST_REJECTED,
  PM_ERROR,
} pm_status_t;

/* Power manager charging status */
typedef enum {
  PM_BATTERY_IDLE = 0,
  PM_BATTERY_DISCHARGING,
  PM_BATTERY_CHARGING,
} pm_charging_status_t;

/* Power manager internal states */
typedef enum {
  PM_STATE_HIBERNATE,
  PM_STATE_CHARGING,
  PM_STATE_SUSPEND,
  PM_STATE_SHUTTING_DOWN,
  PM_STATE_POWER_SAVE,
  PM_STATE_ACTIVE,
} pm_power_status_t;

/* Power manager events */
typedef union {
  uint32_t all;
  struct {
    bool power_status_changed : 1;
    bool charging_status_changed : 1;
    bool usb_connected_changed : 1;
    bool wireless_connected_changed : 1;

    bool soc_updated : 1;
  } flags;
} pm_event_t;

/* Power manager state */
typedef struct {
  bool usb_connected;
  bool wireless_connected;
  pm_charging_status_t charging_status;
  pm_power_status_t power_status;
  uint8_t soc;
} pm_state_t;

/* Power system report */
typedef struct {
  pm_power_status_t power_state;
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

/**
 * @brief Initialize the power manager
 * @param inherit_state Whether to inherit previous power state from backup
 * memory
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_init(bool inherit_state);

/**
 * Deinitialize the power manager
 */
void pm_deinit(void);

/**
 * @brief Read power manager pending events. Events are cleared after reading.
 * @param event_flags Pointer to store the event flags
 * @return bool True if any events were pending
 */
bool pm_get_events(pm_event_t* event_flags);

/**
 * @brief Get the current power management state
 * @param state Pointer to store the power state information
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_get_state(pm_state_t* state);

/**
 * @brief Request device to enter suspend mode
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_suspend(void);

/**
 * @brief Request device to enter hibernation mode
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_hibernate(void);

/**
 * @brief Request the device to turn on and transition from CHARGING/HIBERNATE
 *        to higher power state.
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_turn_on(void);

/**
 * @brief Get power manager report
 * @param report Pointer to store power manager report
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_get_report(pm_report_t* report);

/**
 * @brief Enable battery charging
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_charging_enable(void);

/**
 * @brief Disable battery charging
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_charging_disable(void);

/**
 * @brief Set maximum charging current
 * @param current_ma Maximum charging current in mA
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_charging_set_max_current(uint16_t current_ma);

/**
 * @brief Set the battery State of Charge limit for operations
 * @param limit SoC limit percentage (0-100%)
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_set_soc_limit(uint8_t limit);

/**
 * @brief Store power manager data to backup RAM
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_store_data_to_backup_ram();

/**
 * @brief Set wakeup flags
 * @param flags Wakeup flags to set
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_wakeup_flags_set(pm_wakeup_flags_t flags);

/**
 * @brief Reset wakeup flags
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_wakeup_flags_reset(void);

/**
 * @brief Get wakeup flags
 * @param flags Pointer to store the current wakeup flags
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_wakeup_flags_get(pm_wakeup_flags_t* flags);
