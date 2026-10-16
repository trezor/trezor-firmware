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

// Emulator glue of the power-manager policy: implements <io/power_manager.h>
// by driving the same pure core (core/pm_core.h) the device runs, over the
// emulated PMIC (pmic/emu) and a fuel gauge whose answers the test sets
// (fuel_gauge/emu).
//
// What differs from the device glue (stm32/power_manager.c) is only what
// differs about a host:
//   - time is a virtual clock: wall-clock by default, plus pm_emu_advance_ms()
//     to jump past the policy's timeouts (shutdown, charging-limited filter,
//     thermal debounce) without waiting
//   - sampling is pull-based: the core takes a sample whenever the state is
//     read and the virtual clock has moved a sampling period (there is no
//     systimer on the host)
//   - recovery data lives in memory, suspend is an SDL wait for a key, and
//     "power off" exits the process
//
// The debuglink's DebugLinkSetBatteryState keeps its seven reported fields;
// pm_set_emu_battery_state() maps them onto physical inputs of the emulated
// PMIC and gauge, so the policy derives the reported state the way the device
// does instead of the test asserting it into existence.

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <io/notify.h>
#include <io/pmic.h>
#include <io/power_manager.h>
#include <io/unix/sdl_display.h>
#include <sys/systick.h>
#ifdef USE_TOUCH_WAKEUP
#include <io/touch.h>
#endif

#include <SDL3/SDL.h>
#include <stdlib.h>
#include "SDL3/SDL_events.h"

#include "../core/pm_core.h"
#include "../fuel_gauge/battery.h"
#include "../fuel_gauge/emu/battery_emu.h"
#include "../pmic/emu/pmic_emu.h"
#include "../power_manager_poll.h"

// --- Board tunables ----------------------------------------------------------
// The emulator runs the device's policy, so it needs the device's figures.
// See the board-tunables section in stm32/power_manager_internal.h.
#ifndef BATTERY_LOW_SOC_PERCENT
#error "Unix board header must define BATTERY_LOW_SOC_PERCENT"
#endif
#ifndef PM_POWER_SAVE_BACKLIGHT_LIMIT
#error "Unix board header must define PM_POWER_SAVE_BACKLIGHT_LIMIT"
#endif
#ifndef PM_SUSPEND_CURRENT_MA
#define PM_SUSPEND_CURRENT_MA 0.0f
#endif
#ifndef PM_HIBERNATION_CURRENT_MA
#define PM_HIBERNATION_CURRENT_MA 0.0f
#endif

static const pm_config_t g_pm_config = {
    .low_soc_percent = BATTERY_LOW_SOC_PERCENT,
    .power_save_backlight = PM_POWER_SAVE_BACKLIGHT_LIMIT,
    .suspend_current_ma = PM_SUSPEND_CURRENT_MA,
    .hibernation_current_ma = PM_HIBERNATION_CURRENT_MA,
};

// Emulated physical conditions behind the seven debuglink fields
#define PM_EMU_VBAT_V 3.7f
#define PM_EMU_IBAT_DISCHARGE_MA 50.0f
#define PM_EMU_IBAT_CHARGE_MA -100.0f
#define PM_EMU_NTC_TEMP_C 20.0f
// Inside the 43-45 C derating band (factor 0.7), so the thermal limiter is
// active while charging at the pack maximum
#define PM_EMU_NTC_HOT_C 44.0f
// How far below the charger's target the current must sit to count as
// "charging limited", and how long the filter needs to see it
#define PM_EMU_LIMITED_MARGIN_MA 50
#define PM_EMU_LIMITED_FILTER_MS 5100
// Long enough for the thermal limiter to re-evaluate its debounce
#define PM_EMU_THERMAL_DEBOUNCE_MS (2 * 60 * 1000 + 100)

typedef struct {
  bool initialized;
  pm_core_t core;

  // Virtual clock: systick plus whatever the test skipped
  uint32_t time_offset_ms;
  uint32_t last_sample_ms;

  // Emulated wireless charger (no driver on the host)
  bool wireless_connected;

  // In-memory recovery data, the host's backup RAM
  bool recovery_valid;
  pm_recovery_data_t recovery;
} pm_emu_t;

