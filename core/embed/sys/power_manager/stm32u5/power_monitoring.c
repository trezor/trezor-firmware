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
#ifdef KERNEL_MODE

#include <sys/backup_ram.h>
#include <sys/irq.h>
#include <sys/notify.h>
#include <sys/pmic.h>
#include <sys/systick.h>
#include <trezor_rtl.h>

#include "../fuel_gauge/battery_model.h"
#include "../fuel_gauge/fuel_gauge.h"
#include "../stwlc38/stwlc38.h"
#include "power_manager_internal.h"

#ifdef PM_ENABLE_TEMP_CONTROL
static void pm_temperature_controller(pm_driver_t* drv);
#endif

static void pm_battery_sampling(float vbat, float ibat, float ntc_temp);
static void pm_parse_power_source_state(pm_driver_t* drv);

#ifdef PM_ENABLE_TEMP_CONTROL

// Temperature controller LUT
static const struct {
  float max_temp;
  float current_limit_factor;
} temp_bands[] = {
    {PM_TEMP_CONTROL_BAND_1_MAX_TEMP, 1.0},
    {PM_TEMP_CONTROL_BAND_2_MAX_TEMP, 0.7},
    {PM_TEMP_CONTROL_BAND_3_MAX_TEMP, 0.5},
    {PM_TEMP_CONTROL_BAND_4_MAX_TEMP, 0.3},
};

#endif

void pm_monitor_power_sources(void) {
  // Periodically called timer to request PMIC measurements. PMIC will call
  // pm_pmic_data_ready() callback when the measurements are ready.
  pmic_measure(pm_pmic_data_ready, NULL);
}

// pmic measurement callback
void pm_pmic_data_ready(void* context, pmic_report_t* report) {
  pm_driver_t* drv = &g_pm;

  // Store measurement timestamp
  if (drv->pmic_last_update_us == 0) {
    drv->pmic_sampling_period_ms = PM_TIMER_PERIOD_MS;
  } else {
    // Calculate the time since the last PMIC update
    drv->pmic_sampling_period_ms =
        (systick_us() - drv->pmic_last_update_us) / 1000;
  }
  drv->pmic_last_update_us = systick_us();
  // Copy pmic data
  memcpy(&drv->pmic_data, report, sizeof(pmic_report_t));

  // Get wireless charger data
  stwlc38_get_report(&drv->wireless_data);

  pm_parse_power_source_state(drv);

  // Run battery charging controller
  pm_charging_controller(drv);

  drv->battery_ocv =
      battery_meas_to_ocv(&drv->fuel_gauge.model, drv->pmic_data.vbat,
                          drv->pmic_data.ibat, drv->pmic_data.ntc_temp);

  if (!drv->fuel_gauge_initialized) {
    // Fuel gauge not initialized yet, battery SoC not available, sample the
    // battery data into the circular buffer.
    pm_battery_sampling(drv->pmic_data.vbat, drv->pmic_data.ibat,
                        drv->pmic_data.ntc_temp);

  } else {
    if (drv->woke_up_from_suspend) {
#ifdef USE_RTC

      // Use known battery self-discharge rate to compensate the fuel gauge
      // estimation during the suspend period. Since this period may be very
      // long and the battery temperature may vary, use the average ambient
      // temperature.
      pm_compensate_fuel_gauge(&drv->fuel_gauge.soc, drv->time_in_suspend_s,
                               PM_SELF_DISG_RATE_SUSPEND_MA, 25.0f);

      // TODO: Currently in suspend mode we use single self-discharge rate
      // but in practice the discharge rate may change in case some components
      // remains active. Since the device is very likely to stay in suspend
      // mode for limited time, for now we decided to neglect this. but in
      // the future we may want to distinguish between different suspend modes
      // and use different self-discharge rates.

      fuel_gauge_set_soc(&drv->fuel_gauge, drv->fuel_gauge.soc,
                         drv->fuel_gauge.P);

#endif  // USE_RTC

      // clear the flag
      drv->woke_up_from_suspend = false;

    } else {
      fuel_gauge_update(&drv->fuel_gauge, drv->pmic_sampling_period_ms,
                        drv->pmic_data.vbat, drv->pmic_data.ibat,
                        drv->pmic_data.ntc_temp);
    }

    // Charging completed flag from PMIC controller
    if (drv->pmic_data.charge_status & 0x2) {
      // Force fuel gauge to 100%, keep the covariance
      drv->fully_charged = true;
      fuel_gauge_set_soc(&drv->fuel_gauge, 1.0f, drv->fuel_gauge.P);
    } else {
      if (drv->pmic_data.ibat > 0) {
        drv->fully_charged = false;
      }
    }

    // Ceil the float soc to user-friendly integer
    drv->soc_ceiled = (uint8_t)(drv->fuel_gauge.soc_latched * 100 + 0.999f);

    // Check battery voltage for low threshold
    if (drv->soc_ceiled <= PM_BATTERY_LOW_THRESHOLD_SOC && !drv->battery_low) {
      drv->battery_low = true;
    } else if (drv->soc_ceiled > PM_BATTERY_LOW_THRESHOLD_SOC &&
               drv->battery_low) {
      drv->battery_low = false;
    }

    // Process state machine with updated battery and power source information
    pm_process_state_machine();

    pm_store_data_to_backup_ram();

    if (drv->suspending) {
#ifdef USE_RTC
      // Schedule auto-hibernation rtc event
      pm_schedule_rtc_wakeup();
#endif
      drv->suspending = false;
      drv->suspended = true;
    }

    drv->state_machine_stabilized = true;
  }
}

