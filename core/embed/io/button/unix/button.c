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

bool button_get_event(button_event_t *event) {
  button_driver_t *drv = &g_button_driver;

  memset(event, 0, sizeof(button_event_t));

  if (!drv->initialized) {
    return 0;
  }

  SDL_Event sdl_event;

  if (SDL_PollEvent(&sdl_event) > 0 &&
      (sdl_event.type == SDL_KEYDOWN || sdl_event.type == SDL_KEYUP) &&
      !sdl_event.key.repeat) {
    bool down = (sdl_event.type == SDL_KEYDOWN);
    uint32_t evt_type = down ? BTN_EVENT_DOWN : BTN_EVENT_UP;

    switch (sdl_event.key.keysym.sym) {
#ifdef BTN_LEFT_KEY
      case BTN_LEFT_KEY:
        drv->left_down = down;
        event->event_type = evt_type;
        event->button = BTN_LEFT;
        return true;
#endif
#ifdef BTN_RIGHT_KEY
      case BTN_RIGHT_KEY:
        drv->right_down = down;
        event->event_type = evt_type;
        event->button = BTN_RIGHT;
        return true;
#endif
#ifdef BTN_POWER_KEY
      case BTN_POWER_KEY:
        drv->power_down = down;
        event->event_type = evt_type;
        event->button = BTN_POWER;
        return true;
#endif
      default:
        break;
    }
  }

  return false;
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
