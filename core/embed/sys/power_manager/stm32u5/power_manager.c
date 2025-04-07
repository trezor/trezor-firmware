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
#include <sys/powerctl.h>

#include "../../powerctl/npm1300/npm1300.h"
#include "../../powerctl/stwlc38/stwlc38.h"

#include "sys/power_manager.h"

#define POWER_MANAGER_TIMER_PERIOD_MS 1000
#define POWER_MANAGER_SHUTDOWN_TIMEOUT_MS 15000
#define POWER_MANAGER_VBAT_UVLO_TH_V 3.0f
#define POWER_MANAGER_VBAT_UVLO_TH_HIST_V 0.1f

#define PM_SET_EVENT_FLAG(flags, event) ((flags) |= (event));
#define PM_CLEAR_EVENT_FLAG(flags, event) ((flags) &= ~(event));
#define PM_CLEAR_ALL_EVENT_FLAGS(flags) ((flags) = 0x0);

// String representation of power manager states
const char* const power_manager_state_names[POWER_MANAGER_STATE_COUNT] = {
#define POWER_MANAGER_STATE_STRING(state) #state,
    POWER_MANAGER_STATE_LIST(POWER_MANAGER_STATE_STRING)
#undef POWER_MANAGER_STATE_STRING
};

typedef struct {
  bool initialized;
  power_manager_state_t state;
  power_manager_event_t event_flags;

  // npm1300 report
  npm1300_report_callback_t pmic_callback;
  uint32_t pmic_last_update_ms;
  npm1300_report_t pmic_data;

  // stwlc38 report
  stwlc38_report_t wlc_data;

  bool pmic_measurement_ready;
  // USB power source
  bool usb_connected;
  // WLC power source
  bool wlc_connected;
  // Soc < 15%
  bool battery_low;
  // Battery voltage under UVLO threshold
  bool battery_critical;
  // power mode requests
  bool reqeust_suspend;
  bool request_hibernate;

  bool shutdown_timer_elapsed;

  // Power manager systimer handle
  systimer_t* monitoring_timer;
  systimer_t* shutdown_timer;
} power_manager_driver_t;

typedef struct {
  void (*enter)(power_manager_driver_t* drv);
  power_manager_state_t (*handle)(power_manager_driver_t* drv);
  void (*exit)(power_manager_driver_t *drv);
} power_manager_state_handler_t;

power_manager_driver_t g_power_manager_driver = {
    .initialized = false,
    .state = POWER_MANAGER_STATE_ULTRA_POWER_SAVE,
};

static void pm_shutdown_timer_handler(void* context);
static void pm_monitoring_timer_handler(void* context);
static void pm_process_state_machine();
static void pmic_callback(void* context, npm1300_report_t* report);

power_manager_state_t pm_state_active_handle(power_manager_driver_t* drv) {
  if (drv->request_hibernate) {
    drv->request_hibernate = false;

    if (drv->usb_connected || drv->wlc_connected) {
      return POWER_MANAGER_STATE_CHARGING;
    }

    return POWER_MANAGER_STATE_HIBERNATE;
  }

  if (drv->reqeust_suspend) {
    drv->reqeust_suspend = false;

    if (drv->usb_connected || drv->wlc_connected) {
      return POWER_MANAGER_STATE_CHARGING;
    }

    return POWER_MANAGER_STATE_SUSPEND;
  }

  if (!drv->usb_connected && drv->battery_low) {
    return POWER_MANAGER_STATE_POWER_SAVE;
  }

  return drv->state;

}

