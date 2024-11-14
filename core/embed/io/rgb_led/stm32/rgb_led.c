#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/rgb_led.h>

#define LED_SWITCHING_FREQUENCY_HZ 20000
#define TIMER_PERIOD (SystemCoreClock / LED_SWITCHING_FREQUENCY_HZ)

typedef struct {
  TIM_HandleTypeDef tim;
  bool initialized;
} rgb_led_t;

static rgb_led_t g_rgb_led = {0};

void rgb_led_init(void) {
  rgb_led_t* drv = &g_rgb_led;
  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(*drv));

  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_TIM4_CLK_ENABLE();
  __HAL_RCC_TIM4_FORCE_RESET();
  __HAL_RCC_TIM4_RELEASE_RESET();

  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Pin = GPIO_PIN_6 | GPIO_PIN_7 | GPIO_PIN_8;
  GPIO_InitStructure.Mode = GPIO_MODE_AF_OD;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = GPIO_AF2_TIM4;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

  drv->tim.State = HAL_TIM_STATE_RESET;
  drv->tim.Instance = TIM4;
  drv->tim.Init.Period = TIMER_PERIOD;
  drv->tim.Init.Prescaler = 0;
  drv->tim.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  drv->tim.Init.CounterMode = TIM_COUNTERMODE_UP;
  drv->tim.Init.RepetitionCounter = 0;
  HAL_TIM_PWM_Init(&drv->tim);

  // OC initialization
  TIM_OC_InitTypeDef OC_Init = {0};
  OC_Init.OCMode = TIM_OCMODE_PWM2;
  OC_Init.Pulse = 0;
  OC_Init.OCPolarity = TIM_OCPOLARITY_HIGH;
  OC_Init.OCFastMode = TIM_OCFAST_DISABLE;
  OC_Init.OCIdleState = TIM_OCIDLESTATE_RESET;
  HAL_TIM_PWM_ConfigChannel(&drv->tim, &OC_Init, TIM_CHANNEL_1);
  HAL_TIM_PWM_ConfigChannel(&drv->tim, &OC_Init, TIM_CHANNEL_2);
  HAL_TIM_PWM_ConfigChannel(&drv->tim, &OC_Init, TIM_CHANNEL_3);

  HAL_TIM_Base_Start(&drv->tim);

  HAL_TIM_PWM_Start(&drv->tim, TIM_CHANNEL_1);
  HAL_TIM_PWM_Start(&drv->tim, TIM_CHANNEL_2);
  HAL_TIM_PWM_Start(&drv->tim, TIM_CHANNEL_3);

  drv->initialized = true;
}

void rgb_led_deinit(void) {
  rgb_led_t* drv = &g_rgb_led;
  if (!drv->initialized) {
    return;
  }

  HAL_TIM_PWM_Stop(&drv->tim, TIM_CHANNEL_1);
  HAL_TIM_PWM_Stop(&drv->tim, TIM_CHANNEL_2);
  HAL_TIM_PWM_Stop(&drv->tim, TIM_CHANNEL_3);

  HAL_TIM_Base_Stop(&drv->tim);

  memset(drv, 0, sizeof(*drv));
  drv->initialized = false;
}

void rgb_led_set_color(uint32_t color) {
  rgb_led_t* drv = &g_rgb_led;
  if (!drv->initialized) {
    return;
  }

  TIM4->CCR1 = ((color >> 16) & 0xFF) * TIMER_PERIOD / 255;
  TIM4->CCR2 = ((color >> 8) & 0xFF) * TIMER_PERIOD / 255;
  TIM4->CCR3 = (color & 0xFF) * TIMER_PERIOD / 255;
}

#endif
