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
  // Last state
  pm_state_t last_state;
  // Pending events
  pm_event_t events;

  // Jump detection state for battery temperature
  float temp_anchor;
  uint32_t t_temp_anchor_ms;

  // Jump detection state for battery open-circuit voltage (OCV)
  float ocv_anchor;
  uint32_t t_ocv_anchor_ms;

} pm_fsm_t;

// State machine for each task
static pm_fsm_t g_pm_tls[SYSTASK_MAX_TASKS] = {0};

// Forward declarations
static const syshandle_vmt_t g_pm_handle_vmt;

bool pm_poll_init(void) {
  return syshandle_register(SYSHANDLE_POWER_MANAGER, &g_pm_handle_vmt, NULL);
}

void pm_poll_deinit(void) { syshandle_unregister(SYSHANDLE_POWER_MANAGER); }

bool pm_get_events(pm_event_t* events) {
  pm_fsm_t* fsm = &g_pm_tls[systask_id(systask_active())];

  if (fsm->events.all != 0) {
    *events = fsm->events;
    memset(&fsm->events, 0, sizeof(pm_event_t));
    return true;
  }

  return false;
}

static bool pm_fsm_update(pm_fsm_t* fsm, pm_state_t* new_state) {
  // Return true if there are any state changes
  if (new_state->soc != fsm->last_state.soc) {
    fsm->events.flags.soc_updated = true;
  }

  // Detect battery temperature jump
  {
    const uint32_t now = systick_ms();

    if (fsm->t_temp_anchor_ms == 0U) {
      fsm->temp_anchor = new_state->battery_temp;
      fsm->t_temp_anchor_ms = now;
    }

    float delta = new_state->battery_temp - fsm->temp_anchor;
    if (delta < 0.0f) {
      delta = -delta;
    }

    const uint32_t elapsed = now - fsm->t_temp_anchor_ms;
    const float TEMP_JUMP_THRESHOLD_C = 5.0f;
    const uint32_t TEMP_JUMP_WINDOW_MS = 5000;  // 5 seconds

    bool within_window = (elapsed <= TEMP_JUMP_WINDOW_MS);
    bool over_threshold = (delta >= TEMP_JUMP_THRESHOLD_C);

    if (within_window && over_threshold) {
      fsm->events.flags.battery_temp_jump_detected = true;
      // Reset anchor to new value to avoid cascading triggers
      fsm->temp_anchor = new_state->battery_temp;
      fsm->t_temp_anchor_ms = now;
    } else if (!within_window) {
      // Slide the anchor window forward
      fsm->temp_anchor = new_state->battery_temp;
      fsm->t_temp_anchor_ms = now;
    }
  }

  // Detect battery OCV jump
  {
    const uint32_t now = systick_ms();

    if (fsm->t_ocv_anchor_ms == 0U) {
      fsm->ocv_anchor = new_state->battery_ocv;
      fsm->t_ocv_anchor_ms = now;
    }

    float delta = new_state->battery_ocv - fsm->ocv_anchor;
    if (delta < 0.0f) {
      delta = -delta;
    }

    const uint32_t elapsed = now - fsm->t_ocv_anchor_ms;
    const float OCV_JUMP_THRESHOLD_V = 0.50f;  // 500 mV
    const uint32_t OCV_JUMP_WINDOW_MS = 5000;  // 5 seconds

    bool within_window = (elapsed <= OCV_JUMP_WINDOW_MS);
    bool over_threshold = (delta >= OCV_JUMP_THRESHOLD_V);

    if (within_window && over_threshold) {
      fsm->events.flags.battery_ocv_jump_detected = true;
      // Reset anchor to new value to avoid cascading triggers
      fsm->ocv_anchor = new_state->battery_ocv;
      fsm->t_ocv_anchor_ms = now;
    } else if (!within_window) {
      // Slide the anchor window forward
      fsm->ocv_anchor = new_state->battery_ocv;
      fsm->t_ocv_anchor_ms = now;
    }
  }

  if (new_state->usb_connected != fsm->last_state.usb_connected) {
    fsm->events.flags.usb_connected_changed = true;
  }

  if (new_state->wireless_connected != fsm->last_state.wireless_connected) {
    fsm->events.flags.wireless_connected_changed = true;
  }

  if (new_state->power_status != fsm->last_state.power_status) {
    fsm->events.flags.power_status_changed = true;
  }

  if (new_state->charging_status != fsm->last_state.charging_status) {
    fsm->events.flags.charging_status_changed = true;
  }

  if (new_state->ntc_connected != fsm->last_state.ntc_connected) {
    fsm->events.flags.ntc_connected_changed = true;
  }

  if (new_state->charging_limited != fsm->last_state.charging_limited) {
    fsm->events.flags.charging_limited_changed = true;
  }

  fsm->last_state = *new_state;

  return fsm->events.all != 0;
}

static void on_task_created(void* context, systask_id_t task_id) {
  pm_fsm_t* fsm = &g_pm_tls[task_id];
  memset(fsm, 0, sizeof(pm_fsm_t));
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
  pm_fsm_t* fsm = &g_pm_tls[task_id];

  pm_state_t* new_state = (pm_state_t*)param;

  return pm_fsm_update(fsm, new_state);
}

static const syshandle_vmt_t g_pm_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL_MODE
