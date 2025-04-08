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

#include <sys/systick.h>
#include <sys/systimer.h>

#include "../../powerctl/npm1300/npm1300.h"
#include "power_manager_internal.h"

// State handler lookup table
static const power_manager_state_handler_t state_handlers[] = {
    [POWER_MANAGER_STATE_ACTIVE] =
        {
            .enter = NULL,
            .handle = pm_handle_state_active,
            .exit = NULL,
        },
    [POWER_MANAGER_STATE_POWER_SAVE] =
        {
            .enter = NULL,
            .handle = pm_handle_state_power_save,
            .exit = NULL,
        },
    [POWER_MANAGER_STATE_ULTRA_POWER_SAVE] =
        {
            .enter = NULL,
            .handle = pm_handle_state_ultra_power_save,
            .exit = NULL,
        },
    [POWER_MANAGER_STATE_SHUTTING_DOWN] =
        {
            .enter = pm_enter_shutting_down,
            .handle = pm_handle_state_shutting_down,
            .exit = pm_exit_shutting_down,
        },
    [POWER_MANAGER_STATE_SUSPEND] =
        {
            .enter = pm_enter_suspend,
            .handle = pm_handle_state_suspend,
            .exit = NULL,
        },
    [POWER_MANAGER_STATE_CHARGING] =
        {
            .enter = NULL,
            .handle = pm_handle_state_charging,
            .exit = NULL,
        },
    [POWER_MANAGER_STATE_HIBERNATE] =
        {
            .enter = pm_enter_hibernate,
            .handle = pm_handle_state_hibernate,
            .exit = NULL,
        },
};

void pm_process_state_machine(void) {
  power_manager_driver_t* drv = &g_power_manager;
  power_manager_state_t old_state = drv->state;

  // Get next state from current state's handler
  power_manager_state_t new_state = state_handlers[old_state].handle(drv);

  // Handle state transition if needed
  if (new_state != old_state) {
    // Exit old state
    if (state_handlers[old_state].exit != NULL) {
      state_handlers[old_state].exit(drv);
    }

    // Update state
    drv->state = new_state;
    PM_SET_EVENT(drv->event_flags, POWER_MANAGER_EVENT_STATE_CHANGED);

    // Enter new state
    if (state_handlers[new_state].enter != NULL) {
      state_handlers[new_state].enter(drv);
    }

    // Process state machine again as new state might trigger another transition
    pm_process_state_machine();
  }
}

// State handler implementations

power_manager_state_t pm_handle_state_active(power_manager_driver_t* drv) {
  // Handle hibernate request
  if (drv->request_hibernate) {
    drv->request_hibernate = false;

    if (drv->usb_connected || drv->wireless_connected) {
      return POWER_MANAGER_STATE_CHARGING;
    }

    return POWER_MANAGER_STATE_HIBERNATE;
  }

  // Handle suspend request
  if (drv->request_suspend) {
    drv->request_suspend = false;

    if (drv->usb_connected || drv->wireless_connected) {
      return POWER_MANAGER_STATE_CHARGING;
    }

    return POWER_MANAGER_STATE_SUSPEND;
  }

  // Handle low battery with no external power
  if (!drv->usb_connected && drv->battery_low) {
    return POWER_MANAGER_STATE_POWER_SAVE;
  }

  return drv->state;
}

power_manager_state_t pm_handle_state_power_save(power_manager_driver_t* drv) {
  // Handle hibernate request
  if (drv->request_hibernate) {
    drv->request_hibernate = false;

    if (drv->usb_connected || drv->wireless_connected) {
      return POWER_MANAGER_STATE_CHARGING;
    }

    return POWER_MANAGER_STATE_HIBERNATE;
  }

  // Handle suspend request
  if (drv->request_suspend) {
    drv->request_suspend = false;

    if (drv->usb_connected || drv->wireless_connected) {
      return POWER_MANAGER_STATE_CHARGING;
    }

    return POWER_MANAGER_STATE_SUSPEND;
  }

  // Return to active if external power or battery recovered
  if (drv->usb_connected || !drv->battery_low) {
    return POWER_MANAGER_STATE_ACTIVE;
  }

  // Go to shutdown if battery critical
  if (!drv->usb_connected && drv->battery_critical) {
    return POWER_MANAGER_STATE_SHUTTING_DOWN;
  }

  return drv->state;
}

power_manager_state_t pm_handle_state_ultra_power_save(
    power_manager_driver_t* drv) {
  // Go to power save if external power or battery above critical
  if (drv->usb_connected || !drv->battery_critical) {
    return POWER_MANAGER_STATE_POWER_SAVE;
  }

  return drv->state;
}

power_manager_state_t pm_handle_state_shutting_down(
    power_manager_driver_t* drv) {
  // Return to power save if external power or battery recovered
  if (drv->usb_connected || !drv->battery_critical) {
    return POWER_MANAGER_STATE_POWER_SAVE;
  }

  // Enter hibernate when shutdown timer elapses
  if (drv->shutdown_timer_elapsed) {
    return POWER_MANAGER_STATE_HIBERNATE;
  }

  return drv->state;
}

power_manager_state_t pm_handle_state_suspend(power_manager_driver_t* drv) {
  // Not implemented yet
  return drv->state;
}

power_manager_state_t pm_handle_state_charging(power_manager_driver_t* drv) {
  // Not implemented yet
  return drv->state;
}

power_manager_state_t pm_handle_state_hibernate(power_manager_driver_t* drv) {
  // Terminal state - no transitions
  return drv->state;
}

// State entry/exit actions

void pm_enter_shutting_down(power_manager_driver_t* drv) {
  // Set shutdown timer
  systimer_set(drv->shutdown_timer, POWER_MANAGER_SHUTDOWN_TIMEOUT_MS);
}

void pm_exit_shutting_down(power_manager_driver_t* drv) {
  // Stop the shutdown timer
  systimer_unset(drv->shutdown_timer);
  drv->shutdown_timer_elapsed = false;
}

void pm_enter_suspend(power_manager_driver_t* drv) {
  // Not implemented yet
}

void pm_enter_hibernate(power_manager_driver_t* drv) {
  // Put PMIC into ship mode (ultra-low power)
  npm1300_enter_shipmode();

  // Wait for power off - this should never return
  systick_delay_ms(50);
}
