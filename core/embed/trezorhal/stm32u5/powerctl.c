
#include STM32_HAL_H
#include TREZOR_BOARD

#include <stdio.h>
#include "gfx_draw.h"
#include "platform.h"
#include "supervise.h"
#include "usb.h"
#include "xdisplay.h"

void device_suspend_privileged(void) {
  HAL_SuspendTick();
  HAL_PWREx_EnterSTOP2Mode(PWR_STOPENTRY_WFE);
  SystemInit();
  HAL_ResumeTick();
  svc_elevate();
}

void device_suspend(void) {
  svc_elevate();

  GPIO_InitTypeDef GPIO_InitStruct = {0};

  GPIO_InitStruct.Pin = GPIO_PIN_13;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLDOWN;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  EXTI_HandleTypeDef EXTI_Handle = {0};
  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = EXTI_GPIOC;
  EXTI_Config.Line = EXTI_LINE_13;
  EXTI_Config.Mode = EXTI_MODE_EVENT;
  EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
  HAL_EXTI_SetConfigLine(&EXTI_Handle, &EXTI_Config);

  // HAL_PWR_EnableWakeUpPin(PWR_WAKEUP_PIN2_HIGH_1);

  usb_stop();
  display_deinit();

  svc_suspend();

  display_init();
  usb_start();

  drop_privileges();
}

void device_suspend_test(void) {
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  GPIO_InitStruct.Pin = GPIO_PIN_13;
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLDOWN;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

  if (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) != GPIO_PIN_RESET) {
    while (HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13) != GPIO_PIN_RESET) {
    }

    device_suspend();
  }
}
