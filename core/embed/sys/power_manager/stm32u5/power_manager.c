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

#include <trezor_rtl.h>

#include <sys/backup_ram.h>
#include <sys/irq.h>
#include <sys/pmic.h>
#include <sys/suspend.h>
#include <sys/systick.h>
#include <sys/systimer.h>

#ifdef USE_RTC
#include <sys/rtc.h>
#endif

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
static bool pm_load_recovery_data(pm_recovery_data_t* recovery);

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
  if (drv->monitoring_timer == NULL) {
    pm_deinit();
    return PM_ERROR;
  }

  systimer_set_periodic(drv->monitoring_timer, PM_BATTERY_SAMPLING_PERIOD_MS);

  // Create shutdown timer
  drv->shutdown_timer = systimer_create(pm_shutdown_timer_handler, NULL);
  if (drv->shutdown_timer == NULL) {
    pm_deinit();
    return PM_ERROR;
  }

  // Initial power source measurement
  pmic_measure(pm_pmic_data_ready, NULL);

  // Try to recover SoC from the backup RAM
  pm_recovery_data_t recovery;
  bool recovery_ok = pm_load_recovery_data(&recovery);

  if (!recovery_ok) {
    // Wait for 1s to sample battery data
    systick_delay_ms(1000);
  }

  // In this part of the code, power monitoring timer is already running, so
  // we have to prevent simultaneous access to the driver instance by locking
  // the IRQs.
  irq_key_t irq_key = irq_lock();

  if (recovery_ok) {
    fuel_gauge_set_soc(&drv->fuel_gauge, recovery.soc, recovery.P);
  } else {
    pm_battery_initial_soc_guess();
  }

  if (inherit_state) {
    // Inherit power manager state left in backup RAM from bootloader.
    // in case of error, start with PM_STATE_POWER_SAVE as a lowest state in
    // active mode.
    if (!recovery_ok &&
        (recovery.bootloader_exit_state != PM_STATE_POWER_SAVE &&
         recovery.bootloader_exit_state != PM_STATE_ACTIVE)) {
      drv->state = PM_STATE_POWER_SAVE;

    } else {
      // Backup RAM contain valid data
      drv->state = recovery.bootloader_exit_state;
    }

  } else {
    // Start in lowest state and wait for the bootup sequence to
    // finish (call of pm_turn_on())
    drv->state = PM_STATE_HIBERNATE;
  }

  // Enable charging by default to max current
  drv->charging_enabled = true;

  // Set default SOC limit and max charging current limit
  drv->soc_limit = 100;
  drv->charging_current_max_limit_ma = PM_BATTERY_CHARGING_CURRENT_MAX;

  // Fuel gauge SoC available, set fuel_gauge initialized.
  drv->fuel_gauge_initialized = true;

  irq_unlock(irq_key);

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

  state->power_status = drv->state;
  state->soc = drv->soc_ceiled;

  irq_unlock(irq_key);

  return PM_OK;
}

// This callback is called from inside the system_suspend() function
// when the rtc wake-up timer expires. The callback can perform
// measurements and update the fuel gauge state.
// - The callback can schedule the next wake-up by calling
// rtc_wakeup_timer_start().
// - If the callback return with wakeup_flags set, system_suspend() returns.
#ifdef USE_RTC
void pm_rtc_wakeup_callback(void* context) {
  // TODO: update fuel gauge state
  // TODO: decide whether to reschedule the next wake-up or wake up the coreapp
  if (true) {
    // Reschedule the next wake-up
    rtc_wakeup_timer_start(10, pm_rtc_wakeup_callback, NULL);
  } else {
    // Wake up the coreapp
    wakeup_flags_set(WAKEUP_FLAG_RTC);
  }
}
#endif

