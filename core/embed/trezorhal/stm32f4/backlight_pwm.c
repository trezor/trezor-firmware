
#include "backlight_pwm.h"

#include STM32_HAL_H
#include TREZOR_BOARD

#define LED_PWM_TIM_PERIOD \
  (255)  // little less than 4kHz with PSC = (SystemCoreClock / 1000000) - 1)
#define LED_PWM_SLOW_TIM_PERIOD \
  (10000)  // about 10Hz (with PSC = (SystemCoreClock / 1000000) - 1)

static int BACKLIGHT = -1;

static int pwm_period = LED_PWM_TIM_PERIOD;

int backlight_pwm_set(int val) {
  if (BACKLIGHT != val && val >= 0 && val <= 255) {
    BACKLIGHT = val;
    TIM1->CCR1 = pwm_period * val / 255;
  }
  return BACKLIGHT;
}

void backlight_pwm_init(void) {
  // init peripherals
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_TIM1_CLK_ENABLE();

  GPIO_InitTypeDef GPIO_InitStructure;

  // LCD_PWM/PA7 (backlight control)
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = GPIO_AF1_TIM1;
  GPIO_InitStructure.Pin = GPIO_PIN_7;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  // enable PWM timer
  TIM_HandleTypeDef TIM1_Handle;
  TIM1_Handle.Instance = TIM1;
  TIM1_Handle.Init.Period = LED_PWM_TIM_PERIOD - 1;
  // TIM1/APB2 source frequency equals to SystemCoreClock in our configuration,
  // we want 1 MHz
  TIM1_Handle.Init.Prescaler = SystemCoreClock / 1000000 - 1;
  TIM1_Handle.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  TIM1_Handle.Init.CounterMode = TIM_COUNTERMODE_UP;
  TIM1_Handle.Init.RepetitionCounter = 0;
  HAL_TIM_PWM_Init(&TIM1_Handle);
  pwm_period = LED_PWM_TIM_PERIOD;

  TIM_OC_InitTypeDef TIM_OC_InitStructure;
  TIM_OC_InitStructure.Pulse = 0;
  TIM_OC_InitStructure.OCMode = TIM_OCMODE_PWM2;
  TIM_OC_InitStructure.OCPolarity = TIM_OCPOLARITY_HIGH;
  TIM_OC_InitStructure.OCFastMode = TIM_OCFAST_DISABLE;
  TIM_OC_InitStructure.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  TIM_OC_InitStructure.OCIdleState = TIM_OCIDLESTATE_SET;
  TIM_OC_InitStructure.OCNIdleState = TIM_OCNIDLESTATE_SET;
  HAL_TIM_PWM_ConfigChannel(&TIM1_Handle, &TIM_OC_InitStructure, TIM_CHANNEL_1);

  backlight_pwm_set(0);

  HAL_TIM_PWM_Start(&TIM1_Handle, TIM_CHANNEL_1);
  HAL_TIMEx_PWMN_Start(&TIM1_Handle, TIM_CHANNEL_1);
}

void backlight_pwm_reinit(void) {
  uint32_t prev_arr = TIM1->ARR;
  uint32_t prev_ccr1 = TIM1->CCR1;

  uint8_t prev_val = (prev_ccr1 * 255) / prev_arr;
  BACKLIGHT = prev_val;

  pwm_period = LED_PWM_TIM_PERIOD;
  TIM1->CR1 |= TIM_CR1_ARPE;
  TIM1->CR2 |= TIM_CR2_CCPC;
  TIM1->CCR1 = pwm_period * prev_val / 255;
  TIM1->ARR = LED_PWM_TIM_PERIOD - 1;
}

void backlight_pwm_set_slow(void) {
  uint32_t prev_arr = TIM1->ARR;
  uint32_t prev_ccr1 = TIM1->CCR1;

  uint8_t prev_val = (prev_ccr1 * 255) / prev_arr;

  pwm_period = LED_PWM_SLOW_TIM_PERIOD;
  TIM1->CR1 |= TIM_CR1_ARPE;
  TIM1->CR2 |= TIM_CR2_CCPC;
  TIM1->ARR = LED_PWM_SLOW_TIM_PERIOD - 1;
  TIM1->CCR1 = pwm_period * prev_val / 255;
}
