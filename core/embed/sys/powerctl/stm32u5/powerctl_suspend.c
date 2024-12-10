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

#include <io/display.h>
#include <io/usb.h>
#include <sys/irq.h>
#include <sys/wakeup_flags.h>

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef KERNEL_MODE

static void background_tasks_suspend(void) {
  // stwlc38
  // npm1300
  // nrf52
  // ble
  // powerctl
}

static bool background_tasks_suspended(void) { return true; }

static void background_tasks_resume(void) {}

void powerctl_suspend(void) {
  // Clear all wakeup flags. From this point, any wakeup event that
  // sets a wakeup flag causes this function to return.
  wakeup_flags_reset();

  // Deinitialize all drivers that are not required in low-power mode
  // (e.g., USB, display, touch, haptic, etc.).
  usb_stop();
#ifdef USE_HAPTIC
  haptic_deinit();
#endif
#ifdef USE_TOUCH
  touch_deinit();
#endif
  int backlight_level = display_get_backlight();
  display_deinit(DISPLAY_RESET_CONTENT);

  // In the following loop, the system will attempt to enter low-power mode.
  // Low-power mode may be exited for various reasons, but the loop will
  // terminate only if a wakeup flag is set, indicating that user interaction
  // is required or the user needs to be notified.

  while (wakeup_flags_get() == 0) {
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

    } while (!background_tasks_suspended() && (wakeup_flags_get() == 0));

    if (wakeup_flags_get() == 0) {
      // Disable interrupts by setting PRIMASK to 1.
      //
      // The system can wake up, but interrupts will not be processed until
      // PRIMASK is cleared again. This is necessary to restore the system clock
      // immediately after exiting STOP2 mode.
      irq_key_t irq_key = irq_lock();

      // Enter STOP2 mode
      HAL_PWREx_EnterSTOP2Mode(PWR_STOPENTRY_WFI);

      // Recover system clock
      SystemInit();

      irq_unlock(irq_key);

      // At this point, all pending interrupts are processed.
      // Some of them may set wakeup flags.
    }

    // Resume state machines running in the interrupt context
    background_tasks_resume();
  }

  // Reinitialize all drivers that were stopped earlier
  display_init(DISPLAY_RESET_CONTENT);
  display_set_backlight(backlight_level);
#ifdef USE_TOUCH
  touch_init();
#endif
#ifdef USE_HAPTIC
  haptic_init();
#endif
  usb_start();
}

#endif  // KERNEL_MODE
