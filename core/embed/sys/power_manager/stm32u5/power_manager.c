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
#include <sys/rtc_scheduler.h>
#endif

#include "../fuel_gauge/battery_model.h"
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
static pm_status_t pm_wait_to_stabilize(pm_driver_t* drv, uint32_t timeout_ms);

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

  // Create shutdown timer
  drv->shutdown_timer = systimer_create(pm_shutdown_timer_handler, NULL);
  if (drv->shutdown_timer == NULL) {
    pm_deinit();
    return PM_ERROR;
  }

  systimer_set_periodic(drv->monitoring_timer, PM_TIMER_PERIOD_MS);

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
#ifdef USE_RTC

    // RTC compensation should happen only during initialization in bootloader
    if (!inherit_state) {
      // Get RTC timestamp and compare it with the timestamp from recovery data
      // to estimate time off and compensate self-discharge of the battery.
      uint32_t rtc_timestamp;
      if (recovery.last_capture_timestamp != 0 &&
          rtc_get_timestamp(&rtc_timestamp)) {
        // If the RTC timestamp is older than the last captured timestamp,
        // we will not use it.
        if (rtc_timestamp >= recovery.last_capture_timestamp) {
          pm_compensate_fuel_gauge(
              &recovery.soc, rtc_timestamp - recovery.last_capture_timestamp,
              PM_SELF_DISG_RATE_HIBERNATION_MA, 25.0f);
        }
      }
    }

#endif

    drv->battery_critical = recovery.bat_critical;
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

  // Set default SOC target and max charging current limit
  drv->soc_target = 100;
  drv->i_chg_max_limit_ma = PM_BATTERY_CHARGING_CURRENT_MAX;

#ifdef PM_ENABLE_TEMP_CONTROL
  drv->i_chg_temp_limit_ma = PM_BATTERY_CHARGING_CURRENT_MAX;
#endif

  // Fuel gauge SoC available, set fuel_gauge initialized.
  drv->fuel_gauge_initialized = true;

  irq_unlock(irq_key);

  // Wait to stabilize the state machine
  pm_status_t status = pm_wait_to_stabilize(drv, PM_STABILIZATION_TIMEOUT_MS);
  if (status != PM_OK) {
    pm_deinit();
    return status;
  }

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
  state->ntc_connected = !drv->pmic_data.ntc_disconnected;

  if (pm_is_charging()) {
    state->charging_status = PM_BATTERY_CHARGING;
  } else if (drv->pmic_data.ibat > 0.0f) {
    state->charging_status = PM_BATTERY_DISCHARGING;
  } else {
    state->charging_status = PM_BATTERY_IDLE;
  }

  // Charging-limited detection with 5s filter
  // Conditions to consider:
  //  - Only when charging
  //  - Only when PMIC reports constant-current phase (decoded flag)
  //  - Consider measured current vs target with a small margin
  //  - Assert after predicate holds continuously for >= 5000 ms
  //  - Clear immediately when predicate breaks or not charging
  const bool is_charging = (state->charging_status == PM_BATTERY_CHARGING);
  const float MAX_DIFF_MA = 15;  // tolerance below target current
  const uint32_t FILTER_ASSERT_MS = 5000;

  bool predicate = false;
  if (is_charging) {
    const bool cc_phase = drv->pmic_data.cc_phase;
    float iabs_ma = drv->pmic_data.ibat;
    if (iabs_ma < 0.0f) {
      iabs_ma = -iabs_ma;  // ibat < 0 => charging
    }
    predicate = cc_phase && (iabs_ma < (drv->i_chg_target_ma - MAX_DIFF_MA));
  }

  if (predicate) {
    uint32_t now = systick_ms();
    if (drv->charging_limited_start_ms == 0U) {
      drv->charging_limited_start_ms = now;
    } else if (!drv->charging_limited_latched &&
               (now - drv->charging_limited_start_ms) >= FILTER_ASSERT_MS) {
      drv->charging_limited_latched = true;
    }
  } else {
    drv->charging_limited_start_ms = 0U;
    drv->charging_limited_latched = false;
  }

  state->charging_limited = drv->charging_limited_latched;

  state->power_status = drv->state;
  state->soc = drv->soc_ceiled;
  state->battery_temp = drv->pmic_data.ntc_temp;
  state->battery_ocv = drv->battery_ocv;

  irq_unlock(irq_key);

  return PM_OK;
}

// This callback is called from inside the system_suspend() function
// when the rtc wake-up timer expires.
#ifdef USE_RTC
void pm_rtc_wakeup_callback(void* context) {
  pm_driver_t* drv = &g_pm;

  // Clear autohibernate event reference
  drv->autohibernate_event_id = 0;
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
    drv->request_suspend = false;
    irq_unlock(irq_key);
    return PM_REQUEST_REJECTED;
  }

  irq_unlock(irq_key);

#ifdef USE_RTC
  // Read the current timestamp before entering suspend mode
  if (!rtc_get_timestamp(&drv->suspend_timestamp)) {
    return PM_ERROR;
  }
#endif

  wakeup_flags_t wakeup_flags = system_suspend();

#ifdef USE_RTC
  // Cancel autohibernate event if scheduled
  if (drv->autohibernate_event_id != 0) {
    rtc_cancel_wakeup_event(drv->autohibernate_event_id);
    drv->autohibernate_event_id = 0;
  }
