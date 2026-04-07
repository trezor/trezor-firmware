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

#include <trezor_rtl.h>

#include <sys/sysevent.h>
#include <sys/systick.h>

#ifdef USE_POWER_MANAGER
#include <io/power_manager.h>
#endif

#if defined USE_TOUCH
#include <io/touch.h>
#elif defined USE_BUTTON
#include "io/button.h"
#else
#error "No input method defined"
#endif

#define TIME_TO_HIBERNATE_MS 40000

typedef enum {
  RES_NONE = 0,
  RES_CLICKED = 2,
} result_t;

#ifdef USE_TOUCH
static result_t process_event(bool* layout_state, sysevents_t* signalled) {
  if ((signalled->read_ready & 1 << SYSHANDLE_TOUCH) == 0) {
    return RES_NONE;
  }

  uint32_t event = touch_get_event();

  if (*layout_state && ((event & TOUCH_END) != 0)) {
    return RES_CLICKED;
  }

  if (!*layout_state && ((event & TOUCH_START) != 0)) {
    *layout_state = true;
    return RES_NONE;
  }

  return RES_NONE;
}
#elif defined USE_BUTTON
static result_t process_event(bool* layout_state, sysevents_t* signalled) {
  if ((signalled->read_ready & 1 << SYSHANDLE_BUTTON) == 0) {
    return RES_NONE;
  }

  button_event_t event = {0};

  if (!button_get_event(&event)) {
    return RES_NONE;
  }

  if (*layout_state && !button_is_down(BTN_LEFT) &&
      !button_is_down(BTN_RIGHT)) {
    return RES_CLICKED;
  }

  if (!*layout_state && button_is_down(BTN_LEFT) && button_is_down(BTN_RIGHT)) {
    *layout_state = true;
    return RES_NONE;
  }

  return RES_NONE;
}
#endif

void ui_click(void) {
  sysevents_t awaited = {0};
  sysevents_t signalled = {0};

#ifdef USE_TOUCH
  awaited.read_ready |= 1 << SYSHANDLE_TOUCH;
#elif defined USE_BUTTON
  awaited.read_ready |= 1 << SYSHANDLE_BUTTON;
#endif

#ifdef USE_TOUCH
  // flush touch events if any
  while (touch_get_event() != 0) {
  }
#elif defined USE_BUTTON
  button_event_t event = {0};
  while (button_get_event(&event)) {
  }
#endif

#ifdef USE_POWER_MANAGER
  uint32_t deadline = ticks_timeout(TIME_TO_HIBERNATE_MS);
#endif

  bool layout_state = 0;

  // wait for TOUCH_START
  while (true) {
    sysevents_poll(&awaited, &signalled, ticks_timeout(100));
    if (signalled.read_ready != 0) {
      switch (process_event(&layout_state, &signalled)) {
        case RES_CLICKED:
          return;
        default:
          break;
      }

#ifdef USE_POWER_MANAGER
      deadline = ticks_timeout(TIME_TO_HIBERNATE_MS);
#endif
    }
#ifdef USE_POWER_MANAGER
    if (ticks_expired(deadline)) {
      pm_hibernate();
    }
#endif
  }
}