static pm_emu_t g_pm;

// --- Virtual clock -----------------------------------------------------------

static uint32_t pm_emu_now_ms(void) {
  return systick_ms() + g_pm.time_offset_ms;
}

// Moves the policy's clock forward without waiting.
void pm_emu_advance_ms(uint32_t ms) { g_pm.time_offset_ms += ms; }

// --- Carrying out the core's actions -----------------------------------------

static void pm_emu_store_recovery(void) {
  g_pm.recovery.version = PM_RECOVERY_DATA_VERSION;
  pm_core_recovery(&g_pm.core, &g_pm.recovery);
  g_pm.recovery.last_capture_timestamp = pm_emu_now_ms() / 1000;
  g_pm.recovery_valid = true;
}

static void pm_emu_apply(const pm_actions_t* actions) {
  if (actions->power_source_changed) {
    notify_send(NOTIFY_POWER_STATUS_CHANGE);
  }

  pm_charging_apply(actions);

  // No backlight cap on the host, and ship mode has nothing to switch off.

  if (actions->power_off) {
    // Hibernation: the device powers off here. The emulator exits, as it
    // always has.
    pm_emu_store_recovery();
    exit(1);
  }
}

// --- Sampling ----------------------------------------------------------------

static void pm_emu_data_ready(void* context, pmic_report_t* report) {
  pm_sample_t sample = {
      .pmic = *report,
      .wireless_connected = g_pm.wireless_connected,
  };

  pm_actions_t actions;
  pm_core_sample(&g_pm.core, &sample, pm_emu_now_ms(), &actions);
  pm_emu_apply(&actions);

  if (actions.sample_complete) {
    pm_emu_store_recovery();
  }
}

// Takes a sample now, regardless of the sampling period.
static void pm_emu_sample(void) {
  g_pm.last_sample_ms = pm_emu_now_ms();
  pmic_measure(pm_emu_data_ready, NULL);
}

// Takes a sample if a sampling period has passed since the last one. Called
// from every state read, which is how the emulator's poll loop drives the
// policy forward.
static void pm_emu_tick(void) {
  if (!g_pm.core.has_sample ||
      (pm_emu_now_ms() - g_pm.last_sample_ms) >= PM_TIMER_PERIOD_MS) {
    pm_emu_sample();
  }
}

// --- Public API --------------------------------------------------------------

pm_status_t pm_init(bool inherit_state) {
  pm_emu_t* drv = &g_pm;

  if (drv->initialized) {
    return PM_OK;
  }

  // Keep the in-memory recovery data across a re-init, like backup RAM
  bool recovery_valid = drv->recovery_valid;
  pm_recovery_data_t recovery = drv->recovery;
  memset(drv, 0, sizeof(*drv));
  drv->recovery_valid = recovery_valid;
  drv->recovery = recovery;

  if (!pmic_init()) {
    return PM_ERROR;
  }

  if (!pm_poll_init()) {
    return PM_ERROR;
  }

  bat_init();

  pm_core_reset(&drv->core);
  pm_core_init(&drv->core, &g_pm_config, inherit_state,
               drv->recovery_valid ? &drv->recovery : NULL, 0);

  // The first sample makes the reported state meaningful at once
  pm_emu_sample();

  drv->initialized = true;
  return PM_OK;
}

void pm_deinit(void) {
  pm_poll_deinit();
  pmic_deinit();
  g_pm.initialized = false;
}

pm_status_t pm_get_state(pm_state_t* state) {
  if (!g_pm.initialized) {
    return PM_NOT_INITIALIZED;
  }
  pm_emu_tick();
  pm_core_get_state(&g_pm.core, state);
  return PM_OK;
}

