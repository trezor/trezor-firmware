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

#include "button.h"
#include "common.h"
#include "platform.h"

// Button driver state
typedef struct {
  bool initialized;

  bool left_down;
  bool right_down;

} button_driver_t;

// Button driver instance
button_driver_t g_button_driver = {
    .initialized = false,
};

bool button_init(void) {
  button_driver_t *drv = &g_button_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(button_driver_t));

  drv->initialized = true;

  return true;
}

uint32_t button_get_event(void) {
  button_driver_t *drv = &g_button_driver;

  if (!drv->initialized) {
    return 0;
  }

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
            drv->left_down = true;
            return BTN_EVT_DOWN | BTN_LEFT;
          case SDLK_RIGHT:
            drv->right_down = true;
            return BTN_EVT_DOWN | BTN_RIGHT;
        }
        break;
      case SDL_KEYUP:
        if (event.key.repeat) {
          break;
        }
        switch (event.key.keysym.sym) {
          case SDLK_LEFT:
            drv->left_down = false;
            return BTN_EVT_UP | BTN_LEFT;
          case SDLK_RIGHT:
            drv->right_down = false;
            return BTN_EVT_UP | BTN_RIGHT;
        }
        break;
    }
  }
  return 0;
}

bool button_state_left(void) {
  button_driver_t *drv = &g_button_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->left_down;
}

bool button_state_right(void) {
  button_driver_t *drv = &g_button_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->right_down;
}
