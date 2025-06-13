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
#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/pmic.h>
#include <sys/power_save.h>

#include "power_manager_internal.h"

static void pm_background_tasks_suspend(void);
static bool pm_background_tasks_suspended(void);
static void pm_background_tasks_resume(void);

pm_status_t pm_control_hibernate() {
  if (!pmic_enter_shipmode()) {
    return PM_ERROR;
  }

  // Wait for the device to power off
  // systick_delay_ms(50);

  return PM_ERROR;
}

void pm_control_suspend() {
  // Clear all wakeup flags. From this point, any wakeup event that
  // sets a wakeup flag causes this function to return.
  pm_wakeup_flags_reset();

  power_save_wakeup_params_t wakeup_params = {0};

  // Deinitialize all drivers that are not required in low-power mode
  // (e.g., USB, display, touch, haptic, etc.).
  power_save_suspend_io(&wakeup_params);

  // In the following loop, the system will attempt to enter low-power mode.
  // Low-power mode may be exited for various reasons, but the loop will
  // terminate only if a wakeup flag is set, indicating that user interaction
  // is required or the user needs to be notified.

  pm_wakeup_flags_t wakeup_flags = 0;
  pm_wakeup_flags_get(&wakeup_flags);

  while (wakeup_flags == 0) {
    // Notify state machines running in the interrupt context about the
    // impending low-power mode. They should complete any pending operations
    // and avoid starting new ones.
    pm_background_tasks_suspend();

    // Wait until all state machines are idle and the system is ready to enter
    // low-power mode. This loop also exits if any wakeup flag is set
    // (e.g., due to a button press).
    do {
      __WFI();

      // TODO: Implement a 5-second timeout to trigger a fatal error.

      // Check for wakeup flags again
      pm_wakeup_flags_get(&wakeup_flags);

    } while (!pm_background_tasks_suspended() && (wakeup_flags == 0));

    if (wakeup_flags == 0) {
      // Enter low-power mode
      power_save_suspend_cpu();

      // At this point, all pending interrupts are processed.
      // Some of them may set wakeup flags.
      pm_wakeup_flags_get(&wakeup_flags);
    }

    // Resume state machines running in the interrupt context
    pm_background_tasks_resume();
  }

  // Reinitialize all drivers that were stopped earlier
  power_save_resume_io(&wakeup_params);
}

static void pm_background_tasks_suspend(void) {}

static bool pm_background_tasks_suspended(void) { return true; }

static void pm_background_tasks_resume(void) {}

#endif  // KERNEL_MODE