power_manager_state_t pm_state_power_save_handle(power_manager_driver_t* drv) {
  if (drv->request_hibernate) {
    drv->request_hibernate = false;

    if (drv->usb_connected || drv->wlc_connected) {
      return POWER_MANAGER_STATE_CHARGING;
    }

    return POWER_MANAGER_STATE_HIBERNATE;
  }

  if (drv->reqeust_suspend) {
    drv->reqeust_suspend = false;

    if (drv->usb_connected || drv->wlc_connected) {
      return POWER_MANAGER_STATE_CHARGING;
    }

    return POWER_MANAGER_STATE_SUSPEND;
  }

  if (drv->usb_connected || !drv->battery_low) {
    return POWER_MANAGER_STATE_ACTIVE;
  }

  if (!drv->usb_connected && drv->battery_critical) {
    return POWER_MANAGER_STATE_SHUTTING_DOWN;
  }

  return drv->state;
}

power_manager_state_t pm_state_ultra_power_save_handle(
    power_manager_driver_t* drv) {

  if (drv->usb_connected || !drv->battery_critical) {
    return POWER_MANAGER_STATE_POWER_SAVE;
  }

  return drv->state;
}

void pm_entry_shutting_down_handle(power_manager_driver_t* drv) {
  // Set the shutdown timer
  systimer_set(drv->shutdown_timer, POWER_MANAGER_SHUTDOWN_TIMEOUT_MS);
}

power_manager_state_t pm_state_shutting_down_handle(
    power_manager_driver_t* drv) {

  if(drv->usb_connected || !drv->battery_critical) {
    return POWER_MANAGER_STATE_POWER_SAVE;
  }

  if(drv->shutdown_timer_elapsed){
    return POWER_MANAGER_STATE_HIBERNATE;
  }

  return drv->state;
}

void pm_exit_shutting_down_handle(power_manager_driver_t* drv) {
  // Stop the shutdown timer
  systimer_unset(drv->shutdown_timer);
  drv->shutdown_timer_elapsed = false;
}

power_manager_state_t pm_state_charging_handle(power_manager_driver_t* drv) {
  // Not implemented yet
  return drv->state;
}

void pm_entry_suspend_handle(power_manager_driver_t* drv) {
  // Not implemented yet
  return;
}

power_manager_state_t pm_state_suspend_handle(power_manager_driver_t* drv) {
  // Not implemented yet
  return drv->state;
}

void pm_entry_hibernate_handle(power_manager_driver_t* drv) {

  if (!npm1300_enter_shipmode()) {
  }

  // Wait for the device to power off
  systick_delay_ms(50);

}

power_manager_state_t pm_state_hibernate_handle(power_manager_driver_t* drv) {
  return drv->state;
}

// ~IMPORTANT NOTE~
// State handlers will fully define STM bahavior, and might be perfect place
// where to use linker to split function for bootloader and firmware.
// bootloader will be probably a subset of states used in firmware, so some
// handlers might be used for both cases.

static const power_manager_state_handler_t state_handlers[] = {
    [POWER_MANAGER_STATE_ACTIVE] = {.enter = NULL,
                                    .handle = pm_state_active_handle},
    [POWER_MANAGER_STATE_POWER_SAVE] =
        {
            .enter = NULL,
            .handle = pm_state_power_save_handle,
            .exit = NULL,
        },
    [POWER_MANAGER_STATE_ULTRA_POWER_SAVE] =
        {
            .enter = NULL,
            .handle = pm_state_ultra_power_save_handle,
            .exit = NULL,
        },
    [POWER_MANAGER_STATE_SHUTTING_DOWN] =
        {
            .enter = pm_entry_shutting_down_handle,
            .handle = pm_state_shutting_down_handle,
            .exit = pm_exit_shutting_down_handle,
        },
    [POWER_MANAGER_STATE_CHARGING] =
        {
            .enter = NULL,
            .handle = pm_state_charging_handle,
            .exit = NULL,
        },
    [POWER_MANAGER_STATE_SUSPEND] =
        {
            .enter = pm_entry_suspend_handle,
            .handle = pm_state_suspend_handle,
            .exit = NULL,
        },
    [POWER_MANAGER_STATE_HIBERNATE] =
        {
            .enter = pm_entry_hibernate_handle,
            .handle = pm_state_hibernate_handle,
            .exit = NULL,
        },
};

