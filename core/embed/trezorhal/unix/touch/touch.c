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

static bool _touch_detected = false;
static int _touch_x = 0;
static int _touch_y = 0;

bool is_inside_display(int x, int y) {
  return (x >= sdl_touch_offset_x && y >= sdl_touch_offset_y &&
          x - sdl_touch_offset_x < sdl_display_res_x &&
          y - sdl_touch_offset_y < sdl_display_res_y);
}

uint32_t touch_read(void) {
  emulator_poll_events();
  SDL_Event event;
  SDL_PumpEvents();

  int ev_x = 0;
  int ev_y = 0;
  int ev_type = 0;

  while (SDL_PollEvent(&event) > 0) {
    switch (event.type) {
      case SDL_MOUSEBUTTONDOWN:
        if (is_inside_display(event.button.x, event.button.y)) {
          ev_x = event.button.x - sdl_touch_offset_x;
          ev_y = event.button.y - sdl_touch_offset_y;
          ev_type = TOUCH_START;
        }

        break;

      case SDL_MOUSEBUTTONUP:
        if (_touch_detected) {
          if (is_inside_display(event.button.x, event.button.y)) {
            ev_x = event.button.x - sdl_touch_offset_x;
            ev_y = event.button.y - sdl_touch_offset_y;
          } else {
            // use last valid coordinates
            ev_x = _touch_x;
            ev_y = _touch_y;
          }
          ev_type = TOUCH_END;
        }
        break;

      case SDL_MOUSEMOTION:
        if (_touch_detected) {
          if (is_inside_display(event.motion.x, event.motion.y)) {
            ev_x = event.button.x - sdl_touch_offset_x;
            ev_y = event.button.y - sdl_touch_offset_y;
            ev_type = TOUCH_MOVE;
          } else {
            // use last valid coordinates and simulate TOUCH_END
            ev_x = _touch_x;
            ev_y = _touch_y;
            ev_type = TOUCH_END;
          }
        }
        break;
    }

    if (ev_type != 0) {
      _touch_x = ev_x;
      _touch_y = ev_y;

      if (ev_type == TOUCH_START) {
        _touch_detected = true;
        break;
      }

      if (ev_type == TOUCH_END) {
        _touch_detected = false;
        break;
      }
    }
  }

  return ev_type | touch_pack_xy(ev_x, ev_y);
}

void touch_init(void) {}
void touch_power_on(void) {}
void touch_wait_until_ready(void) {}

uint32_t touch_is_detected(void) { return _touch_detected; }

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
