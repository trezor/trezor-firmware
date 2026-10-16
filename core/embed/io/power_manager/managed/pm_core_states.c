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

#include "pm_core.h"

// The power state machine. Handlers decide the next state from the core's
// inputs; enter/exit hooks only record what the glue must do in `actions`.

typedef struct {
  void (*enter)(pm_core_t* core, pm_actions_t* actions);
  pm_power_status_t (*handle)(pm_core_t* core, pm_actions_t* actions);
  void (*exit)(pm_core_t* core, pm_actions_t* actions);
} pm_state_handler_t;

static pm_power_status_t pm_handle_state_active(pm_core_t* core,
                                                pm_actions_t* actions);
static pm_power_status_t pm_handle_state_power_save(pm_core_t* core,
                                                    pm_actions_t* actions);
static pm_power_status_t pm_handle_state_shutting_down(pm_core_t* core,
                                                       pm_actions_t* actions);
static pm_power_status_t pm_handle_state_suspend(pm_core_t* core,
                                                 pm_actions_t* actions);
static pm_power_status_t pm_handle_state_hibernate(pm_core_t* core,
                                                   pm_actions_t* actions);
static pm_power_status_t pm_handle_state_charging(pm_core_t* core,
                                                  pm_actions_t* actions);

static void pm_enter_hibernate(pm_core_t* core, pm_actions_t* actions);
static void pm_enter_shutting_down(pm_core_t* core, pm_actions_t* actions);
static void pm_enter_power_save(pm_core_t* core, pm_actions_t* actions);
static void pm_enter_active(pm_core_t* core, pm_actions_t* actions);

// State handler lookup table.
//
// The table is complete for every build: the state machine is product
// behaviour, not chip behaviour, and it is the same on every board. A board
// whose PMIC has no charger never reports an external power source, so
// PM_STATE_CHARGING is simply unreachable there - no build-time hole needed.
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
            .exit = NULL,
        },
    [PM_STATE_SUSPEND] =
        {
            .enter = NULL,
            .handle = pm_handle_state_suspend,
            .exit = NULL,
        },
    [PM_STATE_CHARGING] =
        {
            .enter = NULL,
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

void pm_core_run_state_machine(pm_core_t* core, uint32_t now_ms,
                               pm_actions_t* actions) {
  core->now_ms = now_ms;

  // Loop until the state machine converges to a stable state
  while (true) {
    pm_power_status_t old_state = core->state;
    pm_power_status_t new_state =
        state_handlers[old_state].handle(core, actions);

    if (new_state == old_state) {
      break;
    }

    if (state_handlers[old_state].exit != NULL) {
      state_handlers[old_state].exit(core, actions);
    }

    core->state = new_state;

    if (state_handlers[new_state].enter != NULL) {
      state_handlers[new_state].enter(core, actions);
    }
  }
}

// State handler implementations

static pm_power_status_t pm_handle_state_hibernate(pm_core_t* core,
                                                   pm_actions_t* actions) {
  if (core->request_turn_on) {
    core->request_turn_on = false;
    return PM_STATE_POWER_SAVE;
  }

  // External power source, start charging
  if (core->usb_connected || core->wireless_connected) {
    return PM_STATE_CHARGING;
  }

  // Hibernate again
  if (core->request_hibernate) {
    core->request_hibernate = false;

    // Put PMIC into ship mode (ultra-low power)
    actions->enter_shipmode = true;
    return PM_STATE_HIBERNATE;
  }

  return core->state;
}

static pm_power_status_t pm_handle_state_charging(pm_core_t* core,
                                                  pm_actions_t* actions) {
  (void)actions;

  if (core->request_turn_on) {
    core->request_turn_on = false;
    return PM_STATE_POWER_SAVE;
  }

  // Go back to hibernate if external power was removed.
  if (!core->usb_connected && !core->wireless_connected) {
    return PM_STATE_HIBERNATE;
  }

  // Hibernate again
  if (core->request_hibernate) {
    core->request_hibernate = false;

    // Device is charging, request is rejected with no action
    return PM_STATE_CHARGING;
  }

  return core->state;
}

static pm_power_status_t pm_handle_state_suspend(pm_core_t* core,
                                                 pm_actions_t* actions) {
  (void)actions;

  if (core->request_hibernate) {
    core->request_hibernate = false;
    return PM_STATE_HIBERNATE;
  }

  if (core->request_exit_suspend) {
    core->request_exit_suspend = false;
    return PM_STATE_POWER_SAVE;
  }

  return core->state;
}

static pm_power_status_t pm_handle_state_shutting_down(pm_core_t* core,
                                                       pm_actions_t* actions) {
  (void)actions;

  // System is shutting down, but user can still hibernate the device early.
  if (core->request_hibernate) {
    core->request_hibernate = false;
    return PM_STATE_HIBERNATE;
  }

  if (core->request_suspend) {
    core->request_suspend = false;
    return PM_STATE_SUSPEND;
  }

  // Return to power save if external power or battery recovered
  if (core->usb_connected || !core->battery_critical) {
    return PM_STATE_POWER_SAVE;
  }

  // Enter hibernate when the shutdown timeout elapses
  if (pm_core_deadline_passed(core->now_ms, core->shutdown_deadline_ms)) {
    return PM_STATE_HIBERNATE;
  }

  return core->state;
}

static pm_power_status_t pm_handle_state_power_save(pm_core_t* core,
                                                    pm_actions_t* actions) {
  (void)actions;

  // Handle hibernate request
  if (core->request_hibernate) {
    core->request_hibernate = false;
    return PM_STATE_HIBERNATE;
  }

  // Handle suspend request
  if (core->request_suspend) {
    core->request_suspend = false;
    return PM_STATE_SUSPEND;
  }

  // Return to active if external power or battery recovered
  if (core->usb_connected || !core->battery_low) {
    return PM_STATE_ACTIVE;
  }

  // Go to shutdown if battery critical
  if (!core->usb_connected && core->battery_critical) {
    return PM_STATE_SHUTTING_DOWN;
  }

  return core->state;
}

static pm_power_status_t pm_handle_state_active(pm_core_t* core,
                                                pm_actions_t* actions) {
  (void)actions;

  // Handle hibernate request
  if (core->request_hibernate) {
    core->request_hibernate = false;
    return PM_STATE_HIBERNATE;
  }

  // Handle suspend request
  if (core->request_suspend) {
    core->request_suspend = false;
    return PM_STATE_SUSPEND;
  }

  // Handle low battery with no external power
  if (!core->usb_connected && core->battery_low) {
    return PM_STATE_POWER_SAVE;
  }

  return core->state;
}

// State enter actions

static void pm_enter_hibernate(pm_core_t* core, pm_actions_t* actions) {
  (void)core;
  // The glue persists the recovery data and powers the device off; after the
  // reboot the power manager tries to hibernate immediately.
  actions->power_off = true;
}

static void pm_enter_shutting_down(pm_core_t* core, pm_actions_t* actions) {
  (void)actions;
  core->shutdown_deadline_ms = core->now_ms + PM_SHUTDOWN_TIMEOUT_MS;
}

static void pm_enter_power_save(pm_core_t* core, pm_actions_t* actions) {
  actions->set_backlight = true;
  actions->backlight_level = core->cfg.power_save_backlight;
}

static void pm_enter_active(pm_core_t* core, pm_actions_t* actions) {
  (void)core;
  actions->set_backlight = true;
  actions->backlight_level = 255;  // unlimited
}

#endif  // KERNEL_MODE
