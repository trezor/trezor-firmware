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

#include <sys/irq.h>
#include <sys/power_save.h>
#include <sys/systick.h>

#ifdef USE_BLE
#include <io/ble.h>
#endif

#ifdef USE_DISPLAY
#include <io/display.h>
#endif

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga_config.h>
#include <sec/optiga_hal.h>
#include <sec/optiga_transport.h>
#endif

#ifdef USE_RGB_LED
#include <io/rgb_led.h>
#endif

#ifdef USE_STORAGE_HWKEY
#include <sec/secure_aes.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

#ifdef USE_USB
#include <io/usb.h>
#endif

#ifdef SECURE_MODE
void power_save_suspend_cpu(void) {
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
}

void power_save_suspend_secure_io() {
#ifdef USE_STORAGE_HWKEY
  secure_aes_deinit();
#endif
#if defined(USE_TROPIC) && !defined(BOOTLOADER)
  tropic_deinit();
#endif
#ifdef USE_OPTIGA
  optiga_deinit();
#endif
}

void power_save_resume_secure_io() {
#ifdef USE_STORAGE_HWKEY
  secure_aes_init();
#endif
#ifdef USE_OPTIGA
#ifdef BOOTLOADER
  optiga_hal_init();
#else
  optiga_init_and_configure();
#endif
#endif
#if defined(USE_TROPIC) && !defined(BOOTLOADER)
  tropic_init();
#endif
}

#endif  // SECURE_MODE

void power_save_suspend_io(power_save_wakeup_params_t *wakeup_params) {
  power_save_suspend_secure_io();

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
#ifdef USE_BLE
  ble_suspend(&wakeup_params->ble);
#endif
#ifdef USE_DISPLAY
  wakeup_params->backlight_level = display_get_backlight();
  display_deinit(DISPLAY_RESET_CONTENT);
#endif
}

void power_save_resume_io(const power_save_wakeup_params_t *wakeup_params) {
#ifdef USE_DISPLAY
  // Reinitialize all drivers that were stopped earlier
  display_init(DISPLAY_RESET_CONTENT);
  display_set_backlight(wakeup_params->backlight_level);
#endif
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
#ifdef USE_BLE
  ble_resume(&wakeup_params->ble);
#endif
  power_save_resume_secure_io();
}

#endif  // KERNEL_MODE
