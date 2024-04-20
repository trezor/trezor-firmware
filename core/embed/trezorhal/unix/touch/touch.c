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

#include <SDL.h>
#include <stdbool.h>
#include <stdint.h>

#include TREZOR_BOARD
#ifdef USE_TOUCH

#include "common.h"
#include "platform.h"
#include "touch.h"

extern int sdl_display_res_x, sdl_display_res_y;
extern int sdl_touch_offset_x, sdl_touch_offset_y;

static int _touch_x = 0;
static int _touch_y = 0;

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
} touch_input_state_t;

static touch_input_state_t input_state = IDLE;

static bool is_inside_display(int x, int y) {
  return x >= sdl_touch_offset_x && y >= sdl_touch_offset_y &&
         x - sdl_touch_offset_x < sdl_display_res_x &&
         y - sdl_touch_offset_y < sdl_display_res_y;
}

static bool is_button_swipe_initiated() {
  return input_state == BUTTON_SWIPE_LEFT_INITIATED ||
         input_state == BUTTON_SWIPE_RIGHT_INITIATED ||
         input_state == BUTTON_SWIPE_UP_INITIATED ||
         input_state == BUTTON_SWIPE_DOWN_INITIATED;
}

static void handle_mouse_events(SDL_Event event, int* ev_type, int* ev_x,
                                int* ev_y) {
  bool inside_display = is_inside_display(event.button.x, event.button.y);
  switch (event.type) {
    case SDL_MOUSEBUTTONDOWN:
      if (inside_display) {
        *ev_x = event.button.x - sdl_touch_offset_x;
        *ev_y = event.button.y - sdl_touch_offset_y;
        *ev_type = TOUCH_START;
        input_state = MOUSE_DOWN_INSIDE;
      }
      break;

    case SDL_MOUSEBUTTONUP:
      if (input_state != IDLE) {
        *ev_x = inside_display ? event.button.x - sdl_touch_offset_x : _touch_x;
        *ev_y = inside_display ? event.button.y - sdl_touch_offset_y : _touch_y;
        *ev_type = TOUCH_END;
        input_state = IDLE;
      }
      break;

    case SDL_MOUSEMOTION:
      if (input_state != IDLE) {
        if (inside_display) {
          *ev_x = event.motion.x - sdl_touch_offset_x;
          *ev_y = event.motion.y - sdl_touch_offset_y;
          // simulate TOUCH_START if pressed in mouse returned on visible area
          *ev_type =
              (input_state == MOUSE_DOWN_OUTSIDE) ? TOUCH_START : TOUCH_MOVE;
          input_state = MOUSE_DOWN_INSIDE;
        } else {
          if (input_state == MOUSE_DOWN_INSIDE) {
            // use last valid coordinates and simulate TOUCH_END
            *ev_x = _touch_x;
            *ev_y = _touch_y;
            *ev_type = TOUCH_END;
          }
          input_state = MOUSE_DOWN_OUTSIDE;
        }
      }
      break;
  }
}

