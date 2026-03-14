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

typedef struct {
  uint8_t soc;
  pm_charging_status_t charging_status;
  pm_power_status_t power_status;
  bool usb_connected;
  bool wireless_connected;
  bool ntc_connected;
  bool charging_limited;
  bool temp_control_active;
  bool battery_connected;
} emu_battery_state_t;

static emu_battery_state_t emu_battery = {
    .soc = 100,
    .charging_status = PM_BATTERY_IDLE,
    .power_status = PM_STATE_ACTIVE,
    .usb_connected = true,
    .wireless_connected = false,
    .ntc_connected = true,
    .charging_limited = false,
    .temp_control_active = false,
    .battery_connected = true,
};

static pm_event_t emu_pending_events = {.all = 0};

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
  if (emu_pending_events.all != 0) {
    *event_flags = emu_pending_events;
    emu_pending_events.all = 0;
    return true;
  }

  memset(event_flags, 0, sizeof(pm_event_t));
  return false;
}

pm_status_t pm_get_state(pm_state_t* state) {
  state->usb_connected = emu_battery.usb_connected;
  state->wireless_connected = emu_battery.wireless_connected;
  state->charging_status = emu_battery.charging_status;
  state->power_status = emu_battery.power_status;
  state->soc = emu_battery.soc;
  state->ntc_connected = emu_battery.ntc_connected;
  state->charging_limited = emu_battery.charging_limited;
  state->temp_control_active = emu_battery.temp_control_active;
  state->battery_connected = emu_battery.battery_connected;
  return PM_OK;
}

bool pm_is_charging(void) {
  return emu_battery.charging_status == PM_BATTERY_CHARGING;
}

bool pm_usb_connected(void) { return emu_battery.usb_connected; }

pm_status_t pm_set_soc_target(uint8_t target) { return PM_OK; }

// Helper: auto-derive charging status from connection state
static pm_charging_status_t emu_derive_charging_status(void) {
  if (emu_battery.usb_connected || emu_battery.wireless_connected) {
    return PM_BATTERY_CHARGING;
  }
  return PM_BATTERY_DISCHARGING;
}

void pm_set_emu_battery_state(int soc, int usb_connected,
                              int wireless_connected, int ntc_connected,
                              int charging_limited, int temp_control_active,
                              int battery_connected, int charging_status,
                              int power_status) {
  emu_battery_state_t old = emu_battery;

  // Apply only fields that are set (>= 0 means set, -1 means unset/None)
  if (soc >= 0) {
    emu_battery.soc = (uint8_t)(soc > 100 ? 100 : soc);
  }

  if (usb_connected >= 0) {
    emu_battery.usb_connected = (bool)usb_connected;
  }

  if (wireless_connected >= 0) {
    emu_battery.wireless_connected = (bool)wireless_connected;
  }

  if (ntc_connected >= 0) {
    emu_battery.ntc_connected = (bool)ntc_connected;
  }

  if (charging_limited >= 0) {
    emu_battery.charging_limited = (bool)charging_limited;
  }

  if (temp_control_active >= 0) {
    emu_battery.temp_control_active = (bool)temp_control_active;
  }

  if (battery_connected >= 0) {
    emu_battery.battery_connected = (bool)battery_connected;
  }

  if (charging_status >= 0) {
    // Explicit override
    emu_battery.charging_status = (pm_charging_status_t)charging_status;
  } else if (usb_connected >= 0 || wireless_connected >= 0) {
    // Auto-derive when connections changed but no explicit override
    emu_battery.charging_status = emu_derive_charging_status();
  }

  if (power_status >= 0) {
    emu_battery.power_status = (pm_power_status_t)power_status;
  }

  // Generate events for all changes
  if (emu_battery.soc != old.soc) {
    emu_pending_events.flags.soc_updated = true;
  }
  if (emu_battery.charging_status != old.charging_status) {
    emu_pending_events.flags.charging_status_changed = true;
  }
  if (emu_battery.usb_connected != old.usb_connected) {
    emu_pending_events.flags.usb_connected_changed = true;
  }
  if (emu_battery.wireless_connected != old.wireless_connected) {
    emu_pending_events.flags.wireless_connected_changed = true;
  }
  if (emu_battery.ntc_connected != old.ntc_connected) {
    emu_pending_events.flags.ntc_connected_changed = true;
  }
  if (emu_battery.charging_limited != old.charging_limited) {
    emu_pending_events.flags.charging_limited_changed = true;
  }
  if (emu_battery.temp_control_active != old.temp_control_active) {
    emu_pending_events.flags.temp_control_active_changed = true;
  }
  if (emu_battery.battery_connected != old.battery_connected) {
    emu_pending_events.flags.battery_connected_changed = true;
  }
  if (emu_battery.power_status != old.power_status) {
    emu_pending_events.flags.power_status_changed = true;
  }
}
