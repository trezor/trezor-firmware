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

#include <io/display.h>
#include <io/power_manager.h>
#include <io/unix/sdl_display.h>

#include <SDL.h>
#include "SDL_events.h"

pm_status_t pm_init(bool inherit_state) { return PM_OK; }

void pm_deinit(void) {}

pm_status_t pm_hibernate(void) {
  exit(1);
  return PM_OK;
}

pm_status_t pm_suspend(wakeup_flags_t* wakeup_reason) {
  display_draw_suspend_overlay();

  SDL_Event event;
  while (SDL_WaitEvent(&event)) {
    if (event.type == SDL_QUIT) {
      exit(1);
    }
    if (event.type == SDL_KEYDOWN || event.type == SDL_KEYUP ||
        event.type == SDL_MOUSEBUTTONDOWN || event.type == SDL_MOUSEBUTTONUP) {
      *wakeup_reason = WAKEUP_FLAG_BUTTON;
      break;
    }
    SDL_Delay(50);
  }
  display_refresh();
  return PM_OK;
}

pm_status_t pm_turn_on(void) { return PM_OK; }
pm_status_t pm_charging_enable(void) { return PM_OK; }
pm_status_t pm_charging_disable(void) { return PM_OK; }

bool pm_get_events(pm_event_t* event_flags) {
  memset(event_flags, 0, sizeof(pm_event_t));
  return false;
}

pm_status_t pm_get_state(pm_state_t* state) {
  state->usb_connected = true;
  state->wireless_connected = false;
  state->charging_status = PM_BATTERY_IDLE;
  state->power_status = PM_STATE_ACTIVE;
  state->soc = 100;
  return PM_OK;
}

bool pm_is_charging(void) { return false; }

bool pm_usb_connected(void) { return true; }

pm_status_t pm_set_soc_target(uint8_t target) { return PM_OK; }