#endif

  // Wait for pmic measurements to stabilize the fuel gauge estimation.
  pm_status_t status = pm_wait_to_stabilize(drv, PM_STABILIZATION_TIMEOUT_MS);
  if (status != PM_OK) {
    // timeout during state machine stabilization
    return PM_TIMEOUT;
  }

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
  uint32_t pmic_last_update_us;
  do {
    irq_key_t irq_key = irq_lock();
    pmic_last_update_us = drv->pmic_last_update_us;
    irq_unlock(irq_key);
  } while (pmic_last_update_us == 0);

  // Check if device has enough power to startup
  if (drv->battery_critical) {
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
  drv->i_chg_max_limit_ma = current_ma;
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

  recovery.soc = drv->fuel_gauge.soc;
  recovery.P = drv->fuel_gauge.P;

  // Power manager state
  recovery.bat_critical = drv->battery_critical;
  recovery.bootloader_exit_state = drv->state;

#ifdef USE_RTC
  if (!rtc_get_timestamp(&recovery.last_capture_timestamp)) {
    // If RTC timestamp cannot be obtained, set it to 0
    recovery.last_capture_timestamp = 0;
  }
#endif

  irq_unlock(irq_key);

  bool write_ok =
      backup_ram_write(BACKUP_RAM_KEY_PM_RECOVERY, BACKUP_RAM_ITEM_PUBLIC,
                       &recovery, sizeof(recovery));

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

pm_status_t pm_set_soc_target(uint8_t target) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  if (target > 100) {
    return PM_ERROR;
  }

  irq_key_t irq_key = irq_lock();
  drv->soc_target = target;
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

bool pm_driver_suspend(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();

  if (drv->woke_up_from_suspend) {
    // Driver just woke up from suspend and have no data available yet.
    // Request the suspend but wait for the next pmic_meausrement
    drv->suspending = true;
  } else {
#ifdef USE_RTC
    // Schedule auto-hibernation rtc event
    pm_schedule_rtc_wakeup();
#endif
    drv->suspended = true;
  }

  // Delete the monitoring timer to stop the periodic sampling
  systimer_delete(drv->monitoring_timer);

  irq_unlock(irq_key);

  return true;
}

#ifdef USE_RTC

bool pm_schedule_rtc_wakeup(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return false;
  }

  // Capture the timestamp when device was active for the last time.
  if (!rtc_get_timestamp(&drv->last_active_timestamp)) {
    return false;
  }

  if ((drv->last_active_timestamp - drv->suspend_timestamp) >=
      PM_AUTO_HIBERNATE_TIMEOUT_S) {
    // Device is very long time in suspend mode without external power source,
    // hibernate it to save power.
    pm_hibernate();
  }

  if (drv->autohibernate_event_id == 0) {
    rtc_schedule_wakeup_event(
        drv->suspend_timestamp + PM_AUTO_HIBERNATE_TIMEOUT_S,
        pm_rtc_wakeup_callback, NULL, &drv->autohibernate_event_id);
  }

  return true;
}

#endif

bool pm_is_charging(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return false;
  }

  bool is_charging = false;

  irq_key_t irq_key = irq_lock();
  if (drv->charging_enabled &&
      (!drv->fully_charged && !drv->soc_target_reached) &&
      (drv->usb_connected || drv->wireless_connected)) {
    is_charging = true;
  }
  irq_unlock(irq_key);

  return is_charging;
}

bool pm_usb_is_connected(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return false;
  }

  bool usb_connected;
  irq_key_t irq_key = irq_lock();
  usb_connected = drv->usb_connected;
  irq_unlock(irq_key);

  return usb_connected;
}

bool pm_driver_resume(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return false;
  }

  if (!drv->suspended && !drv->suspending) {
    // Already resumed, nothing to do
    return true;
  }

  drv->suspended = false;
  drv->suspending = false;
  drv->woke_up_from_suspend = true;
  drv->state_machine_stabilized = false;

#ifdef USE_RTC

  uint32_t rtc_timestamp;
  rtc_get_timestamp(&rtc_timestamp);
  drv->time_in_suspend_s = (rtc_timestamp - drv->last_active_timestamp);

#endif

  // Recreate the monitoring timer
  drv->monitoring_timer = systimer_create(pm_monitoring_timer_handler, NULL);
  if (drv->monitoring_timer == NULL) {
    return false;
  }

  // Request new pmic measurement
  pmic_measure(pm_pmic_data_ready, NULL);

  // Set the periodic sampling period
  systimer_set_periodic(drv->monitoring_timer, PM_TIMER_PERIOD_MS);

  return true;
}

bool pm_driver_is_suspended(void) {
  pm_driver_t* drv = &g_pm;

  bool suspended;
  irq_key_t irq_key = irq_lock();
  suspended = drv->suspended;
  irq_unlock(irq_key);

  return suspended;
}

void pm_compensate_fuel_gauge(float* soc, uint32_t elapsed_s,
                              float battery_current_ma, float bat_temp_c) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return;
  }

  float compensation_mah = ((battery_current_ma)*elapsed_s) / 3600.0f;
  bool discharging_mode = battery_current_ma >= 0.0f;
  *soc -=
      (compensation_mah / battery_total_capacity(&drv->fuel_gauge.model,
                                                 bat_temp_c, discharging_mode));
}

static pm_status_t pm_wait_to_stabilize(pm_driver_t* drv, uint32_t timeout_ms) {
  uint32_t expire_time = ticks_timeout(timeout_ms);

  // Poll until fuel_gauge is initialized and first PMIC & WLC measurements
  // propagates into power_monitor.
  bool state_machine_stabilized;
  do {
    if (ticks_expired(expire_time)) {
      return PM_TIMEOUT;
    }

    irq_key_t irq_key = irq_lock();
    state_machine_stabilized = drv->state_machine_stabilized;
    irq_unlock(irq_key);
  } while (!state_machine_stabilized);

  return PM_OK;
}

#endif
