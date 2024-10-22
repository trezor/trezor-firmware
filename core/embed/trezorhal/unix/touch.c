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

#include TREZOR_BOARD

#include <SDL.h>
#include <stdbool.h>
#include <stdint.h>

#include "common.h"
#include "touch.h"

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
  BUTTON_SWIPE_LEFT_INITIATED,
  BUTTON_SWIPE_RIGHT_INITIATED,
  BUTTON_SWIPE_UP_INITIATED,
  BUTTON_SWIPE_DOWN_INITIATED,
  BUTTON_SWIPE_COMPLETED
} touch_state_t;

typedef struct {
  // Set if driver is initialized
  secbool initialized;
  // Current state of the touch driver
  touch_state_t state;
  // Last valid coordinates
  int last_x;
  int last_y;

} touch_driver_t;

// Touch driver instance
static touch_driver_t g_touch_driver = {
    .initialized = secfalse,
};

static bool is_inside_display(int x, int y) {
  return x >= sdl_touch_offset_x && y >= sdl_touch_offset_y &&
         x - sdl_touch_offset_x < sdl_display_res_x &&
         y - sdl_touch_offset_y < sdl_display_res_y;
}

static bool is_button_swipe_initiated(const touch_driver_t* driver) {
  return driver->state == BUTTON_SWIPE_LEFT_INITIATED ||
         driver->state == BUTTON_SWIPE_RIGHT_INITIATED ||
         driver->state == BUTTON_SWIPE_UP_INITIATED ||
         driver->state == BUTTON_SWIPE_DOWN_INITIATED;
}

static void handle_mouse_events(touch_driver_t* driver, SDL_Event event,
                                int* ev_type, int* ev_x, int* ev_y) {
  bool inside_display = is_inside_display(event.button.x, event.button.y);
  switch (event.type) {
    case SDL_MOUSEBUTTONDOWN:
      if (inside_display) {
        *ev_x = event.button.x - sdl_touch_offset_x;
        *ev_y = event.button.y - sdl_touch_offset_y;
        *ev_type = TOUCH_START;
        driver->state = MOUSE_DOWN_INSIDE;
      }
      break;

    case SDL_MOUSEBUTTONUP:
      if (driver->state != IDLE) {
        *ev_x = inside_display ? event.button.x - sdl_touch_offset_x
                               : driver->last_x;
        *ev_y = inside_display ? event.button.y - sdl_touch_offset_y
                               : driver->last_y;
        *ev_type = TOUCH_END;
        driver->state = IDLE;
      }
      break;

    case SDL_MOUSEMOTION:
      if (driver->state != IDLE) {
        if (inside_display) {
          *ev_x = event.motion.x - sdl_touch_offset_x;
          *ev_y = event.motion.y - sdl_touch_offset_y;
          // simulate TOUCH_START if pressed in mouse returned on visible area
          *ev_type =
              (driver->state == MOUSE_DOWN_OUTSIDE) ? TOUCH_START : TOUCH_MOVE;
          driver->state = MOUSE_DOWN_INSIDE;
        } else {
          if (driver->state == MOUSE_DOWN_INSIDE) {
            // use last valid coordinates and simulate TOUCH_END
            *ev_x = driver->last_x;
            *ev_y = driver->last_y;
            *ev_type = TOUCH_END;
          }
          driver->state = MOUSE_DOWN_OUTSIDE;
        }
      }
      break;
  }
}

