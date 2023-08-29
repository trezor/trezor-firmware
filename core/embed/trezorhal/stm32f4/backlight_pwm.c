
#include "backlight_pwm.h"

#include STM32_HAL_H
#include TREZOR_BOARD

#define TIM_FREQ 1000000

#define LED_PWM_PRESCALER (SystemCoreClock / TIM_FREQ - 1)  // 1 MHz

#define LED_PWM_TIM_PERIOD (TIM_FREQ / BACKLIGHT_PWM_FREQ)

static int BACKLIGHT = -1;

static int pwm_period = 0;

int backlight_pwm_set(int val) {
  if (BACKLIGHT != val && val >= 0 && val <= 255) {
    BACKLIGHT = val;
    BACKLIGHT_PWM_TIM->CCR1 = pwm_period * val / 255;
  }
  return BACKLIGHT;
}

void backlight_pwm_init(void) {
  // init peripherals
  BACKLIGHT_PWM_PORT_CLK_EN();
  BACKLIGHT_PWM_TIM_CLK_EN();

  GPIO_InitTypeDef GPIO_InitStructure;

  // LCD_PWM/PA7 (backlight control)
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = BACKLIGHT_PWM_TIM_AF;
  GPIO_InitStructure.Pin = BACKLIGHT_PWM_PIN;
  HAL_GPIO_Init(BACKLIGHT_PWM_PORT, &GPIO_InitStructure);

  // enable PWM timer
  TIM_HandleTypeDef TIM_Handle;
  TIM_Handle.Instance = BACKLIGHT_PWM_TIM;
  TIM_Handle.Init.Period = LED_PWM_TIM_PERIOD - 1;
  // TIM1/APB2 source frequency equals to SystemCoreClock in our configuration,
  // we want 1 MHz
  TIM_Handle.Init.Prescaler = LED_PWM_PRESCALER;
  TIM_Handle.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  TIM_Handle.Init.CounterMode = TIM_COUNTERMODE_UP;
  TIM_Handle.Init.RepetitionCounter = 0;
  HAL_TIM_PWM_Init(&TIM_Handle);
  pwm_period = LED_PWM_TIM_PERIOD;

  TIM_OC_InitTypeDef TIM_OC_InitStructure;
  TIM_OC_InitStructure.Pulse = 0;
  TIM_OC_InitStructure.OCMode = BACKLIGHT_PWM_TIM_OCMODE;
  TIM_OC_InitStructure.OCPolarity = TIM_OCPOLARITY_HIGH;
  TIM_OC_InitStructure.OCFastMode = TIM_OCFAST_DISABLE;
  TIM_OC_InitStructure.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  TIM_OC_InitStructure.OCIdleState = TIM_OCIDLESTATE_SET;
  TIM_OC_InitStructure.OCNIdleState = TIM_OCNIDLESTATE_SET;
  HAL_TIM_PWM_ConfigChannel(&TIM_Handle, &TIM_OC_InitStructure,
                            BACKLIGHT_PWM_TIM_CHANNEL);

  backlight_pwm_set(0);

  HAL_TIM_PWM_Start(&TIM_Handle, BACKLIGHT_PWM_TIM_CHANNEL);
  HAL_TIMEx_PWMN_Start(&TIM_Handle, BACKLIGHT_PWM_TIM_CHANNEL);
}

void backlight_pwm_reinit(void) {
  uint32_t prev_arr = BACKLIGHT_PWM_TIM->ARR;
  uint32_t prev_ccr1 = BACKLIGHT_PWM_TIM->BACKLIGHT_PWM_TIM_CCR;

  uint8_t prev_val = (prev_ccr1 * 255) / prev_arr;
  BACKLIGHT = prev_val;

  pwm_period = LED_PWM_TIM_PERIOD;
  BACKLIGHT_PWM_TIM->CR1 |= TIM_CR1_ARPE;
  BACKLIGHT_PWM_TIM->CR2 |= TIM_CR2_CCPC;
  BACKLIGHT_PWM_TIM->BACKLIGHT_PWM_TIM_CCR = pwm_period * prev_val / 255;
  BACKLIGHT_PWM_TIM->ARR = LED_PWM_TIM_PERIOD - 1;
}

#ifdef TREZOR_MODEL_T

#define LED_PWM_SLOW_TIM_PERIOD \
  (10000)  // about 10Hz (with PSC = (SystemCoreClock / 1000000) - 1)

void backlight_pwm_set_slow(void) {
  uint32_t prev_arr = BACKLIGHT_PWM_TIM->ARR;
  uint32_t prev_ccr1 = BACKLIGHT_PWM_TIM->CCR1;

  uint8_t prev_val = (prev_ccr1 * 255) / prev_arr;

  pwm_period = LED_PWM_SLOW_TIM_PERIOD;
  BACKLIGHT_PWM_TIM->CR1 |= TIM_CR1_ARPE;
  BACKLIGHT_PWM_TIM->CR2 |= TIM_CR2_CCPC;
  BACKLIGHT_PWM_TIM->ARR = LED_PWM_SLOW_TIM_PERIOD - 1;
  BACKLIGHT_PWM_TIM->BACKLIGHT_PWM_TIM_CCR = pwm_period * prev_val / 255;
}
#endif
