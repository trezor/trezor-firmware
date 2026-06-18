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

// Headless ("none") touch driver.
//
// Used by boards that have no touch panel (e.g. bare development boards). It
// satisfies the touch API but never reports any touch activity. This lets the
// touch-based UI (and the `touch_get_event()` helper in `touch_poll.c`) link
// and run without touch hardware; the interface simply stays idle.

#include <trezor_rtl.h>

#include <io/touch.h>

#include "../touch_poll.h"

#ifdef KERNEL_MODE

secbool touch_init(void) {
  // Initialize the polling layer so touch_get_event() works (and always
  // returns "no event").
  if (!touch_poll_init()) {
    return secfalse;
  }
  return sectrue;
}

void touch_deinit(void) { touch_poll_deinit(); }

void touch_power_set(bool on) {}

#ifdef USE_SUSPEND
void touch_suspend(void) {}

void touch_resume(void) {}
#endif

secbool touch_ready(void) { return sectrue; }

uint8_t touch_get_version(void) { return 0; }

secbool touch_set_sensitivity(uint8_t value) { return sectrue; }

secbool touch_activity(void) { return secfalse; }

uint32_t touch_get_state(void) { return 0; }

#if defined(USE_SUSPEND) && defined(USE_TOUCH_WAKEUP)
void touch_wakeup_set_enabled(bool enabled) {}

bool touch_wakeup_get_enabled(void) { return false; }
#endif

#endif  // KERNEL_MODE
