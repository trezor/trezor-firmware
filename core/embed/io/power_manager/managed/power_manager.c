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

// Glue of the managed power-manager policy: implements <io/power_manager.h>
// by driving the pure core (pm_core.h) with real time and real samples, and
// carrying out the actions it returns on the hardware and the OS services.
// Nothing in here decides policy; everything in here owns a side effect.

#include <trezor_rtl.h>

#include <io/backlight.h>
#include <io/notify.h>
#include <io/pmic.h>
#include <io/suspend.h>
#include <sec/backup_ram.h>
#include <sys/bootutils.h>
#include <sys/irq.h>
#include <sys/systick.h>
#include <sys/systimer.h>

#ifdef USE_RTC
#include <sys/rtc.h>
#include <sys/rtc_scheduler.h>
#endif

#ifdef USE_TELEMETRY
#include <sec/telemetry.h>
#endif

#include "../fuel_gauge/battery.h"
#include "../power_manager_poll.h"
#include "power_manager_internal.h"

// Global driver instance
pm_driver_t g_pm = {
    .initialized = false,
};

// Board tunables handed to the core
static const pm_config_t g_pm_config = {
    .low_soc_percent = BATTERY_LOW_SOC_PERCENT,
    .power_save_backlight = PM_POWER_SAVE_BACKLIGHT_LIMIT,
#ifdef USE_RTC
    .suspend_current_ma = PM_SUSPEND_CURRENT_MA,
    .hibernation_current_ma = PM_HIBERNATION_CURRENT_MA,
#endif
};

// Forward declarations of static functions
static void pm_monitoring_timer_handler(void* context);
static void pm_pmic_data_ready(void* context, pmic_report_t* report);
static void pm_apply_actions(pm_driver_t* drv, const pm_actions_t* actions);
static bool pm_load_recovery_data(pm_recovery_data_t* recovery);
static pm_status_t pm_wait_to_stabilize(pm_driver_t* drv, uint32_t timeout_ms);

