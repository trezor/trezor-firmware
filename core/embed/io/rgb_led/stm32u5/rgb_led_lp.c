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
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/rgb_led.h>

#define LED_SWITCHING_FREQUENCY_HZ 20000
#define TIMER_PERIOD (16000000 / LED_SWITCHING_FREQUENCY_HZ)

#define RGB_LED_RED_PIN GPIO_PIN_2
#define RGB_LED_RED_PORT GPIOB
#define RGB_LED_RED_CLK_ENA __HAL_RCC_GPIOB_CLK_ENABLE

#define RGB_LED_GREEN_PIN GPIO_PIN_2
#define RGB_LED_GREEN_PORT GPIOF
#define RGB_LED_GREEN_CLK_ENA __HAL_RCC_GPIOF_CLK_ENABLE

#define RGB_LED_BLUE_PIN GPIO_PIN_0
#define RGB_LED_BLUE_PORT GPIOB
#define RGB_LED_BLUE_CLK_ENA __HAL_RCC_GPIOB_CLK_ENABLE

typedef struct {
  LPTIM_HandleTypeDef tim_1;
  LPTIM_HandleTypeDef tim_3;
  bool initialized;
} rgb_led_t;

static rgb_led_t g_rgb_led = {0};

static void rgb_led_set_default_pin_state(void) {
  HAL_GPIO_DeInit(RGB_LED_RED_PORT, RGB_LED_RED_PIN);
  HAL_GPIO_DeInit(RGB_LED_GREEN_PORT, RGB_LED_GREEN_PIN);
  HAL_GPIO_DeInit(RGB_LED_BLUE_PORT, RGB_LED_BLUE_PIN);
}

void rgb_led_init(void) {
  rgb_led_t* drv = &g_rgb_led;
  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(*drv));

  rgb_led_set_default_pin_state();

  // enable LSE clock
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
  HAL_RCC_OscConfig(&RCC_OscInitStruct);

  // select LSE as LPTIM clock source
  RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};
  PeriphClkInitStruct.PeriphClockSelection =
      RCC_PERIPHCLK_LPTIM1 | RCC_PERIPHCLK_LPTIM34;
  PeriphClkInitStruct.Lptim1ClockSelection = RCC_LPTIM1CLKSOURCE_HSI;
  PeriphClkInitStruct.Lptim34ClockSelection = RCC_LPTIM34CLKSOURCE_HSI;
  HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct);

  __HAL_RCC_LPTIM1_CLK_ENABLE();
  __HAL_RCC_LPTIM1_FORCE_RESET();
  __HAL_RCC_LPTIM1_RELEASE_RESET();

  __HAL_RCC_LPTIM3_CLK_ENABLE();
  __HAL_RCC_LPTIM3_FORCE_RESET();
  __HAL_RCC_LPTIM3_RELEASE_RESET();

  drv->tim_1.State = HAL_LPTIM_STATE_RESET;
  drv->tim_1.Instance = LPTIM1;
  drv->tim_1.Init.Period = TIMER_PERIOD;
  drv->tim_1.Init.Clock.Source = LPTIM_CLOCKSOURCE_APBCLOCK_LPOSC;
  drv->tim_1.Init.Clock.Prescaler = LPTIM_PRESCALER_DIV1;
  drv->tim_1.Init.UltraLowPowerClock.Polarity = LPTIM_CLOCKPOLARITY_RISING;
  drv->tim_1.Init.UltraLowPowerClock.SampleTime =
      LPTIM_CLOCKSAMPLETIME_DIRECTTRANSITION;
  drv->tim_1.Init.Trigger.Source = LPTIM_TRIGSOURCE_SOFTWARE;
  HAL_LPTIM_Init(&drv->tim_1);

  drv->tim_3.State = HAL_LPTIM_STATE_RESET;
  drv->tim_3.Instance = LPTIM3;
  drv->tim_3.Init.Period = TIMER_PERIOD;
  drv->tim_3.Init.Clock.Source = LPTIM_CLOCKSOURCE_APBCLOCK_LPOSC;
  drv->tim_3.Init.Clock.Prescaler = LPTIM_PRESCALER_DIV1;
  drv->tim_3.Init.UltraLowPowerClock.Polarity = LPTIM_CLOCKPOLARITY_RISING;
  drv->tim_3.Init.UltraLowPowerClock.SampleTime =
      LPTIM_CLOCKSAMPLETIME_DIRECTTRANSITION;
  drv->tim_3.Init.Trigger.Source = LPTIM_TRIGSOURCE_SOFTWARE;
  HAL_LPTIM_Init(&drv->tim_3);

  // OC initialization
  LPTIM_OC_ConfigTypeDef OC_Init = {0};
  OC_Init.Pulse = 0;
  OC_Init.OCPolarity = LPTIM_OCPOLARITY_LOW;

  HAL_LPTIM_OC_ConfigChannel(&drv->tim_1, &OC_Init, LPTIM_CHANNEL_1);
  HAL_LPTIM_OC_ConfigChannel(&drv->tim_3, &OC_Init, LPTIM_CHANNEL_1);
  HAL_LPTIM_OC_ConfigChannel(&drv->tim_3, &OC_Init, LPTIM_CHANNEL_2);

  HAL_LPTIM_Counter_Start(&drv->tim_1);
  HAL_LPTIM_Counter_Start(&drv->tim_3);

  __HAL_LPTIM_COMPARE_SET(&drv->tim_1, LPTIM_CHANNEL_1, TIMER_PERIOD);
  __HAL_LPTIM_COMPARE_SET(&drv->tim_3, LPTIM_CHANNEL_1, TIMER_PERIOD);
  __HAL_LPTIM_COMPARE_SET(&drv->tim_3, LPTIM_CHANNEL_2, TIMER_PERIOD);

  // Enable the Peripheral
  __HAL_LPTIM_ENABLE(&drv->tim_1);
  __HAL_LPTIM_ENABLE(&drv->tim_3);

  // Start timer in continuous mode
  __HAL_LPTIM_START_CONTINUOUS(&drv->tim_1);
  __HAL_LPTIM_START_CONTINUOUS(&drv->tim_3);

  // Wait for reload before configuring the pins
  __HAL_LPTIM_CLEAR_FLAG(&drv->tim_1, LPTIM_FLAG_UPDATE);
  __HAL_LPTIM_CLEAR_FLAG(&drv->tim_3, LPTIM_FLAG_UPDATE);
  while (__HAL_LPTIM_GET_FLAG(&drv->tim_1, LPTIM_FLAG_UPDATE) != true) {
  }
  while (__HAL_LPTIM_GET_FLAG(&drv->tim_3, LPTIM_FLAG_UPDATE) != true) {
  }

  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;

  RGB_LED_RED_CLK_ENA();
  GPIO_InitStructure.Pin = RGB_LED_RED_PIN;
  GPIO_InitStructure.Alternate = GPIO_AF1_LPTIM1;
  HAL_GPIO_Init(RGB_LED_RED_PORT, &GPIO_InitStructure);

  RGB_LED_GREEN_CLK_ENA();
  GPIO_InitStructure.Pin = RGB_LED_GREEN_PIN;
  GPIO_InitStructure.Alternate = GPIO_AF2_LPTIM3;
  HAL_GPIO_Init(RGB_LED_GREEN_PORT, &GPIO_InitStructure);

  RGB_LED_BLUE_CLK_ENA();
  GPIO_InitStructure.Pin = RGB_LED_BLUE_PIN;
  GPIO_InitStructure.Alternate = GPIO_AF4_LPTIM3;
  HAL_GPIO_Init(RGB_LED_BLUE_PORT, &GPIO_InitStructure);

  drv->initialized = true;
}

