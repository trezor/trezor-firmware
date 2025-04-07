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

#include <sys/irq.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <trezor_rtl.h>

#include "power_manager_internal.h"

// Global driver instance
power_manager_driver_t g_power_manager = {
    .initialized = false,
};

// State name string table
const char* const power_manager_state_names[POWER_MANAGER_STATE_COUNT] = {
#define POWER_MANAGER_STATE_STRING(state) #state,
    POWER_MANAGER_STATE_LIST(POWER_MANAGER_STATE_STRING)
#undef POWER_MANAGER_STATE_STRING
};

// Forward declarations of static functions
static void pm_monitoring_timer_handler(void* context);
static void pm_shutdown_timer_handler(void* context);

// API Implementation

power_manager_status_t power_manager_init(power_manager_state_t initial_state) {
  power_manager_driver_t* drv = &g_power_manager;

  if (drv->initialized) {
    return POWER_MANAGER_OK;
  }

  // Initialize hardware subsystems
  if (!npm1300_init() || !stwlc38_init()) {
    power_manager_deinit();
    return POWER_MANAGER_ERROR;
  }

  // Create monitoring timer
  drv->monitoring_timer = systimer_create(pm_monitoring_timer_handler, NULL);
  systimer_set_periodic(drv->monitoring_timer, POWER_MANAGER_TIMER_PERIOD_MS);

  // Create shutdown timer
  drv->shutdown_timer = systimer_create(pm_shutdown_timer_handler, NULL);

  // Initial power source measurement
  npm1300_measure(pm_pmic_data_ready, NULL);

  drv->state = initial_state;
  drv->initialized = true;
  return POWER_MANAGER_OK;
}

void power_manager_deinit(void) {
  power_manager_driver_t* drv = &g_power_manager;

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
}

power_manager_status_t power_manager_get_events(power_manager_event_t* event) {
  power_manager_driver_t* drv = &g_power_manager;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  *event = drv->event_flags;
  PM_CLEAR_ALL_EVENTS(drv->event_flags);
  irq_unlock(irq_key);

  return POWER_MANAGER_OK;
}

power_manager_status_t power_manager_get_state(power_manager_state_t* state) {
  power_manager_driver_t* drv = &g_power_manager;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  *state = drv->state;
  return POWER_MANAGER_OK;
}

const char* power_manager_get_state_name(power_manager_state_t state) {
  if (state >= POWER_MANAGER_STATE_COUNT) {
    return "UNKNOWN";
  }
  return power_manager_state_names[state];
}

power_manager_status_t power_manager_suspend(void) {
  power_manager_driver_t* drv = &g_power_manager;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  drv->request_suspend = true;
  pm_process_state_machine();
  irq_unlock(irq_key);

  if (drv->state != POWER_MANAGER_STATE_SUSPEND) {
    return POWER_MANAGER_REQUEST_REJECTED;
  }

  return POWER_MANAGER_OK;
}

power_manager_status_t power_manager_hibernate(void) {
  power_manager_driver_t* drv = &g_power_manager;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  drv->request_hibernate = true;
  pm_process_state_machine();

  if (drv->state != POWER_MANAGER_STATE_HIBERNATE) {
    return POWER_MANAGER_REQUEST_REJECTED;
  }

  return POWER_MANAGER_OK;
}

power_manager_status_t power_manager_turn_on(void) {
  power_manager_driver_t* drv = &g_power_manager;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  drv->request_turn_on = true;
  pm_process_state_machine();

  if (drv->state == POWER_MANAGER_STATE_HIBERNATE ||
      drv->state == POWER_MANAGER_STATE_CHARGING) {
    return POWER_MANAGER_REQUEST_REJECTED;
  }

  return POWER_MANAGER_OK;
}

power_manager_status_t power_manager_get_report(
    power_manager_report_t* report) {
  power_manager_driver_t* drv = &g_power_manager;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();

  // Copy current data into report
  report->usb_connected = drv->usb_connected;
  report->wireless_charger_connected = drv->wireless_connected;
  report->system_voltage_v = drv->pmic_data.vsys;
  report->battery_voltage_v = drv->pmic_data.vbat;
  report->battery_current_ma = drv->pmic_data.ibat;
  report->battery_temp_c = drv->pmic_data.ntc_temp;
  report->pmic_temp_c = drv->pmic_data.die_temp;
  report->wireless_rectifier_voltage_v = drv->wireless_data.vrect;
  report->wireless_output_voltage_v = drv->wireless_data.vout;
  report->wireless_current_ma = drv->wireless_data.icur;
  report->wireless_temp_c = drv->wireless_data.tmeas;

  irq_unlock(irq_key);

  return POWER_MANAGER_OK;
}

// Timer handlers

static void pm_monitoring_timer_handler(void* context) {
  pm_monitor_power_sources();
}

static void pm_shutdown_timer_handler(void* context) {
  power_manager_driver_t* drv = &g_power_manager;
  drv->shutdown_timer_elapsed = true;
  pm_process_state_machine();
}
