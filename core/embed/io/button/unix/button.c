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

#include <io/button.h>

// Button driver state
typedef struct {
  bool initialized;

#ifdef BTN_LEFT_KEY
  bool left_down;
#endif
#ifdef BTN_RIGHT_KEY
  bool right_down;
#endif
#ifdef BTN_POWER_KEY
  bool power_down;
#endif
} button_driver_t;

// Button driver instance
static button_driver_t g_button_driver = {
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

  if (SDL_PollEvent(&event) > 0 &&
      (event.type == SDL_KEYDOWN || event.type == SDL_KEYUP) &&
      !event.key.repeat) {
    bool down = (event.type == SDL_KEYDOWN);
    uint32_t evt = down ? BTN_EVT_DOWN : BTN_EVT_UP;

    switch (event.key.keysym.sym) {
#ifdef BTN_LEFT_KEY
      case BTN_LEFT_KEY:
        drv->left_down = down;
        return evt | BTN_LEFT;
#endif
#ifdef BTN_RIGHT_KEY
      case BTN_RIGHT_KEY:
        drv->right_down = down;
        return evt | BTN_RIGHT;
#endif
#ifdef BTN_POWER_KEY
      case BTN_POWER_KEY:
        drv->power_down = down;
        return evt | BTN_POWER;
#endif
      default:
        break;
    }
  }

  return 0;
}

bool button_is_down(button_t button) {
  button_driver_t *drv = &g_button_driver;

  if (!drv->initialized) {
    return false;
  }

  switch (button) {
#ifdef BTN_LEFT_KEY
    case BTN_LEFT:
      return drv->left_down;
#endif
#ifdef BTN_RIGHT_KEY
    case BTN_RIGHT:
      return drv->right_down;
#endif
#ifdef BTN_POWER_KEY
    case BTN_POWER:
      return drv->power_down;
#endif
    default:
      return false;
  }
}