void rgb_led_deinit(void) {
  rgb_led_t* drv = &g_rgb_led;
  if (!drv->initialized) {
    return;
  }

  rgb_led_set_default_pin_state();

  HAL_LPTIM_PWM_Stop(&drv->tim_1, LPTIM_CHANNEL_1);
  HAL_LPTIM_PWM_Stop(&drv->tim_3, LPTIM_CHANNEL_1);
  HAL_LPTIM_PWM_Stop(&drv->tim_3, LPTIM_CHANNEL_2);

  HAL_LPTIM_Counter_Stop(&drv->tim_1);
  HAL_LPTIM_Counter_Stop(&drv->tim_3);

  __HAL_RCC_LPTIM1_CLK_DISABLE();
  __HAL_RCC_LPTIM1_FORCE_RESET();
  __HAL_RCC_LPTIM1_RELEASE_RESET();

  __HAL_RCC_LPTIM3_CLK_DISABLE();
  __HAL_RCC_LPTIM3_FORCE_RESET();
  __HAL_RCC_LPTIM3_RELEASE_RESET();

  memset(drv, 0, sizeof(*drv));
}

void rgb_led_set_color(uint32_t color) {
  rgb_led_t* drv = &g_rgb_led;
  if (!drv->initialized) {
    return;
  }

  uint32_t red = (color >> 16) & 0xFF;
  uint32_t green = (color >> 8) & 0xFF;
  uint32_t blue = color & 0xFF;

  if (red != 0) {
    __HAL_LPTIM_CAPTURE_COMPARE_ENABLE(&drv->tim_1, LPTIM_CHANNEL_1);
  } else {
    __HAL_LPTIM_CAPTURE_COMPARE_DISABLE(&drv->tim_1, LPTIM_CHANNEL_1);
  }

  if (green != 0) {
    __HAL_LPTIM_CAPTURE_COMPARE_ENABLE(&drv->tim_3, LPTIM_CHANNEL_2);
  } else {
    __HAL_LPTIM_CAPTURE_COMPARE_DISABLE(&drv->tim_3, LPTIM_CHANNEL_2);
  }

  if (blue != 0) {
    __HAL_LPTIM_CAPTURE_COMPARE_ENABLE(&drv->tim_3, LPTIM_CHANNEL_1);
  } else {
    __HAL_LPTIM_CAPTURE_COMPARE_DISABLE(&drv->tim_3, LPTIM_CHANNEL_1);
  }

  __HAL_LPTIM_COMPARE_SET(&drv->tim_1, LPTIM_CHANNEL_1,
                          TIMER_PERIOD - (red * (TIMER_PERIOD) / 255));
  __HAL_LPTIM_COMPARE_SET(&drv->tim_3, LPTIM_CHANNEL_2,
                          TIMER_PERIOD - (green * (TIMER_PERIOD) / 255));
  __HAL_LPTIM_COMPARE_SET(&drv->tim_3, LPTIM_CHANNEL_1,
                          TIMER_PERIOD - (blue * (TIMER_PERIOD) / 255));
}

#endif