void pm_charging_controller(pm_driver_t* drv) {
  if (drv->charging_enabled == false) {
    // Charging is disabled
    if (drv->i_chg_target_ma != 0) {
      drv->i_chg_target_ma = 0;
    } else {
      // No action required
      return;
    }
  } else if (drv->usb_connected) {
    drv->i_chg_target_ma = PM_BATTERY_CHARGING_CURRENT_MAX;

  } else if (drv->wireless_connected) {
    drv->i_chg_target_ma = PM_BATTERY_CHARGING_CURRENT_MAX;

  } else {
    // Charging enabled but no external power source, clear charging target
    drv->i_chg_target_ma = 0;
  }

  // charging current software limit
  if (drv->i_chg_target_ma > drv->i_chg_max_limit_ma) {
    drv->i_chg_target_ma = drv->i_chg_max_limit_ma;
  }

#ifdef PM_ENABLE_TEMP_CONTROL
  pm_temperature_controller(drv);
#endif

  if (drv->pmic_data.ntc_disconnected) {
    drv->i_chg_target_ma = 0;
  }

  if (drv->soc_target == 100) {
    drv->soc_target_reached = false;
  } else if (fabsf((-drv->pmic_data.ibat) - (float)drv->i_chg_target_ma) <=
             20.0f) {
    // Translate SoC target to charging voltage via battery model
    float target_ocv_voltage_v =
        battery_ocv(&drv->fuel_gauge.model, drv->soc_target / 100.0f,
                    drv->pmic_data.ntc_temp, false);

    float battery_ocv_v =
        battery_meas_to_ocv(&drv->fuel_gauge.model, drv->pmic_data.vbat,
                            drv->pmic_data.ibat, drv->pmic_data.ntc_temp);

    drv->target_battery_ocv_v_tau =
        (drv->target_battery_ocv_v_tau * 0.95f) +
        (battery_ocv_v * 0.05f);  // Exponential smoothing

    if (drv->target_battery_ocv_v_tau > target_ocv_voltage_v) {
      // current voltage is within tight bounds of target voltage,
      // we may also force SoC estimate to target value.
      if (drv->target_battery_ocv_v_tau < target_ocv_voltage_v + 0.15) {
        fuel_gauge_set_soc(&drv->fuel_gauge,
                           (drv->soc_target / 100.0f) - 0.0001f,
                           drv->fuel_gauge.P);
      }

      drv->soc_target_reached = true;
    }
  } else if (drv->soc_ceiled < drv->soc_target) {
    drv->soc_target_reached = false;
  }

  if (drv->soc_target_reached) {
    drv->i_chg_target_ma = 0;
  }

  // Set charging target
  if (drv->i_chg_target_ma != pmic_get_charging_limit()) {
    // Set charging current limit
    pmic_set_charging_limit(drv->i_chg_target_ma);
  }

  if (drv->i_chg_target_ma == 0) {
    pmic_set_charging(false);
  } else {
    // Clear and release charger if it has any errors
    if (drv->pmic_data.charge_err || drv->pmic_data.charge_sensor_err) {
      pmic_clear_charger_errors();
    }

    pmic_set_charging(true);
  }
}

