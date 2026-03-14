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

static struct {
  uint8_t soc;
  pm_charging_status_t charging_status;
  bool usb_connected;
  bool wireless_connected;
} emu_battery = {
    .soc = 100,
    .charging_status = PM_BATTERY_IDLE,
    .usb_connected = true,
    .wireless_connected = false,
};

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
  state->usb_connected = emu_battery.usb_connected;
  state->wireless_connected = emu_battery.wireless_connected;
  state->charging_status = emu_battery.charging_status;
  state->power_status = PM_STATE_ACTIVE;
  state->soc = emu_battery.soc;
  state->ntc_connected = true;
  state->battery_connected = true;
  return PM_OK;
}

bool pm_is_charging(void) {
  return emu_battery.charging_status == PM_BATTERY_CHARGING;
}

bool pm_usb_connected(void) { return emu_battery.usb_connected; }

pm_status_t pm_set_soc_target(uint8_t target) { return PM_OK; }

void pm_set_emu_battery_state(uint8_t soc, uint8_t charging_state) {
  emu_battery.soc = soc > 100 ? 100 : soc;

  switch (charging_state) {
    case 1:  // CHARGING_CABLE
      emu_battery.charging_status = PM_BATTERY_CHARGING;
      emu_battery.usb_connected = true;
      emu_battery.wireless_connected = false;
      break;
    case 2:  // CHARGING_WIRELESS
      emu_battery.charging_status = PM_BATTERY_CHARGING;
      emu_battery.usb_connected = false;
      emu_battery.wireless_connected = true;
      break;
    default:  // DISCHARGING (0) or unknown
      emu_battery.charging_status = PM_BATTERY_DISCHARGING;
      emu_battery.usb_connected = false;
      emu_battery.wireless_connected = false;
      break;
  }
}
