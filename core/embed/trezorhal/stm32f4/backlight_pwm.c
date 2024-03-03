
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

int backlight_pwm_get(void) { return BACKLIGHT; }

void backlight_pwm_init(void) {
  // init peripherals
  BACKLIGHT_PWM_PORT_CLK_EN();
  BACKLIGHT_PWM_TIM_CLK_EN();

  GPIO_InitTypeDef GPIO_InitStructure;

  // LCD_PWM (backlight control)
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = BACKLIGHT_PWM_TIM_AF;
  GPIO_InitStructure.Pin = BACKLIGHT_PWM_PIN;
  HAL_GPIO_Init(BACKLIGHT_PWM_PORT, &GPIO_InitStructure);

  uint32_t tmpcr1 = 0;

  /* Select the Counter Mode */
  tmpcr1 |= TIM_COUNTERMODE_UP;

  /* Set the clock division */
  tmpcr1 |= (uint32_t)TIM_CLOCKDIVISION_DIV1;

  /* Set the auto-reload preload */
#ifdef STM32U5
  tmpcr1 |= TIM_AUTORELOAD_PRELOAD_DISABLE;
#endif

  BACKLIGHT_PWM_TIM->CR1 = tmpcr1;

  /* Set the Autoreload value */
  BACKLIGHT_PWM_TIM->ARR = (uint32_t)LED_PWM_TIM_PERIOD - 1;

  /* Set the Prescaler value */
  BACKLIGHT_PWM_TIM->PSC = LED_PWM_PRESCALER;

  /* Set the Repetition Counter value */
  BACKLIGHT_PWM_TIM->RCR = 0;

  /* Generate an update event to reload the Prescaler
     and the repetition counter (only for advanced timer) value immediately */
  BACKLIGHT_PWM_TIM->EGR = TIM_EGR_UG;

  pwm_period = LED_PWM_TIM_PERIOD;

  /* Set the Preload enable bit for channel1 */
  BACKLIGHT_PWM_TIM->CCMR1 |= TIM_CCMR1_OC1PE;

  /* Configure the Output Fast mode */
  BACKLIGHT_PWM_TIM->CCMR1 &= ~TIM_CCMR1_OC1FE;
  BACKLIGHT_PWM_TIM->CCMR1 |= TIM_OCFAST_DISABLE;

  uint32_t tmpccmrx;
  uint32_t tmpccer;
  uint32_t tmpcr2;

  /* Get the TIMx CCER register value */
  tmpccer = BACKLIGHT_PWM_TIM->CCER;

  /* Disable the Channel 1: Reset the CC1E Bit */
  BACKLIGHT_PWM_TIM->CCER &= ~TIM_CCER_CC1E;
  tmpccer |= TIM_CCER_CC1E;

  /* Get the TIMx CR2 register value */
  tmpcr2 = BACKLIGHT_PWM_TIM->CR2;

  /* Get the TIMx CCMR1 register value */
  tmpccmrx = BACKLIGHT_PWM_TIM->CCMR1;

  /* Reset the Output Compare Mode Bits */
  tmpccmrx &= ~TIM_CCMR1_OC1M;
  tmpccmrx &= ~TIM_CCMR1_CC1S;
  /* Select the Output Compare Mode */
  tmpccmrx |= BACKLIGHT_PWM_TIM_OCMODE;

  /* Reset the Output Polarity level */
  tmpccer &= ~TIM_CCER_CC1P;
  /* Set the Output Compare Polarity */
  tmpccer |= TIM_OCPOLARITY_HIGH;

  if (IS_TIM_CCXN_INSTANCE(BACKLIGHT_PWM_TIM, TIM_CHANNEL_1)) {
    /* Check parameters */
    assert_param(IS_TIM_OCN_POLARITY(OC_Config->OCNPolarity));

    /* Reset the Output N Polarity level */
    tmpccer &= ~TIM_CCER_CC1NP;
    /* Set the Output N Polarity */
    tmpccer |= TIM_OCNPOLARITY_HIGH;
    /* Set the Output N State */
    tmpccer |= TIM_CCER_CC1NE;
  }

  if (IS_TIM_BREAK_INSTANCE(BACKLIGHT_PWM_TIM)) {
    /* Check parameters */
    assert_param(IS_TIM_OCNIDLE_STATE(OC_Config->OCNIdleState));
    assert_param(IS_TIM_OCIDLE_STATE(OC_Config->OCIdleState));

    /* Reset the Output Compare and Output Compare N IDLE State */
    tmpcr2 &= ~TIM_CR2_OIS1;
    tmpcr2 &= ~TIM_CR2_OIS1N;
    /* Set the Output Idle state */
    tmpcr2 |= TIM_OCIDLESTATE_SET;
    /* Set the Output N Idle state */
    tmpcr2 |= TIM_OCNIDLESTATE_SET;
  }

  /* Write to TIMx CR2 */
  BACKLIGHT_PWM_TIM->CR2 = tmpcr2;

  /* Write to TIMx CCMR1 */
  BACKLIGHT_PWM_TIM->CCMR1 = tmpccmrx;

  /* Set the Capture Compare Register value */
  BACKLIGHT_PWM_TIM->CCR1 = 0;

  /* Write to TIMx CCER */
  BACKLIGHT_PWM_TIM->CCER = tmpccer;

  backlight_pwm_set(0);

  BACKLIGHT_PWM_TIM->BDTR |= TIM_BDTR_MOE;
  BACKLIGHT_PWM_TIM->CR1 |= TIM_CR1_CEN;
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
