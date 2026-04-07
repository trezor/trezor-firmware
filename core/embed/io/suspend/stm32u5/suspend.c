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
#if defined(KERNEL_MODE) && !defined(SECMON)

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/suspend.h>
#include <io/suspend_io.h>
#include <sec/suspend_io.h>
#include <sys/irq.h>

#include <../../power_manager/stwlc38/stwlc38.h>
#include <io/pmic.h>
#include <io/power_manager.h>

#ifdef USE_RGB_LED
#include <io/rgb_led.h>
#endif

static wakeup_flags_t g_wakeup_flags = 0;

static void background_tasks_suspend(void);
static bool background_tasks_suspended(void);
static void background_tasks_resume(void);

void wakeup_flags_set(wakeup_flags_t flags) {
  irq_key_t irq_key = irq_lock();
  g_wakeup_flags |= flags;
  irq_unlock(irq_key);
}

void wakeup_flags_reset(void) {
  irq_key_t irq_key = irq_lock();
  g_wakeup_flags = 0;
  irq_unlock(irq_key);
}

void wakeup_flags_get(wakeup_flags_t* flags) {
  irq_key_t irq_key = irq_lock();
  *flags = g_wakeup_flags;
  irq_unlock(irq_key);
}

wakeup_flags_t system_suspend(void) {
  // Clear all wakeup flags. From this point, any wakeup event that
  // sets a wakeup flag causes this function to return.
  wakeup_flags_reset();

  power_save_wakeup_params_t wakeup_params = {0};

  // Deinitialize drivers that are not required in low-power charging phase
  // (e.g., display, touch, haptic, etc.).
  suspend_drivers_phase1(&wakeup_params);

  wakeup_flags_t wakeup_flags = 0;
  wakeup_flags_get(&wakeup_flags);

  // If the device is requested to go in suspend, but the USB is connected,
  // Keep in this loop until the external power got disconnected or the
  // device is waked up. Also, if the battery is charging, the state is signaled
  // with RGB LED charging effect.

  bool charging_in_suspend = false;
  do {
#ifdef USE_RGB_LED
    if (pm_is_charging()) {
      charging_in_suspend = true;
      if (!rgb_led_effect_ongoing()) {
        rgb_led_effect_start(RGB_LED_EFFECT_CHARGING, 0);
      }
    } else {
      charging_in_suspend = false;
      rgb_led_effect_stop();
    }
#endif

    __WFI();

    wakeup_flags_get(&wakeup_flags);

  } while ((pm_usb_is_connected() || charging_in_suspend) &&
           (wakeup_flags == 0));

  if (wakeup_flags == 0) {
    // Deinitialize rest of the drivers before entering low-power mode
    suspend_drivers_phase2();
  }

  // In the following loop, the system will attempt to enter low-power mode.
  // Low-power mode may be exited for various reasons, but the loop will
  // terminate only if a wakeup flag is set, indicating that user interaction
  // is required or the user needs to be notified.

  while (wakeup_flags == 0) {
    // Notify state machines running in the interrupt context about the
    // impending low-power mode. They should complete any pending operations
    // and avoid starting new ones.
    background_tasks_suspend();

    // Wait until all state machines are idle and the system is ready to enter
    // low-power mode. This loop also exits if any wakeup flag is set
    // (e.g., due to a button press).
    do {
      __WFI();

      // TODO: Implement a 5-second timeout to trigger a fatal error.

      // Check for wakeup flags again
      wakeup_flags_get(&wakeup_flags);

    } while (!background_tasks_suspended() && (wakeup_flags == 0));

    if (wakeup_flags == 0) {
      // Enter low-power mode
      suspend_cpu();
    }

    // Resume state machines running in the interrupt context
    background_tasks_resume();

    // Some wakeup flags may be set in interrupts right after CPU wakes up, and
    // some may be set in the background tasks resume routine. Read them here
    // to wake up immediately if any are set.
    wakeup_flags_get(&wakeup_flags);
  }

  // Reinitialize all drivers that were stopped earlier
  resume_drivers(&wakeup_params);

  return wakeup_flags;
}

static void background_tasks_suspend(void) {
  pm_driver_suspend();
  pmic_suspend();
  stwlc38_suspend();
}

static bool background_tasks_suspended(void) {
  return pmic_is_suspended() && stwlc38_is_suspended() &&
         pm_driver_is_suspended();
}

static void background_tasks_resume(void) {
  stwlc38_resume();
  pmic_resume();
  pm_driver_resume();
}

#endif  // defined(KERNEL_MODE) && !defined(SECMON)
