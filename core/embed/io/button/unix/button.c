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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/button.h>
#include <sys/sysevent_source.h>
#include <sys/unix/sdl_event.h>

#include "../button_fsm.h"

// Button driver state
typedef struct {
  bool initialized;
  // Global state of buttons
  uint32_t state;
  // Each task has its own state machine
  button_fsm_t tls[SYSTASK_MAX_TASKS];
} button_driver_t;

// Button driver instance
static button_driver_t g_button_driver = {
    .initialized = false,
};

// Forward declarations
static const syshandle_vmt_t g_button_handle_vmt;
static void button_sdl_event_filter(void* context, SDL_Event* sdl_event);

bool button_init(void) {
  button_driver_t* drv = &g_button_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(button_driver_t));

  if (!syshandle_register(SYSHANDLE_BUTTON, &g_button_handle_vmt, drv)) {
    goto cleanup;
  }

  if (!sdl_events_register(button_sdl_event_filter, drv)) {
    goto cleanup;
  }

  drv->initialized = true;
  return true;

cleanup:
  button_deinit();
  return false;
}

void button_deinit(void) {
  button_driver_t* drv = &g_button_driver;

  syshandle_unregister(SYSHANDLE_BUTTON);

  sdl_events_unregister(button_sdl_event_filter, drv);

  memset(drv, 0, sizeof(button_driver_t));
}

// Called from global event loop to filter and process SDL events
static void button_sdl_event_filter(void* context, SDL_Event* sdl_event) {
  button_driver_t* drv = &g_button_driver;

  if (sdl_event->type != SDL_KEYDOWN && sdl_event->type != SDL_KEYUP) {
    return;
  }

  if (sdl_event->key.repeat) {
    return;
  }

  button_t button;

  switch (sdl_event->key.keysym.sym) {
#ifdef BTN_LEFT_KEY
    case BTN_LEFT_KEY:
      button = BTN_LEFT;
      break;
#endif
#ifdef BTN_RIGHT_KEY
    case BTN_RIGHT_KEY:
      button = BTN_RIGHT;
      break;
#endif
#ifdef BTN_POWER_KEY
    case BTN_POWER_KEY:
      button = BTN_POWER;
      break;
#endif
    default:
      return;
  }

  if (sdl_event->type == SDL_KEYDOWN) {
    drv->state |= (1 << button);
  } else {
    drv->state &= ~(1 << button);
  }
}

static uint32_t button_read_state(button_driver_t* drv) {
  sdl_events_poll();
  return drv->state;
}

bool button_get_event(button_event_t* event) {
  button_driver_t* drv = &g_button_driver;
  memset(event, 0, sizeof(*event));

  if (!drv->initialized) {
    return false;
  }

  uint32_t new_state = button_read_state(drv);

  button_fsm_t* fsm = &drv->tls[systask_id(systask_active())];
  return button_fsm_get_event(fsm, new_state, event);
}

bool button_is_down(button_t button) {
  button_driver_t* drv = &g_button_driver;

  if (!drv->initialized) {
    return false;
  }

  return (button_read_state(drv) & (1 << button)) != 0;
}

static void on_event_poll(void* context, bool read_awaited,
                          bool write_awaited) {
  button_driver_t* drv = (button_driver_t*)context;

  UNUSED(write_awaited);

  if (read_awaited) {
    uint32_t state = button_read_state(drv);
    syshandle_signal_read_ready(SYSHANDLE_BUTTON, &state);
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  button_driver_t* drv = (button_driver_t*)context;
  button_fsm_t* fsm = &drv->tls[task_id];

  uint32_t new_state = *(uint32_t*)param;

  return button_fsm_event_ready(fsm, new_state);
}

static const syshandle_vmt_t g_button_handle_vmt = {
    .task_created = NULL,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};
