#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/rgb_led.h>

#define LED_SWITCHING_FREQUENCY_HZ 200
#define TIMER_PERIOD ((32768 * 2) / LED_SWITCHING_FREQUENCY_HZ)

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

void rgb_led_init(void) {
  rgb_led_t* drv = &g_rgb_led;
  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(*drv));

  // enable LSE clock
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_LSE;
  RCC_OscInitStruct.LSEState = RCC_LSE_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
  HAL_RCC_OscConfig(&RCC_OscInitStruct);

  // select LSE as LPTIM clock source
  RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};
  PeriphClkInitStruct.PeriphClockSelection =
      RCC_PERIPHCLK_LPTIM1 | RCC_PERIPHCLK_LPTIM34;
  PeriphClkInitStruct.Lptim1ClockSelection = RCC_LPTIM1CLKSOURCE_LSE;
  PeriphClkInitStruct.Lptim34ClockSelection = RCC_LPTIM34CLKSOURCE_LSE;
  HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct);

  __HAL_RCC_LPTIM1_CLK_ENABLE();
  __HAL_RCC_LPTIM1_FORCE_RESET();
  __HAL_RCC_LPTIM1_RELEASE_RESET();

  __HAL_RCC_LPTIM3_CLK_ENABLE();
  __HAL_RCC_LPTIM3_FORCE_RESET();
  __HAL_RCC_LPTIM3_RELEASE_RESET();

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

  HAL_LPTIM_PWM_Start(&drv->tim_1, LPTIM_CHANNEL_1);
  HAL_LPTIM_PWM_Start(&drv->tim_3, LPTIM_CHANNEL_1);
  HAL_LPTIM_PWM_Start(&drv->tim_3, LPTIM_CHANNEL_2);

  drv->initialized = true;
}

void rgb_led_deinit(void) {
  rgb_led_t* drv = &g_rgb_led;
  if (!drv->initialized) {
    return;
  }

  HAL_LPTIM_PWM_Stop(&drv->tim_1, LPTIM_CHANNEL_1);
  HAL_LPTIM_PWM_Stop(&drv->tim_3, LPTIM_CHANNEL_1);
  HAL_LPTIM_PWM_Stop(&drv->tim_3, LPTIM_CHANNEL_2);

  HAL_LPTIM_Counter_Stop(&drv->tim_1);
  HAL_LPTIM_Counter_Stop(&drv->tim_3);

  memset(drv, 0, sizeof(*drv));
  drv->initialized = false;
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
    LPTIM1->CCMR1 |= LPTIM_CCMR1_CC1E;
  } else {
    LPTIM1->CCMR1 &= ~LPTIM_CCMR1_CC1E;
  }

  if (green != 0) {
    LPTIM3->CCMR1 |= LPTIM_CCMR1_CC2E;
  } else {
    LPTIM3->CCMR1 &= ~LPTIM_CCMR1_CC2E;
  }

  if (blue != 0) {
    LPTIM3->CCMR1 |= LPTIM_CCMR1_CC1E;
  } else {
    LPTIM3->CCMR1 &= ~LPTIM_CCMR1_CC1E;
  }

  LPTIM1->CCR1 = TIMER_PERIOD - (red * (TIMER_PERIOD) / 255);
  LPTIM3->CCR2 = TIMER_PERIOD - (green * (TIMER_PERIOD) / 255);
  LPTIM3->CCR1 = TIMER_PERIOD - (blue * (TIMER_PERIOD) / 255);
}

#endif
