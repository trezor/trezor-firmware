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

#include <io/button.h>
#include <sys/irq.h>
#include <sys/mpu.h>

#ifdef USE_POWERCTL
#include <sys/wakeup_flags.h>
#endif

#ifdef KERNEL_MODE

// Button driver state
typedef struct {
  bool initialized;

#ifdef BTN_LEFT_PIN
  bool left_down;
#endif
#ifdef BTN_RIGHT_PIN
  bool right_down;
#endif
#ifdef BTN_POWER_PIN
  bool power_down;
#endif

} button_driver_t;

// Button driver instance
static button_driver_t g_button_driver = {
    .initialized = false,
};

static void button_setup_pin(GPIO_TypeDef *port, uint16_t pin) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};

  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = pin;
  HAL_GPIO_Init(port, &GPIO_InitStructure);
}

bool button_init(void) {
  button_driver_t *drv = &g_button_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(button_driver_t));

#ifdef BTN_LEFT_PIN
  BTN_LEFT_CLK_ENA();
  button_setup_pin(BTN_LEFT_PORT, BTN_LEFT_PIN);
#endif

#ifdef BTN_RIGHT_PIN
  BTN_RIGHT_CLK_ENA();
  button_setup_pin(BTN_RIGHT_PORT, BTN_RIGHT_PIN);
#endif

#ifdef BTN_POWER_PIN
  BTN_POWER_CLK_ENA();
  button_setup_pin(BTN_POWER_PORT, BTN_POWER_PIN);
#endif

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
  __HAL_GPIO_EXTI_CLEAR_FLAG(BTN_EXTI_INTERRUPT_PIN);
  NVIC_EnableIRQ(BTN_EXTI_INTERRUPT_NUM);
#endif  // BTN_EXTI_INTERRUPT_HANDLER

  drv->initialized = true;

  return true;
}

void button_deinit(void) {
#ifdef BTN_EXIT_INTERRUPT_HANDLER
  NVIC_DisableIRQ(BTN_EXTI_INTERRUPT_NUM);
#endif
}

uint32_t button_get_event(void) {
  button_driver_t *drv = &g_button_driver;

  if (!drv->initialized) {
    return 0;
  }

#ifdef BTN_LEFT_PIN
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
#endif

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
#endif

#ifdef BTN_POWER_PIN
  bool power_down =
      (GPIO_PIN_RESET == HAL_GPIO_ReadPin(BTN_POWER_PORT, BTN_POWER_PIN));

  if (drv->power_down != power_down) {
    drv->power_down = power_down;
    if (power_down) {
      return BTN_EVT_DOWN | BTN_POWER;
    } else {
      return BTN_EVT_UP | BTN_POWER;
    }
  }
#endif

  return 0;
}

bool button_is_down(button_t button) {
  button_driver_t *drv = &g_button_driver;

  if (!drv->initialized) {
    return false;
  }

  switch (button) {
#ifdef BTN_LEFT_PIN
    case BTN_LEFT:
      return drv->left_down;
#endif
#ifdef BTN_RIGHT_PIN
    case BTN_RIGHT:
      return drv->right_down;
#endif
#ifdef BTN_POWER_PIN
    case BTN_POWER:
      return drv->power_down;
#endif
    default:
      return false;
  }
}

#ifdef BTN_EXTI_INTERRUPT_HANDLER
void BTN_EXTI_INTERRUPT_HANDLER(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  // button_driver_t *drv = &g_button_driver;

  // Clear the EXTI line pending bit
  __HAL_GPIO_EXTI_CLEAR_FLAG(BTN_EXTI_INTERRUPT_PIN);

#ifdef USE_POWERCTL
  // Inform the powerctl module about button press
  wakeup_flags_set(WAKEUP_FLAG_BUTTON);
#endif

  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}
#endif

#endif  // KERNEL_MODE
