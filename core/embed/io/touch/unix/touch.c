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

#include <io/touch.h>
#include <sys/sysevent_source.h>
#include <sys/systick.h>
#include <sys/unix/sdl_event.h>

#include "../touch_fsm.h"

extern int sdl_display_res_x, sdl_display_res_y;
extern int sdl_touch_offset_x, sdl_touch_offset_y;

// distance from the edge where arrow button swipe starts [px]
static const int _btn_swipe_begin = 120;
// length of the arrow button swipe [px]
static const int _btn_swipe_length = 60;

// A state machine to handle both mouse inputs (simulating touch) and arrow
// buttons (to simulate scroll movements). The variable `input_state` is used to
// ensure that arrow keys are not processed when mouse input is in progress and
// that mouse actions are not processed while arrow button swipe is not
// finished.
typedef enum {
  IDLE,
  MOUSE_DOWN_INSIDE,
  MOUSE_DOWN_OUTSIDE,
  BUTTON_SWIPE_INITIATED,
} touch_state_t;

typedef struct {
  // Set if driver is initialized
  secbool initialized;
  // Current state of the touch driver
  touch_state_t state;

  uint32_t swipe_time;
  int swipe_start_x;
  int swipe_start_y;
  int swipe_end_x;
  int swipe_end_y;
  int swipe_key;

  // Last event not yet read
  uint32_t last_event;
  // Touch state machine for each task
  touch_fsm_t tls[SYSTASK_MAX_TASKS];

} touch_driver_t;

// Touch driver instance
static touch_driver_t g_touch_driver = {
    .initialized = secfalse,
};

// Forward declarations
static const syshandle_vmt_t g_touch_handle_vmt;

static bool is_inside_display(int x, int y) {
  return x >= sdl_touch_offset_x && y >= sdl_touch_offset_y &&
         x - sdl_touch_offset_x < sdl_display_res_x &&
         y - sdl_touch_offset_y < sdl_display_res_y;
}

static void handle_mouse_events(touch_driver_t* drv, SDL_Event* event) {
  bool inside_display = is_inside_display(event->button.x, event->button.y);

  switch (event->type) {
    case SDL_MOUSEBUTTONDOWN:
      if (inside_display) {
        int x = event->button.x - sdl_touch_offset_x;
        int y = event->button.y - sdl_touch_offset_y;
        drv->last_event = TOUCH_START | touch_pack_xy(x, y);
        drv->state = MOUSE_DOWN_INSIDE;
      }
      break;

    case SDL_MOUSEBUTTONUP:
      if (drv->state != IDLE) {
        int x = inside_display ? event->button.x - sdl_touch_offset_x
                               : touch_unpack_x(drv->last_event);
        int y = inside_display ? event->button.y - sdl_touch_offset_y
                               : touch_unpack_y(drv->last_event);
        ;
        drv->last_event = TOUCH_END | touch_pack_xy(x, y);
        drv->state = IDLE;
      }
      break;

    case SDL_MOUSEMOTION:
      if (drv->state != IDLE) {
        if (inside_display) {
          int x = event->motion.x - sdl_touch_offset_x;
          int y = event->motion.y - sdl_touch_offset_y;
          // simulate TOUCH_START if pressed in mouse returned on visible area
          if (drv->state == MOUSE_DOWN_OUTSIDE) {
            drv->last_event = TOUCH_START | touch_pack_xy(x, y);
          } else {
            drv->last_event = TOUCH_MOVE | touch_pack_xy(x, y);
          }
          drv->state = MOUSE_DOWN_INSIDE;
        } else {
          if (drv->state == MOUSE_DOWN_INSIDE) {
            // use last valid coordinates and simulate TOUCH_END
            int x = touch_unpack_x(drv->last_event);
            int y = touch_unpack_y(drv->last_event);
            drv->last_event = TOUCH_END | touch_pack_xy(x, y);
          }
          drv->state = MOUSE_DOWN_OUTSIDE;
        }
      }
      break;
  }
}

