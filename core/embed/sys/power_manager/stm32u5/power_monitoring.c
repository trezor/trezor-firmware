
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

#include <sys/backup_ram.h>
#include <sys/systick.h>
#include <trezor_rtl.h>

#include "../../powerctl/fuel_gauge/fuel_gauge.h"
#include "../../powerctl/npm1300/npm1300.h"
#include "../../powerctl/stwlc38/stwlc38.h"
#include "power_manager_internal.h"

void pm_monitor_power_sources(void) {
  pm_driver_t* drv = &g_pm;

  // Check if PMIC data is ready, otherwise skip processing
  if (!drv->pmic_measurement_ready) {
    return;
  }

  // Update fuel gauge state
  if (drv->fuel_gauge_initialized) {
    if (drv->fuel_gauge_request_new_guess) {
      // Request new single SoC guess based on the latest measurements
      fuel_gauge_initial_guess(&drv->fuel_gauge, drv->pmic_data.vbat,
                               drv->pmic_data.ibat, drv->pmic_data.ntc_temp);

      drv->fuel_gauge_request_new_guess = false;

    } else {
      fuel_gauge_update(&drv->fuel_gauge, PM_BATTERY_SAMPLING_PERIOD_MS,
                        drv->pmic_data.vbat, drv->pmic_data.ibat,
                        drv->pmic_data.ntc_temp);

      // Ceil the float soc to user friendly integer
      uint8_t soc_ceiled_temp =
          (int)(drv->fuel_gauge.soc_latched * 100 + 0.999f);
      if (soc_ceiled_temp != drv->soc_ceiled) {
        drv->soc_ceiled = soc_ceiled_temp;
        PM_SET_EVENT(drv->event_flags, PM_EVENT_SOC_UPDATED);
      }
    }

  } else {
    pm_battery_sampling(drv->pmic_data.vbat, drv->pmic_data.ibat,
                        drv->pmic_data.ntc_temp);

    // Battery sampling period, collect data before initial guess is made.
    fuel_gauge_initial_guess(&drv->fuel_gauge, drv->pmic_data.vbat,
                             drv->pmic_data.ibat, drv->pmic_data.ntc_temp);
  }

  // Check USB power source status
  if (drv->pmic_data.usb_status != 0x0) {
    if (!drv->usb_connected) {
      drv->usb_connected = true;
      PM_SET_EVENT(drv->event_flags, PM_EVENT_USB_CONNECTED);
    }
  } else {
    if (drv->usb_connected) {
      drv->usb_connected = false;
      PM_SET_EVENT(drv->event_flags, PM_EVENT_USB_DISCONNECTED);
    }
  }

  // Check wireless charger status
  if (drv->wireless_data.vout_ready) {
    if (!drv->wireless_connected) {
      drv->wireless_connected = true;
      PM_SET_EVENT(drv->event_flags, PM_EVENT_WIRELESS_CONNECTED);
    }
  } else {
    if (drv->wireless_connected) {
      drv->wireless_connected = false;
      PM_SET_EVENT(drv->event_flags, PM_EVENT_WIRELESS_DISCONNECTED);
    }
  }

  // Check battery voltage for critical (undervoltage) threshold
  if ((drv->pmic_data.vbat < PM_BATTERY_UNDERVOLT_THRESHOLD_V) &&
      !drv->battery_critical) {
    drv->battery_critical = true;
  } else if (drv->pmic_data.vbat > (PM_BATTERY_UNDERVOLT_THRESHOLD_V +
                                    PM_BATTERY_UNDERVOLT_HYSTERESIS_V) &&
             drv->battery_critical) {
    drv->battery_critical = false;
  }

  // Check battery voltage for low threshold
  if (drv->pmic_data.vbat < PM_BATTERY_LOW_THRESHOLD_V && !drv->battery_low) {
    drv->battery_low = true;
  } else if (drv->pmic_data.vbat > PM_BATTERY_LOW_RECOVERY_V &&
             drv->battery_low) {
    drv->battery_low = false;
  }

  // Run battery charging controller
  pm_charging_controller(drv);

  // Process state machine with updated battery and power source information
  pm_process_state_machine();

  // Request fresh measurements
  npm1300_measure(pm_pmic_data_ready, NULL);
  drv->pmic_measurement_ready = false;
}

// PMIC measurement callback
void pm_pmic_data_ready(void* context, npm1300_report_t* report) {
  pm_driver_t* drv = &g_pm;

  // Store measurement timestamp
  drv->pmic_last_update_ms = systick_ms();

  // Copy PMIC data
  memcpy(&drv->pmic_data, report, sizeof(npm1300_report_t));

  // Get wireless charger data
  stwlc38_get_report(&drv->wireless_data);

  drv->pmic_measurement_ready = true;
}