pm_status_t pm_suspend(wakeup_flags_t* wakeup_reason) {
  pm_driver_t* drv = &g_pm;

  if (wakeup_reason != NULL) {
    *wakeup_reason = 0;
  }

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  drv->request_suspend = true;

  pm_process_state_machine();

  // Something went wrong, suspend request was not accepted
  if (drv->request_suspend == true || drv->state != PM_STATE_SUSPEND) {
    irq_unlock(irq_key);
    return PM_REQUEST_REJECTED;
  }

  irq_unlock(irq_key);

#ifdef USE_RTC
  // Automatically wakes up after specified time and call pm_rtc_wakeup_callback
  rtc_wakeup_timer_start(10, pm_rtc_wakeup_callback, NULL);
#endif

  wakeup_flags_t wakeup_flags = system_suspend();

#ifdef USE_RTC
  rtc_wakeup_timer_stop();
#endif

  // TODO: Handle wake-up flags
  // UNUSED(wakeup_flags);

  // Exit hibernation state if it was requested
  irq_key = irq_lock();
  drv->request_exit_suspend = true;
  pm_process_state_machine();
  irq_unlock(irq_key);

  if (wakeup_reason != NULL) {
    *wakeup_reason = wakeup_flags;
  }

  return PM_OK;
}

pm_status_t pm_hibernate(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  drv->request_hibernate = true;
  pm_process_state_machine();
  irq_unlock(irq_key);

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
    irq_key_t irq_key = irq_lock();
    drv->battery_critical = true;
    pm_store_data_to_backup_ram();
    irq_unlock(irq_key);

    return PM_REQUEST_REJECTED;
  }

  irq_key_t irq_key = irq_lock();
  drv->request_turn_on = true;
  pm_process_state_machine();
  irq_unlock(irq_key);

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

  irq_key_t irq_key = irq_lock();
  drv->charging_enabled = true;
  pm_charging_controller(drv);
  irq_unlock(irq_key);

  return PM_OK;
}

pm_status_t pm_charging_disable(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  drv->charging_enabled = false;
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

  irq_key_t irq_key = irq_lock();
  drv->charging_current_max_limit_ma = current_ma;
  pm_charging_controller(drv);
  irq_unlock(irq_key);

  return PM_OK;
}

pm_status_t pm_store_data_to_backup_ram() {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();

  pm_recovery_data_t recovery = {.version = PM_RECOVERY_DATA_VERSION};

  // Fuel gauge state
  if (drv->battery_critical) {
    recovery.soc = 0;
  } else {
    recovery.soc = drv->fuel_gauge.soc;
  }
  recovery.P = drv->fuel_gauge.P;

  // Power manager state
  recovery.bat_critical = drv->battery_critical;
  recovery.bootloader_exit_state = drv->state;

  irq_unlock(irq_key);

  bool write_ok =
      backup_ram_write(BACKUP_RAM_KEY_PM_RECOVERY, &recovery, sizeof(recovery));

  if (!write_ok) {
    return PM_ERROR;
  }

  return PM_OK;
}

static bool pm_load_recovery_data(pm_recovery_data_t* recovery) {
  union {
    uint16_t version;
    pm_recovery_data_t v1;  // v1 is the only version currently supported
    // pm_recovery_data_t v2;
  } data;

  size_t data_size = 0;

  memset(recovery, 0, sizeof(*recovery));

  bool read_ok = backup_ram_read(BACKUP_RAM_KEY_PM_RECOVERY, &data,
                                 sizeof(data), &data_size);

  if (!read_ok) {
    return false;
  }

  // Incremental migration logic can be added here if needed
  // if (data.version == PM_RECOVERY_DATA_VERSION_V1) {
  //   migrate_pm_recovery_data_v1_to_v2(&data.v1, &date_v2);
  // }

  if (data.version != PM_RECOVERY_DATA_VERSION) {
    return false;
  }

  *recovery = data.v1;

  if (recovery->soc < 0.0f || recovery->soc > 1.0f) {
    return false;
  }

  return true;
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

  irq_key_t irq_key = irq_lock();
  drv->soc_limit = limit;
  irq_unlock(irq_key);

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
