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
#include <sys/pmic.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <trezor_rtl.h>

#include "../power_manager_poll.h"
#include "../stwlc38/stwlc38.h"
#include "power_manager_internal.h"

// Global driver instance
pm_driver_t g_pm = {
    .initialized = false,
};

// Forward declarations of static functions
static void pm_monitoring_timer_handler(void* context);
static void pm_shutdown_timer_handler(void* context);

// API Implementation

pm_status_t pm_init(bool inherit_state) {
  pm_driver_t* drv = &g_pm;

  if (drv->initialized) {
    return PM_OK;
  }

  // Clear driver instance
  memset(drv, 0, sizeof(pm_driver_t));

  // Initialize hardware subsystems
  if (!pmic_init() || !stwlc38_init()) {
    pm_deinit();
    return PM_ERROR;
  }

  if (!pm_poll_init()) {
    pm_deinit();
    return PM_ERROR;
  }

  // Initialize fuel gauge
  fuel_gauge_init(&drv->fuel_gauge, PM_FUEL_GAUGE_R, PM_FUEL_GAUGE_Q,
                  PM_FUEL_GAUGE_R_AGGRESSIVE, PM_FUEL_GAUGE_Q_AGGRESSIVE,
                  PM_FUEL_GAUGE_P_INIT);

  // Create monitoring timer
  drv->monitoring_timer = systimer_create(pm_monitoring_timer_handler, NULL);
  systimer_set_periodic(drv->monitoring_timer, PM_BATTERY_SAMPLING_PERIOD_MS);

  // Create shutdown timer
  drv->shutdown_timer = systimer_create(pm_shutdown_timer_handler, NULL);

  // Initial power source measurement
  pmic_measure(pm_pmic_data_ready, NULL);

  // Try to recover SoC from the backup RAM
  backup_ram_power_manager_data_t pm_recovery_data;
  backup_ram_status_t status =
      backup_ram_read_power_manager_data(&pm_recovery_data);

  if (status == BACKUP_RAM_OK) {
    fuel_gauge_set_soc(&drv->fuel_gauge, pm_recovery_data.soc,
                       pm_recovery_data.P);
  } else {
    // Wait for 1s to sample battery data
    systick_delay_ms(1000);
    pm_battery_initial_soc_guess();
  }

  if (inherit_state) {
    // Inherit power manager state left in backup RAM from bootloader.
    // in case of error, start with PM_STATE_POWER_SAVE as a lowest state in
    // active mode.
    if (status != BACKUP_RAM_OK &&
        (pm_recovery_data.bootloader_exit_state != PM_STATE_POWER_SAVE &&
         pm_recovery_data.bootloader_exit_state != PM_STATE_ACTIVE)) {
      drv->state = PM_STATE_POWER_SAVE;

    } else {
      // Backup RAM contain valid data
      drv->state = pm_recovery_data.bootloader_exit_state;
    }

  } else {
    // Start in lowest state and wait for the bootup sequence to
    // finish (call of pm_turn_on())
    drv->state = PM_STATE_HIBERNATE;
  }

  // Fuel gauge SoC available, set fuel_gauge initialized.
  drv->fuel_gauge_initialized = true;

  // Enable charging by default to max current
  drv->charging_enabled = true;
  pm_charging_set_max_current(PM_BATTERY_CHARGING_CURRENT_MAX);

  // Set default SOC limit
  drv->soc_limit = 100;

  // Poll until fuel_gauge is initialized and first PMIC & WLC measurements
  // propagates into power_monitor.
  bool state_machine_stabilized;
  do {
    irq_key_t irq_key = irq_lock();
    state_machine_stabilized = drv->state_machine_stabilized;
    irq_unlock(irq_key);
  } while (!state_machine_stabilized);

  drv->initialized = true;

  return PM_OK;
}

void pm_deinit(void) {
  pm_driver_t* drv = &g_pm;

  pm_poll_deinit();

  if (drv->monitoring_timer) {
    systimer_delete(drv->monitoring_timer);
    drv->monitoring_timer = NULL;
  }

  if (drv->shutdown_timer) {
    systimer_delete(drv->shutdown_timer);
    drv->shutdown_timer = NULL;
  }

  if (drv->fuel_gauge_initialized) {
    pm_store_data_to_backup_ram();
  }

  pmic_deinit();
  stwlc38_deinit();

  drv->initialized = false;
}

pm_status_t pm_get_state(pm_state_t* state) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();

  state->usb_connected = drv->usb_connected;
  state->wireless_connected = drv->wireless_connected;

  if (drv->pmic_data.ibat > 0.0f) {
    state->charging_status = PM_BATTERY_DISCHARGING;
  } else if (drv->pmic_data.ibat < 0.0f) {
    state->charging_status = PM_BATTERY_CHARGING;
  } else {
    state->charging_status = PM_BATTERY_IDLE;
  }

  state->power_state = drv->state;
  state->soc = drv->soc_ceiled;

  irq_unlock(irq_key);

  return PM_OK;
}

pm_status_t pm_suspend(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  drv->request_suspend = true;
  pm_process_state_machine();

  if (drv->state != PM_STATE_SUSPEND) {
    return PM_REQUEST_REJECTED;
  }

  return PM_OK;
}