power_manager_status_t power_manager_init(void) {
  power_manager_driver_t* drv = &g_power_manager_driver;

  if (drv->initialized) {
    return POWER_MANAGER_OK;
  }

  // Initialize PMIC driver
  if (!npm1300_init()) {
    goto cleanup;
  }

  // Initialize WLC
  if (!stwlc38_init()) {
    goto cleanup;
  }

  // Initialize Fuel Gauge

  // - Readout state of charge from retained memory

  // Initialize power manager timer
  drv->monitoring_timer = systimer_create(pm_monitoring_timer_handler, NULL);
  systimer_set_periodic(drv->monitoring_timer, POWER_MANAGER_TIMER_PERIOD_MS);

  // Initialize suspend timer
  drv->shutdown_timer = systimer_create(pm_shutdown_timer_handler, NULL);

  drv->initialized = true;

  return POWER_MANAGER_OK;

cleanup:
  power_manager_deinit();
  return POWER_MANAGER_ERROR;
}

void power_manager_deinit(void) {
  power_manager_driver_t* drv = &g_power_manager_driver;

  // Deinitialize PMIC driver
  npm1300_deinit();

  // Deinitialize WLC
  stwlc38_deinit();

  // Deinitialize Fuel Gauge
  // Store the SoC into the retained memory

  // Deinitialize power manager timer
  systimer_delete(drv->monitoring_timer);

  return;
}

static void pm_monitoring_timer_handler(void* context) {
  power_manager_driver_t* drv = &g_power_manager_driver;

  // Run Fuel gauge
  // ..... HERE .....

  // Check USB power source
  if (drv->pmic_data.usb_status != 0x0) {
    if (!drv->usb_connected) {
      drv->usb_connected = true;
      PM_SET_EVENT_FLAG(drv->event_flags, POWER_MANAGER_USB_CONNECTED);
    }
  } else {
    if (drv->usb_connected) {
      drv->usb_connected = false;
      PM_SET_EVENT_FLAG(drv->event_flags, POWER_MANAGER_USB_DISCONNECTED);
    }
  }

  // Check WLC power source
  if(drv->wlc_data.vout_ready){
    if(!drv->wlc_connected){
      drv->wlc_connected = true;
      PM_SET_EVENT_FLAG(drv->event_flags, POWER_MANAGER_WLC_CONNECTED);
    }
  }else{
    if(drv->wlc_connected){
      drv->wlc_connected = false;
      PM_SET_EVENT_FLAG(drv->event_flags, POWER_MANAGER_WLC_DISCONNECTED);
    }
  }

  // Check Battery voltage
  if ((drv->pmic_data.vbat < POWER_MANAGER_VBAT_UVLO_TH_V) &&
      !drv->battery_critical) {
    drv->battery_critical = true;
  } else if (drv->pmic_data.vbat > (POWER_MANAGER_VBAT_UVLO_TH_V +
                                    POWER_MANAGER_VBAT_UVLO_TH_HIST_V) &&
             drv->battery_critical) {
    drv->battery_critical = false;
  }

  // Check low battery state
  // WARNINIG: This shall be replaced for SOC, which do not require threshold
  if (drv->pmic_data.vbat < 3.2f && !drv->battery_low) {
    drv->battery_low = true;
  } else if (drv->pmic_data.vbat > 3.3f && drv->battery_low) {
    drv->battery_low = false;
  }

  // Request PMIC measurement
  npm1300_measure(pmic_callback, NULL);
  drv->pmic_measurement_ready = false;

  pm_process_state_machine();

}


static void pm_shutdown_timer_handler(void* context){

  power_manager_driver_t* drv = &g_power_manager_driver;

  // Stop the shutdown timer
  systimer_delete(drv->shutdown_timer);
  drv->shutdown_timer = NULL;

  // Shutdown the device
  npm1300_enter_shipmode();


}