pm_status_t pm_init(bool inherit_state) {
  pm_driver_t* drv = &g_pm;

  if (drv->initialized) {
    return PM_OK;
  }

  // Clear driver instance (including the core)
  memset(drv, 0, sizeof(pm_driver_t));
  pm_core_reset(&drv->core);

  // Initialize hardware subsystems
  if (!pmic_init()) {
    pm_deinit();
    return PM_ERROR;
  }

#ifdef USE_WIRELESS_CHARGER
  if (!stwlc38_init()) {
    pm_deinit();
    return PM_ERROR;
  }
#endif

  if (!pm_poll_init()) {
    pm_deinit();
    return PM_ERROR;
  }

  // Initialize battery model with fuel gauge estimator
  bat_init();

  // Create monitoring timer
  drv->monitoring_timer = systimer_create(pm_monitoring_timer_handler, NULL);
  if (drv->monitoring_timer == NULL) {
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

  // How long the device was off since the snapshot, for self-discharge
  // compensation. Only the bootloader compensates (the kernel inherits a state
  // the bootloader already compensated), and only when the RTC is sane.
  uint32_t elapsed_s = 0;
#ifdef USE_RTC
  if (recovery_ok && !inherit_state && recovery.last_capture_timestamp != 0) {
    uint32_t rtc_timestamp;
    if (rtc_get_timestamp(&rtc_timestamp) &&
        rtc_timestamp >= recovery.last_capture_timestamp) {
      elapsed_s = rtc_timestamp - recovery.last_capture_timestamp;
    }
  }
#endif

  // In this part of the code, power monitoring timer is already running, so
  // we have to prevent simultaneous access to the driver instance by locking
  // the IRQs.
  irq_key_t irq_key = irq_lock();
  pm_core_init(&drv->core, &g_pm_config, inherit_state,
               recovery_ok ? &recovery : NULL, elapsed_s);
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

  if (bat_fg_is_locked()) {
    pm_store_data_to_backup_ram();
  }

  pmic_deinit();
#ifdef USE_WIRELESS_CHARGER
  stwlc38_deinit();
#endif

  drv->initialized = false;
}

pm_status_t pm_get_state(pm_state_t* state) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  pm_core_get_state(&drv->core, state);
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

#ifndef USE_SUSPEND
  // This board has no low-power suspend path (no `suspend` feature), so there
  // is nothing to put the CPU into. Reject before touching the state machine
  // rather than parking it in PM_STATE_SUSPEND with the core still running.
  return PM_REQUEST_REJECTED;
#else
  pm_actions_t actions;

  irq_key_t irq_key = irq_lock();
  pm_core_request(&drv->core, PM_REQ_SUSPEND, systick_ms(), &actions);
  pm_apply_actions(drv, &actions);

  // Something went wrong, suspend request was not accepted
  if (drv->core.request_suspend || drv->core.state != PM_STATE_SUSPEND) {
    drv->core.request_suspend = false;
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

  // Leave the suspend state
  irq_key = irq_lock();
  pm_core_request(&drv->core, PM_REQ_EXIT_SUSPEND, systick_ms(), &actions);
  pm_apply_actions(drv, &actions);
  irq_unlock(irq_key);

  if (wakeup_reason != NULL) {
    *wakeup_reason = wakeup_flags;
  }

  return PM_OK;
#endif /* USE_SUSPEND */
}

pm_status_t pm_hibernate(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  pm_actions_t actions;

  irq_key_t irq_key = irq_lock();
  pm_core_request(&drv->core, PM_REQ_HIBERNATE, systick_ms(), &actions);
  pm_apply_actions(drv, &actions);  // does not return if it powers off
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
  bool has_sample;
  do {
    irq_key_t irq_key = irq_lock();
    has_sample = drv->core.has_sample;
    irq_unlock(irq_key);
  } while (!has_sample);

  // Check if device has enough power to startup
  if (drv->core.battery_critical) {
    pm_store_data_to_backup_ram();
    return PM_REQUEST_REJECTED;
  }

  pm_actions_t actions;

  irq_key_t irq_key = irq_lock();
  pm_core_request(&drv->core, PM_REQ_TURN_ON, systick_ms(), &actions);
  pm_apply_actions(drv, &actions);
  pm_power_status_t state = drv->core.state;
  irq_unlock(irq_key);

  if (state == PM_STATE_HIBERNATE || state == PM_STATE_CHARGING) {
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

  const pm_core_t* core = &drv->core;

  // Copy current data into report
  report->power_state = core->state;
  report->usb_connected = core->usb_connected;
  report->wireless_charger_connected = core->wireless_connected;
  report->system_voltage_v = core->pmic.vsys;
  report->battery_voltage_v = core->pmic.vbat;
  report->battery_current_ma = core->pmic.ibat;
  report->battery_temp_c = core->pmic.ntc_temp;

  bat_fg_state_t fg_state;
  bat_fg_get_state(&fg_state);
  report->battery_soc = fg_state.soc;
  report->battery_soc_latched = fg_state.soc_latched;

  report->pmic_temp_c = core->pmic.die_temp;
#ifdef USE_WIRELESS_CHARGER
  report->wireless_rectifier_voltage_v = drv->wireless_data.vrect;
  report->wireless_output_voltage_v = drv->wireless_data.vout;
  report->wireless_current_ma = drv->wireless_data.icur;
  report->wireless_temp_c = drv->wireless_data.tmeas;
#else
  report->wireless_rectifier_voltage_v = 0.0f;
  report->wireless_output_voltage_v = 0.0f;
  report->wireless_current_ma = 0.0f;
  report->wireless_temp_c = 0.0f;
#endif

  irq_unlock(irq_key);

  return PM_OK;
}

// --- Charging API ------------------------------------------------------------
// Each request changes the charger leaf's inputs and re-runs its controller
// at once, so the charger reflects the change before the next sample.

static pm_status_t pm_charging_request_done(pm_driver_t* drv) {
  pm_actions_t actions = {0};
  pm_charging_step(&drv->core, &actions);
  pm_charging_apply(&actions);
  return PM_OK;
}

pm_status_t pm_charging_enable(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  pm_charging_set_enabled(&drv->core, true);
  pm_status_t status = pm_charging_request_done(drv);
  irq_unlock(irq_key);

  return status;
}

pm_status_t pm_charging_disable(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  pm_charging_set_enabled(&drv->core, false);
  pm_status_t status = pm_charging_request_done(drv);
  irq_unlock(irq_key);

  return status;
}

pm_status_t pm_charging_set_max_current(uint16_t current_ma) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  pm_status_t status;
  if (pm_charging_set_max_limit(&drv->core, current_ma)) {
    status = pm_charging_request_done(drv);
  } else {
    // Out of range, or no charger: never report success for a limit that
    // would not be applied.
    status = PM_REQUEST_REJECTED;
  }
  irq_unlock(irq_key);

  return status;
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
  pm_charging_set_soc_target(&drv->core, target);
  irq_unlock(irq_key);

  return PM_OK;
}

bool pm_is_charging(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  bool is_charging = pm_charging_active(&drv->core);
  irq_unlock(irq_key);

  return is_charging;
}

bool pm_usb_is_connected(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return false;
  }

  // External-power presence is a PMIC measurement, not a charger feature:
  // a chargerless PMIC that still senses VBUS reports it the same way.
  irq_key_t irq_key = irq_lock();
  bool usb_connected = drv->core.usb_connected;
  irq_unlock(irq_key);

  return usb_connected;
}