static void handle_button_events(touch_driver_t* drv, SDL_Event* event) {
  // Handle arrow buttons to trigger a scroll movement by set length in the
  // direction of the button
  if (event->type == SDL_KEYDOWN && !event->key.repeat) {
    if (drv->state != BUTTON_SWIPE_INITIATED) {
      switch (event->key.keysym.sym) {
        case SDLK_LEFT:
          drv->swipe_start_x = _btn_swipe_begin;
          drv->swipe_start_y = sdl_display_res_y / 2;
          drv->swipe_end_x = drv->swipe_start_x + _btn_swipe_length;
          drv->swipe_end_y = drv->swipe_start_y;
          drv->state = BUTTON_SWIPE_INITIATED;
          break;
        case SDLK_RIGHT:
          drv->swipe_start_x = sdl_display_res_x - _btn_swipe_begin;
          drv->swipe_start_y = sdl_display_res_y / 2;
          drv->swipe_end_x = drv->swipe_start_x - _btn_swipe_length;
          drv->swipe_end_y = drv->swipe_start_y;
          drv->state = BUTTON_SWIPE_INITIATED;
          break;
        case SDLK_UP:
          drv->swipe_start_x = sdl_display_res_x / 2;
          drv->swipe_start_y = _btn_swipe_begin;
          drv->swipe_end_x = drv->swipe_start_x;
          drv->swipe_end_y = drv->swipe_start_y + _btn_swipe_length;
          drv->state = BUTTON_SWIPE_INITIATED;
          break;
        case SDLK_DOWN:
          drv->swipe_start_x = sdl_display_res_x / 2;
          drv->swipe_start_y = sdl_display_res_y - _btn_swipe_begin;
          drv->swipe_end_x = drv->swipe_start_x;
          drv->swipe_end_y = drv->swipe_start_y - _btn_swipe_length;
          drv->state = BUTTON_SWIPE_INITIATED;
          break;
      }

      if (drv->state == BUTTON_SWIPE_INITIATED) {
        drv->swipe_key = event->key.keysym.sym;
        drv->swipe_time = systick_ms();
        drv->last_event =
            TOUCH_START | touch_pack_xy(drv->swipe_start_x, drv->swipe_start_y);
      }
    }
  } else if (event->type == SDL_KEYUP &&
             event->key.keysym.sym == drv->swipe_key) {
    if (drv->state == BUTTON_SWIPE_INITIATED) {
      drv->last_event =
          TOUCH_END | touch_pack_xy(drv->swipe_end_x, drv->swipe_end_y);
      drv->state = IDLE;
    }
  }
}

// Called from global event loop to filter and process SDL events
static void touch_sdl_event_filter(void* context, SDL_Event* sdl_event) {
  touch_driver_t* drv = (touch_driver_t*)context;

  if (drv->state == IDLE || drv->state == MOUSE_DOWN_INSIDE ||
      drv->state == MOUSE_DOWN_OUTSIDE) {
    handle_mouse_events(drv, sdl_event);
  }

  if (drv->state == IDLE || drv->state == BUTTON_SWIPE_INITIATED) {
    handle_button_events(drv, sdl_event);
  }
}

secbool touch_init(void) {
  touch_driver_t* drv = &g_touch_driver;

  if (drv->initialized) {
    return sectrue;
  }

  memset(drv, 0, sizeof(touch_driver_t));
  drv->state = IDLE;

  if (!syshandle_register(SYSHANDLE_TOUCH, &g_touch_handle_vmt, drv)) {
    goto cleanup;
  }

  if (!sdl_events_register(touch_sdl_event_filter, drv)) {
    goto cleanup;
  }

  drv->initialized = sectrue;
  return drv->initialized;

cleanup:
  return secfalse;
}

void touch_deinit(void) {
  touch_driver_t* drv = &g_touch_driver;

  if (drv->initialized == sectrue) {
    syshandle_unregister(SYSHANDLE_TOUCH);
    memset(drv, 0, sizeof(touch_driver_t));
  }
}

void touch_power_set(bool on) {
  // Not implemented on the emulator
}

secbool touch_ready(void) {
  touch_driver_t* drv = &g_touch_driver;
  return drv->initialized;
}

secbool touch_set_sensitivity(uint8_t value) {
  // Not implemented on the emulator
  return sectrue;
}

uint8_t touch_get_version(void) {
  // Not implemented on the emulator
  return 0;
}

secbool touch_activity(void) {
  if (touch_get_event() != 0) {
    return sectrue;
  } else {
    return secfalse;
  }
}

uint32_t touch_get_state(touch_driver_t* drv) {
  sdl_events_poll();

  if (drv->state == BUTTON_SWIPE_INITIATED) {
    if (drv->last_event & TOUCH_START) {
      // Emulate swipe by sending MOVE event after 100ms
      uint32_t time_delta = systick_ms() - drv->swipe_time;
      if (time_delta > 100) {
        int x = (drv->swipe_start_x + drv->swipe_end_x) / 2;
        int y = (drv->swipe_start_y + drv->swipe_end_y) / 2;
        drv->last_event = TOUCH_MOVE | touch_pack_xy(x, y);
      }
    }
  }

  return drv->last_event;
}

uint32_t touch_get_event(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue != driver->initialized) {
    return 0;
  }

  touch_fsm_t* fsm = &driver->tls[systask_id(systask_active())];

  uint32_t touch_state = touch_get_state(driver);

  uint32_t event = touch_fsm_get_event(fsm, touch_state);

  return event;
}

static void on_task_created(void* context, systask_id_t task_id) {
  touch_driver_t* dr = (touch_driver_t*)context;
  touch_fsm_t* fsm = &dr->tls[task_id];
  touch_fsm_init(fsm);
}

static void on_event_poll(void* context, bool read_awaited,
                          bool write_awaited) {
  touch_driver_t* drv = (touch_driver_t*)context;

  UNUSED(write_awaited);

  if (read_awaited) {
    uint32_t touch_state = touch_get_state(drv);
    if (touch_state != 0) {
      syshandle_signal_read_ready(SYSHANDLE_TOUCH, &touch_state);
    }
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  touch_driver_t* drv = (touch_driver_t*)context;
  touch_fsm_t* fsm = &drv->tls[task_id];

  uint32_t touch_state = *(uint32_t*)param;

  return touch_fsm_event_ready(fsm, touch_state);
}

static const syshandle_vmt_t g_touch_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};
