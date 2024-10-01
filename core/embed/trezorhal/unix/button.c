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

#include <SDL.h>

#include "button.h"

#ifdef BTN_LEFT_KEY
static bool last_left = 0;
#endif

#ifdef BTN_RIGHT_KEY
static bool last_right = 0;
#endif

#ifdef BTN_POWER_KEY
static bool last_power = 0;
#endif

#ifdef BTN_LEFT_KEY
bool button_state_left(void) { return last_left; }
#endif

#ifdef BTN_RIGHT_KEY
bool button_state_right(void) { return last_right; }
#endif

#ifdef BTN_POWER_KEY
bool button_state_power(void) { return last_power; }
#endif

bool button_state(button_t button) {
  switch (button) {
#ifdef BTN_LEFT_KEY
    case BTN_LEFT:
      return button_state_left();
#endif
#ifdef BTN_RIGHT_KEY
    case BTN_RIGHT:
      return button_state_right();
#endif
#ifdef BTN_POWER_KEY
    case BTN_POWER:
      return button_state_power();
#endif
    default:
      return false;
  }
}

uint32_t button_read(void) {
  SDL_Event event;
  if (SDL_PollEvent(&event) > 0) {
    switch (event.type) {
      case SDL_KEYDOWN:
        if (event.key.repeat) {
          break;
        }
        switch (event.key.keysym.sym) {
#ifdef BTN_LEFT_KEY
          case BTN_LEFT_KEY:
            last_left = 1;
            return BTN_EVT_DOWN | BTN_LEFT;
#endif
#ifdef BTN_RIGHT_KEY
          case BTN_RIGHT_KEY:
            last_right = 1;
            return BTN_EVT_DOWN | BTN_RIGHT;
#endif
#ifdef BTN_POWER_KEY
          case BTN_POWER_KEY:
            last_power = 1;
            return BTN_EVT_DOWN | BTN_POWER;
#endif
          default:
            break;
        }
        break;
      case SDL_KEYUP:
        if (event.key.repeat) {
          break;
        }
        switch (event.key.keysym.sym) {
#ifdef BTN_LEFT_KEY
          case BTN_LEFT_KEY:
            last_left = 0;
            return BTN_EVT_UP | BTN_LEFT;
#endif
#ifdef BTN_RIGHT_KEY
          case BTN_RIGHT_KEY:
            last_right = 0;
            return BTN_EVT_UP | BTN_RIGHT;
#endif
#ifdef BTN_POWER_KEY
          case BTN_POWER_KEY:
            last_power = 0;
            return BTN_EVT_UP | BTN_POWER;
#endif
          default:
            break;
        }
        break;
      default:
        break;
    }
  }
  return 0;
}

void button_init(void) {}