#ifdef PM_ENABLE_TEMP_CONTROL

static void pm_temperature_controller(pm_driver_t* drv) {
  if (ticks_expired(drv->temp_control_timeout)) {
    uint16_t i_chg_temp_limit_ma = 0;

    i_chg_temp_limit_ma = 0;  // Default to safety limit
    for (size_t i = 0; i < sizeof(temp_bands) / sizeof(temp_bands[0]); ++i) {
      if (drv->pmic_data.ntc_temp < temp_bands[i].max_temp) {
        i_chg_temp_limit_ma = PM_BATTERY_CHARGING_CURRENT_MAX *
                              temp_bands[i].current_limit_factor;
        break;
      }
    }

    // If the temperature limit has changed, update the limit and reset the
    // debounce timer
    if (drv->i_chg_temp_limit_ma != i_chg_temp_limit_ma) {
      drv->i_chg_temp_limit_ma = i_chg_temp_limit_ma;
      drv->temp_control_timeout = ticks_timeout(PM_TEMP_CONTROL_IDLE_PERIOD_MS);
    }
  }

  if (drv->i_chg_target_ma > drv->i_chg_temp_limit_ma) {
    // Limit the charging current by temperature controller
    drv->i_chg_target_ma = drv->i_chg_temp_limit_ma;
    drv->temp_control_active = true;
  } else {
    drv->temp_control_active = false;
  }
}

#endif

static void pm_battery_sampling(float vbat, float ibat, float ntc_temp) {
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

static void pm_parse_power_source_state(pm_driver_t* drv) {
  // Check USB power source status
  if (drv->pmic_data.usb_status != 0x0) {
    if (!drv->usb_connected) {
      drv->usb_connected = true;
      notify_send(NOTIFY_POWER_STATUS_CHANGE);
    }
  } else {
    if (drv->usb_connected) {
      drv->usb_connected = false;
      notify_send(NOTIFY_POWER_STATUS_CHANGE);
    }
  }

  // Check wireless charger status
  if (drv->wireless_data.vout_ready) {
    if (!drv->wireless_connected) {
      drv->wireless_connected = true;
      notify_send(NOTIFY_POWER_STATUS_CHANGE);
    }
  } else {
    if (drv->wireless_connected) {
      drv->wireless_connected = false;
      notify_send(NOTIFY_POWER_STATUS_CHANGE);
    }
  }

  // Check battery voltage for critical (undervoltage) threshold
  if ((drv->pmic_data.vbat < PM_BATTERY_UNDERVOLT_THR_V) &&
      !drv->battery_critical && !drv->usb_connected) {
    // Force Fuel gauge to 0, keep the covariance
    fuel_gauge_set_soc(&drv->fuel_gauge, 0.0f, drv->fuel_gauge.P);
    drv->battery_critical = true;

  } else if (drv->fuel_gauge.soc_latched >=
                 (PM_BATTERY_CRITICAL_RECOVERY_SOC) ||
             drv->usb_connected) {
    // Restore the battery critical state
    drv->battery_critical = false;
  }
}

void pm_battery_initial_soc_guess(void) {
  pm_driver_t* drv = &g_pm;

  irq_key_t irq_key = irq_lock();

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

  irq_unlock(irq_key);
}

#endif
