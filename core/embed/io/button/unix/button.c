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
#include <sys/unix/sdl_event.h>

#include "../button_poll.h"

// Button driver state
typedef struct {
  bool initialized;
  // Global state of buttons
  uint32_t state;
} button_driver_t;

// Button driver instance
static button_driver_t g_button_driver = {
    .initialized = false,
};

// Forward declarations
static void button_sdl_event_filter(void* context, SDL_Event* sdl_event);

bool button_init(void) {
  button_driver_t* drv = &g_button_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(button_driver_t));

  if (!button_poll_init()) {
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

  button_poll_deinit();

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

uint32_t button_get_state(void) {
  button_driver_t* drv = &g_button_driver;

  if (!drv->initialized) {
    return 0;
  }

  sdl_events_poll();
  return drv->state;
}

bool button_is_down(button_t button) {
  button_driver_t* drv = &g_button_driver;

  if (!drv->initialized) {
    return false;
  }

  return (button_get_state() & (1 << button)) != 0;
}
