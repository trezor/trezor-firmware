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

#include <sys/systask.h>
#include <sys/systick.h>

#include "button_poll.h"

#include "sys/sysevent_source.h"

#ifdef DEBUGLINK
#include "button_debug.h"
#endif

typedef struct {
  // Time of last update of pressed/released data
  uint64_t time;
  // Button presses that were detected since last get_event call
  uint32_t pressed;
  // Button releases that were detected since last get_event call
  uint32_t released;
  // State of buttons signalled to the poller
  uint32_t state;
} button_fsm_t;

static const syshandle_vmt_t g_button_handle_vmt;

// Each task has its own state machine
static button_fsm_t g_button_tls[SYSTASK_MAX_TASKS];

bool button_poll_init(void) {
  memset(g_button_tls, 0, sizeof(g_button_tls));

#ifdef DEBUGLINK
  button_debug_init();
#endif

  return syshandle_register(SYSHANDLE_BUTTON, &g_button_handle_vmt, NULL);
}

void button_poll_deinit(void) {
#ifdef DEBUGLINK
  button_debug_deinit();
#endif

  memset(g_button_tls, 0, sizeof(g_button_tls));
  syshandle_unregister(SYSHANDLE_BUTTON);
}

void button_fsm_clear(button_fsm_t* fsm) {
  memset(fsm, 0, sizeof(button_fsm_t));
}

bool button_fsm_event_ready(button_fsm_t* fsm, uint32_t new_state) {
  // Remember state changes
  fsm->pressed |= new_state & ~fsm->state;
  fsm->released |= ~new_state & fsm->state;
  fsm->time = systick_us();
  // Return true if there are any state changes
  return (fsm->pressed | fsm->released) != 0;
}

bool button_fsm_get_event(button_fsm_t* fsm, uint32_t new_state,
                          button_event_t* event) {
  uint64_t now = systick_us();

  if ((now - fsm->time) > 100000) {
    // Reset the history if the button was not read for 100ms
    fsm->pressed = 0;
    fsm->released = 0;
  }

  // Remember state changes and the time of the last read
  fsm->pressed |= new_state & ~fsm->state;
  fsm->released |= ~new_state & fsm->state;

  // Bring the automaton out of invalid states,
  // in case it somehow ends up in one.
  fsm->released &= fsm->pressed | fsm->state;
  fsm->pressed &= fsm->released | ~fsm->state;

  uint8_t button_idx = 0;
  while (fsm->pressed | fsm->released) {
    uint32_t mask = 1 << button_idx;

    if ((fsm->pressed & mask) != 0 && (fsm->state & mask) == 0) {
      // Button press was not signalled yet
      fsm->pressed &= ~mask;
      fsm->state |= mask;
      event->button = (button_t)button_idx;
      event->event_type = BTN_EVENT_DOWN;
      return true;
    } else if ((fsm->released & mask) != 0 && (fsm->state & mask) != 0) {
      // Button release was not signalled yet
      fsm->released &= ~mask;
      fsm->state &= ~mask;
      event->button = (button_t)button_idx;
      event->event_type = BTN_EVENT_UP;
      return true;
    }

    ++button_idx;
  }

  return false;
}

bool button_get_event(button_event_t* event) {
  memset(event, 0, sizeof(*event));

  uint32_t new_state = button_get_state();

#ifdef DEBUGLINK
  new_state |= button_debug_get_state();
#endif

  button_fsm_t* fsm = &g_button_tls[systask_id(systask_active())];
  return button_fsm_get_event(fsm, new_state, event);
}

static void on_task_created(void* context, systask_id_t task_id) {
  button_fsm_t* fsm = &g_button_tls[task_id];
  button_fsm_clear(fsm);
}

static void on_event_poll(void* context, bool read_awaited,
                          bool write_awaited) {
  UNUSED(write_awaited);

  if (read_awaited) {
    uint32_t state = button_get_state();
    syshandle_signal_read_ready(SYSHANDLE_BUTTON, &state);
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  button_fsm_t* fsm = &g_button_tls[task_id];

  uint32_t new_state = *(uint32_t*)param;

#ifdef DEBUGLINK
  button_debug_next();
  new_state |= button_debug_get_state();
#endif

  return button_fsm_event_ready(fsm, new_state);
}

static const syshandle_vmt_t g_button_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL_MODE