pm_status_t pm_get_report(pm_report_t* report) {
  if (!g_pm.initialized) {
    return PM_NOT_INITIALIZED;
  }
  pm_emu_tick();

  const pm_core_t* core = &g_pm.core;
  memset(report, 0, sizeof(*report));
  report->power_state = core->state;
  report->usb_connected = core->usb_connected;
  report->wireless_charger_connected = core->wireless_connected;
  report->system_voltage_v = core->pmic.vsys;
  report->battery_voltage_v = core->pmic.vbat;
  report->battery_current_ma = core->pmic.ibat;
  report->battery_temp_c = core->pmic.ntc_temp;
  report->pmic_temp_c = core->pmic.die_temp;

  bat_fg_state_t fg_state;
  bat_fg_get_state(&fg_state);
  report->battery_soc = fg_state.soc;
  report->battery_soc_latched = fg_state.soc_latched;

  return PM_OK;
}

pm_status_t pm_suspend(wakeup_flags_t* wakeup_reason) {
  pm_emu_t* drv = &g_pm;

  if (wakeup_reason != NULL) {
    *wakeup_reason = 0;
  }

  if (!drv->initialized) {
    return PM_NOT_INITIALIZED;
  }

  pm_actions_t actions;
  pm_core_request(&drv->core, PM_REQ_SUSPEND, pm_emu_now_ms(), &actions);
  pm_emu_apply(&actions);

  if (drv->core.request_suspend || drv->core.state != PM_STATE_SUSPEND) {
    drv->core.request_suspend = false;
    return PM_REQUEST_REJECTED;
  }

  // The host's system_suspend(): draw the overlay and wait for a wake-up key
  uint32_t suspended_at_ms = pm_emu_now_ms();
  display_draw_suspend_overlay();

  wakeup_flags_t wakeup_flags = 0;
  SDL_Event event;
  while (SDL_WaitEvent(&event)) {
    if (event.type == SDL_EVENT_QUIT) {
      exit(1);
    }
    if (event.type == SDL_EVENT_KEY_DOWN || event.type == SDL_EVENT_KEY_UP) {
      wakeup_flags = WAKEUP_FLAG_BUTTON;
      break;
    }
#ifdef USE_TOUCH_WAKEUP
    if (event.type == SDL_EVENT_MOUSE_BUTTON_DOWN ||
        event.type == SDL_EVENT_MOUSE_BUTTON_UP) {
      if (!touch_wakeup_get_enabled()) {
        /* tap-to-wake disabled: ignore touch and stay suspended */
        continue;
      }
      wakeup_flags = WAKEUP_FLAG_TOUCH;
      break;
    }
#endif
    SDL_Delay(50);
  }

  // Back: compensate the gauge for the time away, take a sample, leave SUSPEND
  pm_core_resume(&drv->core, (pm_emu_now_ms() - suspended_at_ms) / 1000);
  pm_emu_sample();

  pm_core_request(&drv->core, PM_REQ_EXIT_SUSPEND, pm_emu_now_ms(), &actions);
  pm_emu_apply(&actions);

  display_refresh();

  if (wakeup_reason != NULL) {
    *wakeup_reason = wakeup_flags;
  }
  return PM_OK;
}

pm_status_t pm_hibernate(void) {
  if (!g_pm.initialized) {
    return PM_NOT_INITIALIZED;
  }

  pm_actions_t actions;
  pm_core_request(&g_pm.core, PM_REQ_HIBERNATE, pm_emu_now_ms(), &actions);
  pm_emu_apply(&actions);  // exits the process if the policy powers off

  // Still here: the policy refused (e.g. an external source is connected)
  return PM_REQUEST_REJECTED;
}

pm_status_t pm_turn_on(void) {
  if (!g_pm.initialized) {
    return PM_NOT_INITIALIZED;
  }

  pm_actions_t actions;
  pm_core_request(&g_pm.core, PM_REQ_TURN_ON, pm_emu_now_ms(), &actions);
  pm_emu_apply(&actions);

  pm_power_status_t state = g_pm.core.state;
  if (state == PM_STATE_HIBERNATE || state == PM_STATE_CHARGING) {
    return PM_REQUEST_REJECTED;
  }
  return PM_OK;
}

// --- Charging API ------------------------------------------------------------

static pm_status_t pm_emu_charging_request_done(void) {
  pm_actions_t actions = {0};
  pm_charging_step(&g_pm.core, &actions);
  pm_charging_apply(&actions);
  return PM_OK;
}

