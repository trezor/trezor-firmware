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

#include <sys/power_manager.h>
#include <sys/sysevent_source.h>
#include <sys/systick.h>

#include "power_manager_poll.h"

typedef struct {
  // Time (in ticks) when the tls was last updated
  uint32_t update_ticks;
  // Last state
  pm_state_t pm_state;
  // Pending events
  pm_event_t event;
  bool pending_event;

} pm_fsm_t;

// State machine for each task
static pm_fsm_t tls[SYSTASK_MAX_TASKS] = {0};

// Forward declarations
static const syshandle_vmt_t g_pm_handle_vmt;

bool pm_poll_init(void) {
  return syshandle_register(SYSHANDLE_POWER_MANAGER, &g_pm_handle_vmt, NULL);
}

void pm_poll_deinit(void) { syshandle_unregister(SYSHANDLE_POWER_MANAGER); }

void pm_fsm_clear(pm_fsm_t* fsm) { memset(fsm, 0, sizeof(pm_fsm_t)); }

static void pm_clear_state_flags(pm_fsm_t* fsm) {
  fsm->event.flags.entered_mode_active = false;
  fsm->event.flags.entered_mode_power_save = false;
  fsm->event.flags.entered_mode_shutting_down = false;
  fsm->event.flags.entered_mode_charging = false;
  fsm->event.flags.entered_mode_suspend = false;
  fsm->event.flags.entered_mode_hibernate = false;
}

bool pm_fsm_event_ready(pm_fsm_t* fsm, pm_state_t* new_state) {
  bool event_detected = false;

  // Remember state changes
  fsm->update_ticks = systick_ms();

  // Return true if there are any state changes
  if (new_state->soc != fsm->pm_state.soc) {
    fsm->event.flags.soc_updated = true;
    event_detected = true;
  }

  if (new_state->usb_connected && !fsm->pm_state.usb_connected) {
    fsm->event.flags.usb_connected = true;
    fsm->event.flags.usb_disconnected = false;
  }

  if (!new_state->usb_connected && fsm->pm_state.usb_connected) {
    fsm->event.flags.usb_disconnected = true;
    fsm->event.flags.usb_connected = false;
  }

  if (new_state->wireless_connected && !fsm->pm_state.wireless_connected) {
    fsm->event.flags.wireless_connected = true;
    fsm->event.flags.wireless_disconnected = false;
  }

  if (!new_state->wireless_connected && fsm->pm_state.wireless_connected) {
    fsm->event.flags.wireless_disconnected = true;
    fsm->event.flags.wireless_connected = false;
  }

  if (new_state->power_state == PM_STATE_ACTIVE) {
    if (fsm->pm_state.power_state != PM_STATE_ACTIVE) {
      pm_clear_state_flags(fsm);
      fsm->event.flags.entered_mode_active = true;
      event_detected = true;
    }
  } else if (new_state->power_state == PM_STATE_POWER_SAVE) {
    if (fsm->pm_state.power_state != PM_STATE_POWER_SAVE) {
      pm_clear_state_flags(fsm);
      fsm->event.flags.entered_mode_power_save = true;
      event_detected = true;
    }
  } else if (new_state->power_state == PM_STATE_SHUTTING_DOWN) {
    if (fsm->pm_state.power_state != PM_STATE_SHUTTING_DOWN) {
      pm_clear_state_flags(fsm);
      fsm->event.flags.entered_mode_shutting_down = true;
      event_detected = true;
    }
  } else if (new_state->power_state == PM_STATE_CHARGING) {
    if (fsm->pm_state.power_state != PM_STATE_CHARGING) {
      pm_clear_state_flags(fsm);
      fsm->event.flags.entered_mode_charging = true;
      event_detected = true;
    }
  } else if (new_state->power_state == PM_STATE_SUSPEND) {
    if (fsm->pm_state.power_state != PM_STATE_SUSPEND) {
      pm_clear_state_flags(fsm);
      fsm->event.flags.entered_mode_suspend = true;
      event_detected = true;
    }
  } else if (new_state->power_state == PM_STATE_HIBERNATE) {
    if (fsm->pm_state.power_state != PM_STATE_HIBERNATE) {
      pm_clear_state_flags(fsm);
      fsm->event.flags.entered_mode_hibernate = true;
      event_detected = true;
    }
  }

  if (new_state->charging_status != fsm->pm_state.charging_status) {
    fsm->event.flags.state_changed = true;
    event_detected = true;
  }

  if (event_detected) {
    fsm->pending_event = true;
  }

  memcpy(&fsm->pm_state, new_state, sizeof(pm_state_t));

  return event_detected;
}

bool pm_fsm_get_event(pm_fsm_t* fsm, pm_event_t* event) {
  if (fsm->pending_event) {
    memcpy(event, &fsm->event, sizeof(pm_event_t));
    memset(&fsm->event, 0, sizeof(pm_event_t));
    fsm->pending_event = false;
    return true;
  }

  return false;
}

static void on_task_created(void* context, systask_id_t task_id) {
  pm_fsm_t* fsm = &tls[task_id];
  pm_fsm_clear(fsm);
}

static void on_event_poll(void* context, bool read_awaited,
                          bool write_awaited) {
  UNUSED(write_awaited);

  if (read_awaited) {
    pm_state_t state = {0};
    pm_get_state(&state);
    syshandle_signal_read_ready(SYSHANDLE_POWER_MANAGER, &state);
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  pm_fsm_t* fsm = &tls[task_id];

  pm_state_t* new_state = (pm_state_t*)param;

  return pm_fsm_event_ready(fsm, new_state);
}

static const syshandle_vmt_t g_pm_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

bool pm_get_events(pm_event_t* event_flags) {
  pm_fsm_t* fsm = &tls[systask_id(systask_active())];

  return pm_fsm_get_event(fsm, event_flags);
}

#endif  // KERNEL_MODE