static void pm_process_state_machine() {
  power_manager_driver_t* drv = &g_power_manager_driver;
  power_manager_state_t old_state = drv->state;

  power_manager_state_t new_state = state_handlers[old_state].handle(drv);
  bool state_changed = false;

  if (new_state != old_state) {

    if(state_handlers[old_state].exit != NULL) {
      state_handlers[old_state].exit(drv);
    }

    drv->state = new_state;
    state_changed = true;
    PM_SET_EVENT_FLAG(drv->event_flags, POWER_MANAGER_STATE_CHANGED);

    if (state_handlers[new_state].enter != NULL) {
      state_handlers[new_state].enter(drv);
    }

  }

  if (state_changed) {
    pm_process_state_machine();
  }
}

static void pmic_callback(void* context, npm1300_report_t* report) {
  power_manager_driver_t* drv = &g_power_manager_driver;

  drv->pmic_last_update_ms = systick_ms();
  memcpy(&drv->pmic_data, report, sizeof(npm1300_report_t));

  if(!stwlc38_get_report(&drv->wlc_data)) {
    // Cannot read data from STWLC38
    PM_SET_EVENT_FLAG(drv->event_flags, POWER_MANAGER_ERROR);
  }

  drv->pmic_measurement_ready = true;
}

power_manager_status_t power_manager_get_events(
    power_manager_event_t* event_flags) {
  power_manager_driver_t* drv = &g_power_manager_driver;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  *event_flags = drv->event_flags;
  PM_CLEAR_ALL_EVENT_FLAGS(drv->event_flags)
  irq_unlock(irq_key);

  return POWER_MANAGER_OK;
}

power_manager_status_t power_manager_get_state(power_manager_state_t* state) {
  power_manager_driver_t* drv = &g_power_manager_driver;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();
  *state = drv->state;
  irq_unlock(irq_key);

  return POWER_MANAGER_OK;
}

power_manager_status_t power_manager_suspend(void) {
  power_manager_driver_t* drv = &g_power_manager_driver;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();

  drv->reqeust_suspend = true;
  pm_process_state_machine();
  irq_unlock(irq_key);

  if(drv->state != POWER_MANAGER_STATE_SUSPEND) {
    return POWER_MANAGER_REQUEST_REJECTED;
  }

  return POWER_MANAGER_OK;
}

power_manager_status_t power_manager_hibernate(void) {
  power_manager_driver_t* drv = &g_power_manager_driver;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();

  drv->request_hibernate = true;
  pm_process_state_machine();

  irq_unlock(irq_key);

  if(drv->state != POWER_MANAGER_STATE_HIBERNATE) {
    return POWER_MANAGER_REQUEST_REJECTED;
  }

  return POWER_MANAGER_OK;
}
// Helper function to get state name
const char* power_manager_get_state_name(power_manager_state_t state) {
  if (state >= POWER_MANAGER_STATE_COUNT) {
    return "UNKNOWN";
  }
  return power_manager_state_names[state];
}

power_manager_status_t power_manager_get_report(
    power_manager_report_t* report) {
  power_manager_driver_t* drv = &g_power_manager_driver;

  if (!drv->initialized) {
    return POWER_MANAGER_NOT_INITIALIZED;
  }

  irq_key_t irq_key = irq_lock();

  report->usb_connected = drv->usb_connected;
  report->wlc_connected = drv->wlc_connected;
  report->vsys_voltage_V = drv->pmic_data.vsys;
  report->battery_voltage_V = drv->pmic_data.vbat;
  report->battery_current_mA = drv->pmic_data.ibat;
  report->battery_temp_deg = drv->pmic_data.ntc_temp;
  report->pmic_die_temp_deg = drv->pmic_data.die_temp;
  report->wlc_vrect_V = drv->wlc_data.vrect;
  report->wlc_vout_V = drv->wlc_data.vout;
  report->wlc_current_mA = drv->wlc_data.icur;
  report->wlc_die_temp_deg = drv->wlc_data.tmeas;

  irq_unlock(irq_key);

  return POWER_MANAGER_OK;
}