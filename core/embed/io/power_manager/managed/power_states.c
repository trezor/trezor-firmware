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

#include <io/backlight.h>
#include <io/pmic.h>
#include <sys/bootutils.h>
#include <sys/systick.h>
#include <sys/systimer.h>

#include "power_manager_internal.h"

// Power manager internal state machine handlers and entry/exit funtions
static pm_power_status_t pm_handle_state_active(pm_driver_t* drv);
static pm_power_status_t pm_handle_state_power_save(pm_driver_t* drv);
static pm_power_status_t pm_handle_state_shutting_down(pm_driver_t* drv);
static pm_power_status_t pm_handle_state_suspend(pm_driver_t* drv);
static pm_power_status_t pm_handle_state_charging(pm_driver_t* drv);
static pm_power_status_t pm_handle_state_hibernate(pm_driver_t* drv);

static void pm_enter_hibernate(pm_driver_t* drv);
static void pm_enter_charging(pm_driver_t* drv);
static void pm_enter_shutting_down(pm_driver_t* drv);
static void pm_enter_power_save(pm_driver_t* drv);
static void pm_enter_active(pm_driver_t* drv);
static void pm_exit_shutting_down(pm_driver_t* drv);

// State handler lookup table
static const pm_state_handler_t state_handlers[] = {
    [PM_STATE_ACTIVE] =
        {
            .enter = pm_enter_active,
            .handle = pm_handle_state_active,
            .exit = NULL,
        },
    [PM_STATE_POWER_SAVE] =
        {
            .enter = pm_enter_power_save,
            .handle = pm_handle_state_power_save,
            .exit = NULL,
        },
    [PM_STATE_SHUTTING_DOWN] =
        {
            .enter = pm_enter_shutting_down,
            .handle = pm_handle_state_shutting_down,
            .exit = pm_exit_shutting_down,
        },
    [PM_STATE_SUSPEND] =
        {
            .enter = NULL,
            .handle = pm_handle_state_suspend,
            .exit = NULL,
        },
    [PM_STATE_CHARGING] =
        {
            .enter = pm_enter_charging,
            .handle = pm_handle_state_charging,
            .exit = NULL,
        },
    [PM_STATE_HIBERNATE] =
        {
            .enter = pm_enter_hibernate,
            .handle = pm_handle_state_hibernate,
            .exit = NULL,
        },
};

void pm_process_state_machine(void) {
  pm_driver_t* drv = &g_pm;
  pm_power_status_t old_state;
  pm_power_status_t new_state;

  // Loop until state machine converge to a stable state
  while (true) {
    // Get current state
    old_state = drv->state;

    // Call state handler to process the current state
    new_state = state_handlers[old_state].handle(drv);

    // Check if the state has changed
    if (new_state != old_state) {
      // Exit old state
      if (state_handlers[old_state].exit != NULL) {
        state_handlers[old_state].exit(drv);
      }

      // Update state
      drv->state = new_state;

      // Enter new state
      if (state_handlers[new_state].enter != NULL) {
        state_handlers[new_state].enter(drv);
      }

    } else {
      // State has not changed, exit the loop
      break;
    }
  }
}

// State handler implementations

static pm_power_status_t pm_handle_state_hibernate(pm_driver_t* drv) {
  if (drv->request_turn_on) {
    drv->request_turn_on = false;
    return PM_STATE_POWER_SAVE;
  }

  // External power source, start charging
  if (drv->usb_connected || drv->wireless_connected) {
    return PM_STATE_CHARGING;
  }

  // Hibernate again
  if (drv->request_hibernate) {
    drv->request_hibernate = false;

    // Put PMIC into ship mode (ultra-low power)
    pmic_enter_shipmode();
    return PM_STATE_HIBERNATE;
  }

  return drv->state;
}

static pm_power_status_t pm_handle_state_charging(pm_driver_t* drv) {
  if (drv->request_turn_on) {
    drv->request_turn_on = false;
    return PM_STATE_POWER_SAVE;
  }

  // Go back to hibernate if external power was removed.
  if (!drv->usb_connected && !drv->wireless_connected) {
    return PM_STATE_HIBERNATE;
  }

  // Hibernate again
  if (drv->request_hibernate) {
    drv->request_hibernate = false;

    // Device is charging, request is rejected with no action
    return PM_STATE_CHARGING;
  }

  return drv->state;
}

static pm_power_status_t pm_handle_state_suspend(pm_driver_t* drv) {
  if (drv->request_hibernate) {
    drv->request_hibernate = false;
    return PM_STATE_HIBERNATE;
  }

  if (drv->request_exit_suspend) {
    drv->request_exit_suspend = false;
    return PM_STATE_POWER_SAVE;
  }

  return drv->state;
}

static pm_power_status_t pm_handle_state_shutting_down(pm_driver_t* drv) {
  // System is shutting down, but user can still hibernate the device early.
  if (drv->request_hibernate) {
    drv->request_hibernate = false;
    return PM_STATE_HIBERNATE;
  }

  if (drv->request_suspend) {
    drv->request_suspend = false;
    return PM_STATE_SUSPEND;
  }

  // Return to power save if external power or battery recovered
  if (drv->usb_connected || !drv->battery_critical) {
    return PM_STATE_POWER_SAVE;
  }

  // Enter hibernate when shutdown timer elapses
  if (drv->shutdown_timer_elapsed) {
    return PM_STATE_HIBERNATE;
  }

  return drv->state;
}

static pm_power_status_t pm_handle_state_power_save(pm_driver_t* drv) {
  // Handle hibernate request
  if (drv->request_hibernate) {
    drv->request_hibernate = false;
    return PM_STATE_HIBERNATE;
  }

  // Handle suspend request
  if (drv->request_suspend) {
    drv->request_suspend = false;
    return PM_STATE_SUSPEND;
  }

  // Return to active if external power or battery recovered
  if (drv->usb_connected || !drv->battery_low) {
    return PM_STATE_ACTIVE;
  }

  // Go to shutdown if battery critical
  if (!drv->usb_connected && drv->battery_critical) {
    return PM_STATE_SHUTTING_DOWN;
  }

  return drv->state;
}

static pm_power_status_t pm_handle_state_active(pm_driver_t* drv) {
  // Handle hibernate request
  if (drv->request_hibernate) {
    drv->request_hibernate = false;
    return PM_STATE_HIBERNATE;
  }

  // Handle suspend request
  if (drv->request_suspend) {
    drv->request_suspend = false;
    return PM_STATE_SUSPEND;
  }

  // Handle low battery with no external power
  if (!drv->usb_connected && drv->battery_low) {
    return PM_STATE_POWER_SAVE;
  }

  return drv->state;
}

// State enter/exit actions

static void pm_enter_hibernate(pm_driver_t* drv) {
  // Store power manager data with request to hibernate, power manager
  // will try to hibernate immediately after reboot.
  pm_store_data_to_backup_ram();
  reboot_to_off();
}

static void pm_enter_charging(pm_driver_t* drv) {}

static void pm_enter_shutting_down(pm_driver_t* drv) {
  // Set shutdown timer
  systimer_set(drv->shutdown_timer, PM_SHUTDOWN_TIMEOUT_MS);
}

static void pm_enter_power_save(pm_driver_t* drv) {
  // Limit backlight
  backlight_set_max_level(130);
}

static void pm_enter_active(pm_driver_t* drv) {
  // Set unlimited backlight
  backlight_set_max_level(255);
}

static void pm_exit_shutting_down(pm_driver_t* drv) {
  // Stop the shutdown timer
  systimer_unset(drv->shutdown_timer);
  drv->shutdown_timer_elapsed = false;
}

#endif