static void handle_button_events(touch_driver_t* driver, SDL_Event event,
                                 int* ev_type, int* ev_x, int* ev_y) {
  // Handle arrow buttons to trigger a scroll movement by set length in the
  // direction of the button
  if (event.type == SDL_KEYDOWN && !event.key.repeat &&
      !is_button_swipe_initiated(driver)) {
    switch (event.key.keysym.sym) {
      case SDLK_LEFT:
        *ev_x = _btn_swipe_begin;
        *ev_y = sdl_display_res_y / 2;
        *ev_type = TOUCH_START;
        driver->state = BUTTON_SWIPE_LEFT_INITIATED;
        break;
      case SDLK_RIGHT:
        *ev_x = sdl_display_res_x - _btn_swipe_begin;
        *ev_y = sdl_display_res_y / 2;
        *ev_type = TOUCH_START;
        driver->state = BUTTON_SWIPE_RIGHT_INITIATED;
        break;
      case SDLK_UP:
        *ev_x = sdl_display_res_x / 2;
        *ev_y = _btn_swipe_begin;
        *ev_type = TOUCH_START;
        driver->state = BUTTON_SWIPE_UP_INITIATED;
        break;
      case SDLK_DOWN:
        *ev_x = sdl_display_res_x / 2;
        *ev_y = sdl_display_res_y - _btn_swipe_begin;
        *ev_type = TOUCH_START;
        driver->state = BUTTON_SWIPE_DOWN_INITIATED;
        break;
    }
  } else if (event.type == SDL_KEYUP && driver->state != IDLE) {
    switch (event.key.keysym.sym) {
      case SDLK_LEFT:
        if (driver->state == BUTTON_SWIPE_LEFT_INITIATED) {
          *ev_x = _btn_swipe_begin + _btn_swipe_length;
          *ev_y = sdl_display_res_y / 2;
          *ev_type = TOUCH_MOVE;
          driver->state = BUTTON_SWIPE_COMPLETED;
        }
        break;
      case SDLK_RIGHT:
        if (driver->state == BUTTON_SWIPE_RIGHT_INITIATED) {
          *ev_x = sdl_display_res_x - _btn_swipe_begin - _btn_swipe_length;
          *ev_y = sdl_display_res_y / 2;
          *ev_type = TOUCH_MOVE;
          driver->state = BUTTON_SWIPE_COMPLETED;
        }
        break;
      case SDLK_UP:
        if (driver->state == BUTTON_SWIPE_UP_INITIATED) {
          *ev_x = sdl_display_res_x / 2;
          *ev_y = _btn_swipe_begin + _btn_swipe_length;
          *ev_type = TOUCH_MOVE;
          driver->state = BUTTON_SWIPE_COMPLETED;
        }
        break;
      case SDLK_DOWN:
        if (driver->state == BUTTON_SWIPE_DOWN_INITIATED) {
          *ev_x = sdl_display_res_x / 2;
          *ev_y = sdl_display_res_y - _btn_swipe_begin - _btn_swipe_length;
          *ev_type = TOUCH_MOVE;
          driver->state = BUTTON_SWIPE_COMPLETED;
        }
        break;
    }
  }
}

secbool touch_init(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (driver->initialized != sectrue) {
    memset(driver, 0, sizeof(touch_driver_t));
    driver->state = IDLE;
    driver->initialized = sectrue;
  }

  return driver->initialized;
}

void touch_deinit(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (driver->initialized == sectrue) {
    memset(driver, 0, sizeof(touch_driver_t));
  }
}

void touch_power_set(bool on) {
  // Not implemented on the emulator
}

secbool touch_ready(void) {
  touch_driver_t* driver = &g_touch_driver;
  return driver->initialized;
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

uint32_t touch_get_event(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (driver->initialized != sectrue) {
    return 0;
  }

  if (driver->state == BUTTON_SWIPE_COMPLETED) {
    driver->state = IDLE;
    return TOUCH_END | touch_pack_xy(driver->last_x, driver->last_y);
  }

  SDL_Event event;

  int ev_x = 0;
  int ev_y = 0;
  int ev_type = 0;

  while (SDL_PollEvent(&event) > 0) {
    if (driver->state == IDLE || driver->state == MOUSE_DOWN_INSIDE ||
        driver->state == MOUSE_DOWN_OUTSIDE) {
      handle_mouse_events(driver, event, &ev_type, &ev_x, &ev_y);
    }
    if (driver->state == IDLE || is_button_swipe_initiated(driver)) {
      handle_button_events(driver, event, &ev_type, &ev_x, &ev_y);
    }

    if (ev_type != 0) {
      driver->last_x = ev_x;
      driver->last_y = ev_y;
    }
  }
  return ev_type | touch_pack_xy(ev_x, ev_y);
}