// --- Recovery data -----------------------------------------------------------

pm_status_t pm_store_data_to_backup_ram(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();

  pm_recovery_data_t recovery = {.version = PM_RECOVERY_DATA_VERSION};
  pm_core_recovery(&drv->core, &recovery);

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

#ifdef USE_TELEMETRY
  // Update battery cycle counter telemetry
  float cycle_increment = bat_fetch_cycle_increment();
  telemetry_update_battery_cycles(cycle_increment);
#endif

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

// --- Sampling ----------------------------------------------------------------

static void pm_monitoring_timer_handler(void* context) {
  // Periodically called timer to request PMIC measurements. PMIC will call
  // pm_pmic_data_ready() callback when the measurements are ready.
  pmic_measure(pm_pmic_data_ready, NULL);
}

// PMIC measurement callback: one sample through the core
static void pm_pmic_data_ready(void* context, pmic_report_t* report) {
  pm_driver_t* drv = &g_pm;

  pm_sample_t sample = {
      .pmic = *report,
      .wireless_connected = false,
  };

#ifdef USE_WIRELESS_CHARGER
  stwlc38_get_report(&drv->wireless_data);
  sample.wireless_connected = drv->wireless_data.vout_ready;
#endif

#ifdef USE_TELEMETRY
  // Update telemetry with the current battery temperature
  if (report->ntc_present && !report->ntc_disconnected) {
    telemetry_update_battery_temp(report->ntc_temp);
  }
#endif

  pm_actions_t actions;
  pm_core_sample(&drv->core, &sample, systick_ms(), &actions);
  pm_apply_actions(drv, &actions);

  if (actions.sample_complete) {
    pm_store_data_to_backup_ram();

    if (drv->suspending) {
#ifdef USE_RTC
      // Schedule auto-hibernation rtc event
      pm_schedule_rtc_wakeup();
#endif
      drv->suspending = false;
      drv->suspended = true;
    }
  }
}

// Carries out what the core decided. Called with the lock held, or from the
// sampling callback.
static void pm_apply_actions(pm_driver_t* drv, const pm_actions_t* actions) {
  (void)drv;

  if (actions->power_source_changed) {
    notify_send(NOTIFY_POWER_STATUS_CHANGE);
  }

  pm_charging_apply(actions);

  if (actions->set_backlight) {
    backlight_set_max_level(actions->backlight_level);
  }

  if (actions->enter_shipmode) {
    pmic_enter_shipmode();
  }

  if (actions->power_off) {
    // Store power manager data with request to hibernate, power manager
    // will try to hibernate immediately after reboot.
    pm_store_data_to_backup_ram();
    reboot_to_off();
  }
}

// --- Suspend / resume of the driver itself -----------------------------------

bool pm_driver_suspend(void) {
  pm_driver_t* drv = &g_pm;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();

  if (drv->core.woke_up_from_suspend) {
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

  // Suspend the sub-drivers owned by the power manager.
  pmic_suspend();
#ifdef USE_WIRELESS_CHARGER
  stwlc38_suspend();
#endif

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

bool pm_driver_resume(void) {
  // Resume the sub-drivers owned by the power manager.
#ifdef USE_WIRELESS_CHARGER
  stwlc38_resume();
#endif
  pmic_resume();

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

  // Time spent suspended, for the gauge's drain compensation
  uint32_t time_in_suspend_s = 0;
#ifdef USE_RTC
  uint32_t rtc_timestamp;
  rtc_get_timestamp(&rtc_timestamp);
  time_in_suspend_s = rtc_timestamp - drv->last_active_timestamp;
#endif
  pm_core_resume(&drv->core, time_in_suspend_s);

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

  // The power manager is only fully suspended once its sub-drivers are too.
  suspended = suspended && pmic_is_suspended();
#ifdef USE_WIRELESS_CHARGER
  suspended = suspended && stwlc38_is_suspended();
#endif

  return suspended;
}

static pm_status_t pm_wait_to_stabilize(pm_driver_t* drv, uint32_t timeout_ms) {
  uint32_t expire_time = ticks_timeout(timeout_ms);

  // Poll until the fuel gauge is initialized and the first PMIC & WLC
  // measurements have gone through the core.
  bool stabilized;
  do {
    if (ticks_expired(expire_time)) {
      return PM_TIMEOUT;
    }

    irq_key_t irq_key = irq_lock();
    stabilized = drv->core.stabilized;
    irq_unlock(irq_key);
  } while (!stabilized);

  return PM_OK;
}

#endif  // KERNEL_MODE
