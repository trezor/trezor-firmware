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

#include STM32_HAL_H
#include TREZOR_BOARD

#include <stdio.h>
#include "haptic.h"
#include "platform.h"
#include "touch.h"
#include "usb.h"
#include "xdisplay.h"

void powerctl_suspend(void) {
  usb_stop();

#ifdef USE_HAPTIC
  haptic_deinit();
#endif

#ifdef USE_TOUCH
  touch_deinit();
#endif

  int backlight_level = display_get_backlight();

  display_deinit(DISPLAY_RESET_CONTENT);

  HAL_SuspendTick();

  // Configure PC13 (on-board button) as a wake up pin
  EXTI_HandleTypeDef EXTI_Handle = {0};
  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = EXTI_GPIOC;
  EXTI_Config.Line = EXTI_LINE_13;
  EXTI_Config.Mode = EXTI_MODE_EVENT;
  EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
  HAL_EXTI_SetConfigLine(&EXTI_Handle, &EXTI_Config);
  // HAL_PWR_EnableWakeUpPin(PWR_WAKEUP_PIN2_HIGH_1);

  // Enter STOP2 mode
  HAL_PWREx_EnterSTOP2Mode(PWR_STOPENTRY_WFE);

  // We get here when the wake-up button is pressed

  // Recover system clock
  SystemInit();

  HAL_ResumeTick();

  // Initialize drivers
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

// Test on DISC2 kit
void device_suspend_test(void) {
  // Configure PC13 (on-board button) as input
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  GPIO_InitStruct.Pin = GPIO_PIN_13;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLDOWN;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  // Is the button pressed ?
  if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) != GPIO_PIN_RESET) {
    // Wait until the button is released
    while (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) != GPIO_PIN_RESET) {
    }

    powerctl_suspend();
  }
}