static void handle_button_events(SDL_Event event, int* ev_type, int* ev_x,
                                 int* ev_y) {
  // Handle arrow buttons to trigger a scroll movement by set length in the
  // direction of the button
  if (event.type == SDL_KEYDOWN && !event.key.repeat &&
      !is_button_swipe_initiated()) {
    switch (event.key.keysym.sym) {
      case SDLK_LEFT:
        *ev_x = _btn_swipe_begin;
        *ev_y = sdl_display_res_y / 2;
        *ev_type = TOUCH_START;
        input_state = BUTTON_SWIPE_LEFT_INITIATED;
        break;
      case SDLK_RIGHT:
        *ev_x = sdl_display_res_x - _btn_swipe_begin;
        *ev_y = sdl_display_res_y / 2;
        *ev_type = TOUCH_START;
        input_state = BUTTON_SWIPE_RIGHT_INITIATED;
        break;
      case SDLK_UP:
        *ev_x = sdl_display_res_x / 2;
        *ev_y = _btn_swipe_begin;
        *ev_type = TOUCH_START;
        input_state = BUTTON_SWIPE_UP_INITIATED;
        break;
      case SDLK_DOWN:
        *ev_x = sdl_display_res_x / 2;
        *ev_y = sdl_display_res_y - _btn_swipe_begin;
        *ev_type = TOUCH_START;
        input_state = BUTTON_SWIPE_DOWN_INITIATED;
        break;
    }
  } else if (event.type == SDL_KEYUP && input_state != IDLE) {
    switch (event.key.keysym.sym) {
      case SDLK_LEFT:
        if (input_state == BUTTON_SWIPE_LEFT_INITIATED) {
          *ev_x = _btn_swipe_begin + _btn_swipe_length;
          *ev_y = sdl_display_res_y / 2;
          *ev_type = TOUCH_MOVE;
          input_state = BUTTON_SWIPE_COMPLETED;
        }
        break;
      case SDLK_RIGHT:
        if (input_state == BUTTON_SWIPE_RIGHT_INITIATED) {
          *ev_x = sdl_display_res_x - _btn_swipe_begin - _btn_swipe_length;
          *ev_y = sdl_display_res_y / 2;
          *ev_type = TOUCH_MOVE;
          input_state = BUTTON_SWIPE_COMPLETED;
        }
        break;
      case SDLK_UP:
        if (input_state == BUTTON_SWIPE_UP_INITIATED) {
          *ev_x = sdl_display_res_x / 2;
          *ev_y = _btn_swipe_begin + _btn_swipe_length;
          *ev_type = TOUCH_MOVE;
          input_state = BUTTON_SWIPE_COMPLETED;
        }
        break;
      case SDLK_DOWN:
        if (input_state == BUTTON_SWIPE_DOWN_INITIATED) {
          *ev_x = sdl_display_res_x / 2;
          *ev_y = sdl_display_res_y - _btn_swipe_begin - _btn_swipe_length;
          *ev_type = TOUCH_MOVE;
          input_state = BUTTON_SWIPE_COMPLETED;
        }
        break;
    }
  }
}

uint32_t touch_read(void) {
  if (input_state == BUTTON_SWIPE_COMPLETED) {
    input_state = IDLE;
    return TOUCH_END | touch_pack_xy(_touch_x, _touch_y);
  }

  emulator_poll_events();
  SDL_Event event;
  SDL_PumpEvents();

  int ev_x = 0;
  int ev_y = 0;
  int ev_type = 0;

  while (SDL_PollEvent(&event) > 0) {
    if (input_state == IDLE || input_state == MOUSE_DOWN_INSIDE ||
        input_state == MOUSE_DOWN_OUTSIDE) {
      handle_mouse_events(event, &ev_type, &ev_x, &ev_y);
    }
    if (input_state == IDLE || is_button_swipe_initiated()) {
      handle_button_events(event, &ev_type, &ev_x, &ev_y);
    }

    if (ev_type != 0) {
      _touch_x = ev_x;
      _touch_y = ev_y;
      break;
    }
  }
  return ev_type | touch_pack_xy(ev_x, ev_y);
}

secbool touch_init(void) { return sectrue; }
void touch_power_on(void) {}
void touch_wait_until_ready(void) {}

uint32_t touch_is_detected(void) {
  return input_state == MOUSE_DOWN_INSIDE || is_button_swipe_initiated();
}

uint8_t touch_get_version(void) { return 0; }

#endif

#ifdef USE_BUTTON

#include "button.h"

static char last_left = 0, last_right = 0;

char button_state_left(void) { return last_left; }

char button_state_right(void) { return last_right; }

uint32_t button_read(void) {
  SDL_Event event;
  SDL_PumpEvents();
  if (SDL_PollEvent(&event) > 0) {
    switch (event.type) {
      case SDL_KEYDOWN:
        if (event.key.repeat) {
          break;
        }
        switch (event.key.keysym.sym) {
          case SDLK_LEFT:
            last_left = 1;
            return BTN_EVT_DOWN | BTN_LEFT;
          case SDLK_RIGHT:
            last_right = 1;
            return BTN_EVT_DOWN | BTN_RIGHT;
        }
        break;
      case SDL_KEYUP:
        if (event.key.repeat) {
          break;
        }
        switch (event.key.keysym.sym) {
          case SDLK_LEFT:
            last_left = 0;
            return BTN_EVT_UP | BTN_LEFT;
          case SDLK_RIGHT:
            last_right = 0;
            return BTN_EVT_UP | BTN_RIGHT;
        }
        break;
    }
  }
  return 0;
}

void button_init(void) {}

#endif