pm_status_t pm_charging_enable(void) {
  if (!g_pm.initialized) {
    return PM_NOT_INITIALIZED;
  }
  pm_charging_set_enabled(&g_pm.core, true);
  return pm_emu_charging_request_done();
}

pm_status_t pm_charging_disable(void) {
  if (!g_pm.initialized) {
    return PM_NOT_INITIALIZED;
  }
  pm_charging_set_enabled(&g_pm.core, false);
  return pm_emu_charging_request_done();
}

pm_status_t pm_charging_set_max_current(uint16_t current_ma) {
  if (!g_pm.initialized) {
    return PM_NOT_INITIALIZED;
  }
  if (!pm_charging_set_max_limit(&g_pm.core, current_ma)) {
    return PM_REQUEST_REJECTED;
  }
  return pm_emu_charging_request_done();
}

pm_status_t pm_set_soc_target(uint8_t target) {
  if (!g_pm.initialized) {
    return PM_NOT_INITIALIZED;
  }
  if (target > 100) {
    return PM_ERROR;
  }
  pm_charging_set_soc_target(&g_pm.core, target);
  return PM_OK;
}

bool pm_is_charging(void) {
  if (!g_pm.initialized) {
    return false;
  }
  pm_emu_tick();
  return pm_charging_active(&g_pm.core);
}

bool pm_usb_is_connected(void) {
  if (!g_pm.initialized) {
    return false;
  }
  pm_emu_tick();
  return g_pm.core.usb_connected;
}

// --- Debuglink: emulated battery state ---------------------------------------

// Current the emulated battery reports for the current physical situation
static float pm_emu_ibat_ma(const pmic_report_t* in) {
  if (in->vbat < PM_BATTERY_DISCONNECTED_THR_V) {
    return 0.0f;  // no cell, no current
  }
  return in->vbus_present ? PM_EMU_IBAT_CHARGE_MA : PM_EMU_IBAT_DISCHARGE_MA;
}

void pm_set_emu_battery_state(int soc, int usb_connected,
                              int wireless_connected, int ntc_connected,
                              int charging_limited, int temp_control_active,
                              int battery_connected) {
  pmic_report_t* in = pmic_emu_inputs();

  // Apply only fields that are set (>= 0 means set, -1 means unset/None).
  // Each reported field becomes the physical condition that produces it.
  if (soc >= 0) {
    bat_emu_set_soc((soc > 100 ? 100 : soc) / 100.0f);
  }

  if (usb_connected >= 0) {
    in->vbus_present = (bool)usb_connected;
  }

  if (wireless_connected >= 0) {
    g_pm.wireless_connected = (bool)wireless_connected;
  }

  if (ntc_connected >= 0) {
    in->ntc_disconnected = !(bool)ntc_connected;
  }

  if (battery_connected >= 0) {
    in->vbat = battery_connected ? PM_EMU_VBAT_V : 0.0f;
    in->vsys = PM_EMU_VBAT_V;
  }

  if (temp_control_active >= 0) {
    // A hot cell makes the thermal limiter derate the charging current. The
    // limiter re-evaluates after a debounce, so skip past it.
    in->ntc_temp = temp_control_active ? PM_EMU_NTC_HOT_C : PM_EMU_NTC_TEMP_C;
    pm_emu_advance_ms(PM_EMU_THERMAL_DEBOUNCE_MS);
  }

  in->ibat = pm_emu_ibat_ma(in);
  in->cc_phase = in->vbus_present;

  // Let the policy see the new inputs
  pm_emu_sample();

  if (charging_limited >= 0) {
    if (charging_limited) {
      // The charger sits in constant current but delivers well below its
      // target; the filter asserts after it has seen that for a while.
      int target_ma = pmic_emu_charging_limit_ma();
      in->ibat = -(float)(target_ma > PM_EMU_LIMITED_MARGIN_MA
                              ? target_ma - PM_EMU_LIMITED_MARGIN_MA
                              : 1);
      in->cc_phase = true;
      pm_emu_sample();
      pm_emu_advance_ms(PM_EMU_LIMITED_FILTER_MS);
      pm_emu_sample();
    } else {
      in->ibat = pm_emu_ibat_ma(in);
      pm_emu_sample();
    }
  }
}
