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

#include <io/suspend.h>

/* power manager status codes */
typedef enum {
  PM_OK = 0,
  PM_NOT_INITIALIZED,
  PM_REQUEST_REJECTED,
  PM_TIMEOUT,
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

// Current version of the power management recovery data structure
#define PM_RECOVERY_DATA_VERSION 0x0001

/**
 * @brief Structure for power management data stored in backup RAM
 *
 * This structure contains critical power management information that needs to
 * persist across power cycles and resets. It stores battery state of charge
 * (SOC), timing information, and system state data required for proper power
 * management.
 *
 * If the structure is changed, the version must be incremented and
 * proper migration logic must be implemented.
 */
typedef struct {
  /** Data version */
  uint16_t version;
  /** Fuel gauge state of charge <0, 1> */
  float soc;
  /** Fuel gauge covariance */
  float P;
  bool bat_critical;
  /** RTC time at which SOC was captured */
  uint32_t last_capture_timestamp;
  /** Power manager state at bootloader exit so it could be correctly
  restored in the firwmare. */
  uint32_t bootloader_exit_state;
} pm_recovery_data_t;

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
 * @param wakeup_reason Pointer to store wakeup flags (reason for wakeup).
 * Can be NULL if not needed.
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_suspend(wakeup_flags_t* wakeup_reason);

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
 * @brief Set the battery State of Charge precharge target.
 *
 * Charging controller will continously compare taget SoC charging voltage from
 * battery model (temperature dependant) with the actual battery voltage and if
 * the battery voltage is above the target, charging is stopped. If the battery
 * voltage also cross the charging voltage target, Fuel gauge SoC estimate is
 * enforced with the target value.
 *
 * Setting value to `100` disables the precharge target and charging cycle will
 * be driven with PMIC driver.
 *
 * @param target SoC target percentage (0-100%)
 * @return pm_status_t Status code indicating success or failure
 */
pm_status_t pm_set_soc_target(uint8_t target);

/**
 * @brief Check if the device is currently charging the battery
 *
 * @return true if the device is charging, false otherwise
 */
bool pm_is_charging(void);

/**
 * @brief Check if the USB is connected
 *
 * @return true if USB is connected, false otherwise
 */
bool pm_usb_is_connected(void);

/**
 * @brief Suspends driver activity so the CPU can enter low-power mode.
 *
 * Suspending may take some time if the driver is currently
 * performing an operation. Caller may check the status by
 * pm_is_suspended().
 *
 * @return true if the power manager was successfully suspended, false otherwise
 */
bool pm_driver_suspend(void);

/**
 * @brief Resume the power manager after it has been suspended
 *
 * @return true if the power manager was successfully resumed, false otherwise
 *  */
bool pm_driver_resume(void);

/**
 * @brief Check if the power manager is suspended
 *
 * @return true if the power manager is suspended, false otherwise
 */
bool pm_driver_is_suspended(void);
