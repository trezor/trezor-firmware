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

#include <io/display.h>
#include <io/usb.h>
#include <sys/irq.h>
#include <sys/systick.h>

#include "../npm1300/npm1300.h"
#include "power_manager_internal.h"

#ifdef USE_OPTIGA
#include <sec/optiga_config.h>
#include <sec/optiga_transport.h>
#endif

#ifdef USE_STORAGE_HWKEY
#include <sec/secure_aes.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef USE_RGB_LED
#include <io/rgb_led.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

static void pm_background_tasks_suspend(void);
static bool pm_background_tasks_suspended(void);
static void pm_background_tasks_resume(void);

pm_status_t pm_control_hibernate() {
  // TEMPORARY FIX:
  // Enable Backup domain retentaion in VBAT mode before entering the
  // hiberbation. BREN bit can be accessed only in LDO mode.
  __HAL_RCC_PWR_CLK_ENABLE();

  // Switch to LDO regulator
  CLEAR_BIT(PWR->CR3, PWR_CR3_REGSEL);
  // Wait until system switch on new regulator
  while (HAL_IS_BIT_SET(PWR->SVMSR, PWR_SVMSR_REGS))
    ;
  // Enable backup domain retention
  PWR->BDCR1 |= PWR_BDCR1_BREN;

  if (!npm1300_enter_shipmode()) {
    return PM_ERROR;
  }

  // Wait for the device to power off
  systick_delay_ms(50);

  return PM_ERROR;
}

void pm_control_suspend() {
  // Clear all wakeup flags. From this point, any wakeup event that
  // sets a wakeup flag causes this function to return.
  pm_wakeup_flags_reset();

// Deinitialize all drivers that are not required in low-power mode
// (e.g., USB, display, touch, haptic, etc.).
#ifdef USE_STORAGE_HWKEY
  secure_aes_deinit();
#endif
#ifdef USE_TROPIC
  tropic_deinit();
#endif
#ifdef USE_OPTIGA
  optiga_deinit();
#endif
#ifdef USE_USB
  usb_stop();
#endif
#ifdef USE_HAPTIC
  haptic_deinit();
#endif
#ifdef USE_RGB_LED
  rgb_led_deinit();
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

  pm_wakeup_flags_t wakeup_flags = 0;

  while (true) {
    pm_wakeup_flags_get(&wakeup_flags);
    if (wakeup_flags != 0) {
      // If any wakeup flag is set, exit the loop.
      break;
    }

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

    if (true) {
      pm_wakeup_flags_get(&wakeup_flags);
      if (wakeup_flags != 0) {
        // If any wakeup flag is set, exit the loop.
        break;
      }

      // Disable interrupts by setting PRIMASK to 1.
      //
      // The system can wake up, but interrupts will not be processed until
      // PRIMASK is cleared again. This is necessary to restore the system clock
      // immediately after exiting STOP2 mode.
      irq_key_t irq_key = irq_lock();

      // The PWR clock is disabled after system initialization.
      // Re-enable it before writing to PWR registers.
      __HAL_RCC_PWR_CLK_ENABLE();

      // Enter STOP2 low-power mode
      HAL_PWREx_EnterSTOP2Mode(PWR_STOPENTRY_WFI);

      // Disable PWR clock after use
      __HAL_RCC_PWR_CLK_DISABLE();

      // Recover system clock
      SystemInit();

      irq_unlock(irq_key);

      // At this point, all pending interrupts are processed.
      // Some of them may set wakeup flags.
    }

    // Resume state machines running in the interrupt context
    pm_background_tasks_resume();
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
#ifdef USE_RGB_LED
  rgb_led_init();
#endif
#ifdef USE_USB
  usb_start();
#endif
#ifdef USE_STORAGE_HWKEY
  secure_aes_init();
#endif
#ifdef USE_OPTIGA
  optiga_init_and_configure();
#endif
#ifdef USE_TROPIC
  tropic_init();
#endif
}

static void pm_background_tasks_suspend(void) {
  // stwlc38
  // npm1300
  // nrf52
  // ble
  // powerctl
}

static bool pm_background_tasks_suspended(void) { return true; }

static void pm_background_tasks_resume(void) {}

#endif
