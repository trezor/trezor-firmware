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

#include TREZOR_BOARD
#include STM32_HAL_H

#include "button.h"

#ifdef KERNEL_MODE

// Button driver state
typedef struct {
  bool initialized;

  bool left_down;
  bool right_down;

} button_driver_t;

// Button driver instance
button_driver_t g_button_driver = {
    .initialized = false,
};

bool button_init(void) {
  button_driver_t *drv = &g_button_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(button_driver_t));

  BTN_LEFT_CLK_ENA();
  BTN_RIGHT_CLK_ENA();

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = BTN_LEFT_PIN;
  HAL_GPIO_Init(BTN_LEFT_PORT, &GPIO_InitStructure);

#ifdef BTN_RIGHT_PIN
  GPIO_InitStructure.Pin = BTN_RIGHT_PIN;
  HAL_GPIO_Init(BTN_RIGHT_PORT, &GPIO_InitStructure);
#endif  // BTN_RIGHT_PIN

#ifdef BTN_EXTI_INTERRUPT_HANDLER
  // Setup interrupt handler
  EXTI_HandleTypeDef EXTI_Handle = {0};
  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = BTN_EXTI_INTERRUPT_GPIOSEL;
  EXTI_Config.Line = BTN_EXTI_INTERRUPT_LINE;
  EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
  EXTI_Config.Trigger = EXTI_TRIGGER_FALLING;
  HAL_EXTI_SetConfigLine(&EXTI_Handle, &EXTI_Config);
  NVIC_SetPriority(BTN_EXTI_INTERRUPT_NUM, IRQ_PRI_NORMAL);
  __HAL_GPIO_EXTI_CLEAR_FLAG(BTN_INT_PIN);
  NVIC_EnableIRQ(BTN_EXTI_INTERRUPT_NUM);
#endif  // BTN_EXTI_INTERRUPT_HANDLER

  drv->initialized = true;

  return true;
}

uint32_t button_get_event(void) {
  button_driver_t *drv = &g_button_driver;

  if (!drv->initialized) {
    return 0;
  }

  bool left_down =
      (GPIO_PIN_RESET == HAL_GPIO_ReadPin(BTN_LEFT_PORT, BTN_LEFT_PIN));

  if (drv->left_down != left_down) {
    drv->left_down = left_down;
    if (left_down) {
      return BTN_EVT_DOWN | BTN_LEFT;
    } else {
      return BTN_EVT_UP | BTN_LEFT;
    }
  }

#ifdef BTN_RIGHT_PIN
  bool right_down =
      (GPIO_PIN_RESET == HAL_GPIO_ReadPin(BTN_RIGHT_PORT, BTN_RIGHT_PIN));

  if (drv->right_down != right_down) {
    drv->right_down = right_down;
    if (right_down) {
      return BTN_EVT_DOWN | BTN_RIGHT;
    } else {
      return BTN_EVT_UP | BTN_RIGHT;
    }
  }
#endif  // BTN_RIGHT_PIN

  return 0;
}

bool button_state_left(void) {
  button_driver_t *drv = &g_button_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->left_down;
}

bool button_state_right(void) {
  button_driver_t *drv = &g_button_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->right_down;
}

void BTN_EXTI_INTERRUPT_HANDLER(void) {
  // button_driver_t *drv = &g_button_driver;

  // Clear the EXTI line pending bit
  __HAL_GPIO_EXTI_CLEAR_FLAG(BTN_LEFT_PIN);

  // Inform the powerctl module about button press
  // wakeup_flags_set(WAKEUP_FLAGS_BUTTON);
}

#endif  // KERNEL_MODE