void pm_charging_controller(pm_driver_t* drv) {
  if (drv->charging_enabled == false) {
    // Charging is disabled
    if (drv->charging_current_target_ma != 0) {
      drv->charging_current_target_ma = 0;
      drv->charging_target_timestamp = systick_ms();
    } else {
      // No action required
      return;
    }
  } else if (drv->usb_connected) {
    // USB connected, set maximum charging current right away
    drv->charging_current_target_ma = NPM1300_CHARGING_LIMIT_MAX;

  } else if (drv->wireless_connected) {
    // Gradually increase charging current to the maximum
    if (drv->charging_current_target_ma == NPM1300_CHARGING_LIMIT_MAX) {
      // No action required
    } else if (drv->charging_current_target_ma == 0) {
      drv->charging_current_target_ma = NPM1300_CHARGING_LIMIT_MIN;
      drv->charging_target_timestamp = systick_ms();
    } else if (systick_ms() - drv->charging_target_timestamp >
               PM_WPC_CHARGE_CURR_STEP_TIMEOUT_MS) {
      drv->charging_current_target_ma += PM_WPC_CHARGE_CURR_STEP_MA;
      drv->charging_target_timestamp = systick_ms();

      if (drv->charging_current_target_ma > NPM1300_CHARGING_LIMIT_MAX) {
        drv->charging_current_target_ma = NPM1300_CHARGING_LIMIT_MAX;
      }
    }

  } else {
    // Charging enabled but no external power source, clear charging target
    drv->charging_current_target_ma = 0;
  }

  // Set charging target
  if (drv->charging_current_target_ma != npm1300_get_charging_limit()) {
    // Set charging current limit
    npm1300_set_charging_limit(drv->charging_current_target_ma);
  }

  if (drv->charging_current_target_ma == 0) {
    npm1300_set_charging(false);
  } else {
    npm1300_set_charging(true);
  }
}

void pm_battery_sampling(float vbat, float ibat, float ntc_temp) {
  pm_driver_t* drv = &g_pm;

  // Store battery data in the buffer
  drv->bat_sampling_buf[drv->bat_sampling_buf_head_idx].vbat = vbat;
  drv->bat_sampling_buf[drv->bat_sampling_buf_head_idx].ibat = ibat;
  drv->bat_sampling_buf[drv->bat_sampling_buf_head_idx].ntc_temp = ntc_temp;

  // Update head index
  drv->bat_sampling_buf_head_idx++;
  if (drv->bat_sampling_buf_head_idx >= PM_BATTERY_SAMPLING_BUF_SIZE) {
    drv->bat_sampling_buf_head_idx = 0;
  }

  // Check if the buffer is full
  if (drv->bat_sampling_buf_head_idx == drv->bat_sampling_buf_tail_idx) {
    // Buffer is full, move tail index forward
    drv->bat_sampling_buf_tail_idx++;
    if (drv->bat_sampling_buf_tail_idx >= PM_BATTERY_SAMPLING_BUF_SIZE) {
      drv->bat_sampling_buf_tail_idx = 0;
    }
  }
}

void pm_battery_initial_soc_guess(void) {
  pm_driver_t* drv = &g_pm;

  // Check if the buffer is full
  if (drv->bat_sampling_buf_head_idx == drv->bat_sampling_buf_tail_idx) {
    // Buffer is empty, no data to process
    return;
  }

  // Calculate average voltage, current and temperature from the sampling
  // buffer and run the fuel gauge initial guess
  uint8_t buf_idx = drv->bat_sampling_buf_tail_idx;
  uint8_t samples_count = 0;
  float vbat_g = 0.0f;
  float ibat_g = 0.0f;
  float ntc_temp_g = 0.0f;
  while (drv->bat_sampling_buf_head_idx != buf_idx) {
    vbat_g += drv->bat_sampling_buf[buf_idx].vbat;
    ibat_g += drv->bat_sampling_buf[buf_idx].ibat;
    ntc_temp_g += drv->bat_sampling_buf[buf_idx].ntc_temp;

    buf_idx++;
    if (buf_idx >= PM_BATTERY_SAMPLING_BUF_SIZE) {
      buf_idx = 0;
    }

    samples_count++;
  }

  // Calculate average values
  vbat_g /= samples_count;
  ibat_g /= samples_count;
  ntc_temp_g /= samples_count;

  fuel_gauge_initial_guess(&drv->fuel_gauge, vbat_g, ibat_g, ntc_temp_g);
}

void pm_store_power_manager_data(pm_driver_t* drv) {
  backup_ram_power_manager_data_t pm_data = {0};

  // Store the current state of the power manager
  pm_data.soc = drv->fuel_gauge.soc;
  pm_data.last_capture_timestamp = systick_ms();

  // Store the data in backup RAM
  backup_ram_store_power_manager_data(&pm_data);
}