pm_status_t pm_hibernate(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  drv->request_hibernate = true;
  pm_process_state_machine();

  systick_delay_ms(50);

  // Whenever hibernation request fall through, request was rejected
  return PM_REQUEST_REJECTED;
}

pm_status_t pm_turn_on(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  // Poll until at least single PMIC measurement is done
  uint32_t pmic_last_update_ms;
  do {
    irq_key_t irq_key = irq_lock();
    pmic_last_update_ms = drv->pmic_last_update_ms;
    irq_unlock(irq_key);
  } while (pmic_last_update_ms == 0);

  bool usb_connected = drv->usb_connected;
  bool wireless_connected =
      drv->wireless_connected &&
      drv->pmic_data.vbat > PM_BATTERY_UNDERVOLT_RECOVERY_WPC_THR_V;

  // Check if device has enough power to startup
  if ((!usb_connected && !wireless_connected) &&
      (drv->pmic_data.vbat < PM_BATTERY_UNDERVOLT_RECOVERY_THR_V ||
       drv->battery_critical)) {
    drv->battery_critical = true;
    pm_store_data_to_backup_ram();
    return PM_REQUEST_REJECTED;
  }

  drv->request_turn_on = true;
  pm_process_state_machine();

  if (drv->state == PM_STATE_HIBERNATE || drv->state == PM_STATE_CHARGING) {
    return PM_REQUEST_REJECTED;
  }

  // Set monitoiring timer with longer period
  systimer_set_periodic(drv->monitoring_timer, PM_TIMER_PERIOD_MS);

  return PM_OK;
}

pm_status_t pm_get_report(pm_report_t* report) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();

  // Copy current data into report
  report->power_state = drv->state;
  report->usb_connected = drv->usb_connected;
  report->wireless_charger_connected = drv->wireless_connected;
  report->system_voltage_v = drv->pmic_data.vsys;
  report->battery_voltage_v = drv->pmic_data.vbat;
  report->battery_current_ma = drv->pmic_data.ibat;
  report->battery_temp_c = drv->pmic_data.ntc_temp;
  report->battery_soc = drv->fuel_gauge.soc;
  report->battery_soc_latched = drv->fuel_gauge.soc_latched;
  report->pmic_temp_c = drv->pmic_data.die_temp;
  report->wireless_rectifier_voltage_v = drv->wireless_data.vrect;
  report->wireless_output_voltage_v = drv->wireless_data.vout;
  report->wireless_current_ma = drv->wireless_data.icur;
  report->wireless_temp_c = drv->wireless_data.tmeas;

  irq_unlock(irq_key);

  return PM_OK;
}

pm_status_t pm_charging_enable(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  drv->charging_enabled = true;
  irq_key_t irq_key = irq_lock();
  pm_charging_controller(drv);
  irq_unlock(irq_key);

  return PM_OK;
}

pm_status_t pm_charging_disable(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  drv->charging_enabled = false;
  irq_key_t irq_key = irq_lock();
  pm_charging_controller(drv);
  irq_unlock(irq_key);

  return PM_OK;
}

pm_status_t pm_charging_set_max_current(uint16_t current_ma) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  if (current_ma > PM_BATTERY_CHARGING_CURRENT_MAX) {
    return PM_REQUEST_REJECTED;
  }

  if (current_ma < PM_BATTERY_CHARGING_CURRENT_MIN) {
    return PM_REQUEST_REJECTED;
  }

  drv->charging_current_max_limit_ma = current_ma;

  return PM_OK;
}

pm_status_t pm_store_data_to_backup_ram() {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  backup_ram_power_manager_data_t pm_data = {0};

  // Fuel gauge state
  if (drv->battery_critical) {
    pm_data.soc = 0;
  } else {
    pm_data.soc = drv->fuel_gauge.soc;
  }
  pm_data.P = drv->fuel_gauge.P;

  // Power manager state
  pm_data.bat_critical = drv->battery_critical;
  pm_data.bootloader_exit_state = drv->state;

  backup_ram_status_t status = backup_ram_store_power_manager_data(&pm_data);

  if (status != BACKUP_RAM_OK) {
    return PM_ERROR;
  }

  return PM_OK;
}

pm_status_t pm_wakeup_flags_set(pm_wakeup_flags_t flags) {
  pm_driver_t* drv = &g_pm;
  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }
  irq_key_t irq_key = irq_lock();
  drv->wakeup_flags |= flags;
  irq_unlock(irq_key);

  return PM_OK;
}

pm_status_t pm_wakeup_flags_reset(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  drv->wakeup_flags = 0;
  irq_unlock(irq_key);
  return PM_OK;
}

pm_status_t pm_wakeup_flags_get(pm_wakeup_flags_t* flags) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  *flags = drv->wakeup_flags;
  irq_unlock(irq_key);
  return PM_OK;
}

pm_status_t pm_set_soc_limit(uint8_t limit) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  if (limit > 100) {
    return PM_ERROR;
  }

  if (limit <= PM_SOC_LIMIT_HYSTERESIS) {
    return PM_ERROR;
  }

  drv->soc_limit = limit;
  return PM_OK;
}

// Timer handlers
static void pm_monitoring_timer_handler(void* context) {
  pm_monitor_power_sources();
}

static void pm_shutdown_timer_handler(void* context) {
  pm_driver_t* drv = &g_pm;
  drv->shutdown_timer_elapsed = true;
  pm_process_state_machine();
}

#endif
