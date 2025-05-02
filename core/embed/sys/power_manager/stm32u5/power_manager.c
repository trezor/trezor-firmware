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
#include <sys/irq.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <trezor_rtl.h>

#include "../npm1300/npm1300.h"
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

pm_status_t pm_init(bool skip_bootup_sequence, bool reboot_to_charing) {
  pm_driver_t* drv = &g_pm;

  if (drv->initialized) {
    return PM_OK;
  }

  // Initialize hardware subsystems
  if (!npm1300_init() || !stwlc38_init()) {
    pm_deinit();
    return PM_ERROR;
  }

  // Clear fuel gauge state
  memset(&drv->fuel_gauge, 0, sizeof(fuel_gauge_state_t));

  // Initialize fuel gauge
  fuel_gauge_init(&(drv->fuel_gauge), PM_FUEL_GAUGE_R, PM_FUEL_GAUGE_Q,
                  PM_FUEL_GAUGE_R_AGGRESSIVE, PM_FUEL_GAUGE_Q_AGGRESSIVE,
                  PM_FUEL_GAUGE_P_INIT);


  drv->check_initial_voltage = !skip_bootup_sequence;

  // Try to recover the power manages state left in backup ram.

  backup_ram_power_manager_data_t pm_recovery_data;
  backup_ram_status_t status =
      backup_ram_read_power_manager_data(&pm_recovery_data);

  if (reboot_to_charing) {
    drv->state = PM_STATE_CHARGING;
  } else {
    drv->state = PM_STATE_HIBERNATE;
  }

  if (status != BACKUP_RAM_OK) {
    drv->fuel_gauge_request_new_guess = false;
    drv->fuel_gauge_initialized = false;
  } else {
    // Backup RAM contain valid data
    if (skip_bootup_sequence) {
      // only inherit state on later stages
      drv->state = pm_recovery_data.bootloader_exit_state;
    }
    drv->battery_critical = pm_recovery_data.bat_crittical;

    // SOC sanity check
    if (pm_recovery_data.soc < 0.01f) {
      drv->fuel_gauge_initialized = false;
    } else {
      drv->fuel_gauge.soc = pm_recovery_data.soc;
      drv->fuel_gauge_request_new_guess = false;
      drv->fuel_gauge_initialized = true;
    }
  }
  // Disable charging by default
  drv->charging_enabled = false;

  // Create monitoring timer
  drv->monitoring_timer = systimer_create(pm_monitoring_timer_handler, NULL);
  systimer_set_periodic(drv->monitoring_timer, PM_BATTERY_SAMPLING_PERIOD_MS);

  // Create shutdown timer
  drv->shutdown_timer = systimer_create(pm_shutdown_timer_handler, NULL);

  // Initial power source measurement
  npm1300_measure(pm_pmic_data_ready, NULL);

  drv->initialized = true;
  return PM_OK;
}

void pm_deinit(void) {
  pm_driver_t* drv = &g_pm;

  if (drv->fuel_gauge_initialized) {
    pm_store_data_to_backup_ram();
  }

  if (drv->monitoring_timer) {
    systimer_delete(drv->monitoring_timer);
    drv->monitoring_timer = NULL;
  }

  if (drv->shutdown_timer) {
    systimer_delete(drv->shutdown_timer);
    drv->shutdown_timer = NULL;
  }

  npm1300_deinit();
  stwlc38_deinit();

  drv->initialized = false;
}

pm_status_t pm_get_events(pm_event_t* event_flags) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  *event_flags = drv->event_flags;
  PM_CLEAR_ALL_EVENTS(drv->event_flags);
  irq_unlock(irq_key);

  return PM_OK;
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

  switch (drv->state) {
    case PM_STATE_POWER_SAVE:
      state->power_mode = PM_POWER_MODE_POWER_SAVE;
      break;
    case PM_STATE_SHUTTING_DOWN:
      state->power_mode = PM_POWER_MODE_SHUTTING_DOWN;
      break;
    case PM_STATE_ACTIVE:
      state->power_mode = PM_POWER_MODE_ACTIVE;
      break;
    default:
      state->power_mode = PM_POWER_MODE_NOT_INITIALIZED;
  }

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

pm_status_t  pm_hibernate(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  drv->request_hibernate = true;
  pm_process_state_machine();

  if (drv->state != PM_STATE_HIBERNATE) {
    return PM_REQUEST_REJECTED;
  }

  return PM_OK;
}

pm_status_t pm_turn_on(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  drv->request_turn_on = true;

  if (drv->check_initial_voltage) {
    while (drv->pmic_last_update_ms == 0 || !wireless_data_valid) {
      systick_delay_ms(10);
    }

    if (((drv->pmic_data.vbat < PM_BATTERY_UNDERVOLT_THRESHOLD_V || (drv->battery_critical && drv->pmic_data.vbat < (PM_BATTERY_UNDERVOLT_THRESHOLD_V + PM_BATTERY_UNDERVOLT_HYSTERESIS_V))) && drv->pmic_data.usb_status == 0x0 &&
        !drv->wireless_connected) ) {
      pm_store_data_to_backup_ram();
      return PM_REQUEST_REJECTED;
    }
  }

  pm_process_state_machine();

  if (!drv->fuel_gauge_initialized) {
    systick_delay_ms(1000);
    pm_battery_initial_soc_guess();
    drv->fuel_gauge_initialized = true;
  }

  // Set monitoring timer with longer period
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
  pm_charging_controller(drv);

  return PM_OK;
}

pm_status_t pm_charging_disable(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  drv->charging_enabled = false;
  pm_charging_controller(drv);

  return PM_OK;
}

pm_status_t pm_store_data_to_backup_ram(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  backup_ram_power_manager_data_t pm_data = {0};
  pm_data.bootloader_exit_state = drv->state;
  pm_data.soc = drv->fuel_gauge.soc;
  pm_data.bat_crittical = drv->battery_critical;

  backup_ram_status_t status = backup_ram_store_power_manager_data(&pm_data);

  if (status != BACKUP_RAM_OK) {
    return PM_ERROR;
  }

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
