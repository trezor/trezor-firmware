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

#include <stdbool.h>
#include <string.h>

#include "backlight_pwm.h"
#include "common.h"

#include STM32_HAL_H
#include TREZOR_BOARD

// Requested PWM Timer clock frequency [Hz]
#define TIM_FREQ 10000000
// Prescaler divider for the PWM Timer
#define LED_PWM_PRESCALER (SystemCoreClock / TIM_FREQ - 1)
// Period of the PWM Timer
#define LED_PWM_TIM_PERIOD (TIM_FREQ / BACKLIGHT_PWM_FREQ)

// Backlight driver state
typedef struct {
  // Set if driver is initialized
  bool initialized;
  // Current backlight level in range 0-255
  int current_level;

} backlight_driver_t;

// Backlight driver instance
static backlight_driver_t g_backlight_driver = {
    .initialized = false,
};

void backlight_pwm_init(backlight_action_t action) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(backlight_driver_t));

  int initial_level = 0;

  if (action == BACKLIGHT_RETAIN) {
    // We expect the BACKLIGHT_PWM_TIM to be already initialized
    // (e.g. by the bootloader or boardloader)
    uint32_t prev_arr = BACKLIGHT_PWM_TIM->ARR;
    uint32_t prev_ccr1 = BACKLIGHT_PWM_TIM->BACKLIGHT_PWM_TIM_CCR;

    initial_level = (prev_ccr1 * 255) / (prev_arr + 1);
    if (initial_level > 255) {
      initial_level = 255;
    }
  }

  // Enable peripheral clocks
  BACKLIGHT_PWM_PORT_CLK_EN();
  BACKLIGHT_PWM_TIM_CLK_EN();

  // Initialize PWM GPIO
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = BACKLIGHT_PWM_TIM_AF;
  GPIO_InitStructure.Pin = BACKLIGHT_PWM_PIN;
  HAL_GPIO_Init(BACKLIGHT_PWM_PORT, &GPIO_InitStructure);

  // Initialize PWM timer

  uint32_t tmpcr1 = 0;

  // Select the Counter Mode
  tmpcr1 |= TIM_COUNTERMODE_UP;

  // Set the clock division
  tmpcr1 |= (uint32_t)TIM_CLOCKDIVISION_DIV1;

  // Set the auto-reload preload
#ifdef STM32U5
  tmpcr1 |= TIM_AUTORELOAD_PRELOAD_DISABLE;
#endif

  BACKLIGHT_PWM_TIM->CR1 = tmpcr1;

  // Set the Autoreload value
  BACKLIGHT_PWM_TIM->ARR = (uint32_t)LED_PWM_TIM_PERIOD - 1;

  // Set the Prescaler value
  BACKLIGHT_PWM_TIM->PSC = LED_PWM_PRESCALER;

  // Set the Repetition Counter value
  BACKLIGHT_PWM_TIM->RCR = 0;

  // Generate an update event to reload the Prescaler
  // and the repetition counter (only for advanced timer) value immediately
  BACKLIGHT_PWM_TIM->EGR = TIM_EGR_UG;

  // Set the Preload enable bit for channel1
  BACKLIGHT_PWM_TIM->CCMR1 |= TIM_CCMR1_OC1PE;

  // Configure the Output Fast mode
  BACKLIGHT_PWM_TIM->CCMR1 &= ~TIM_CCMR1_OC1FE;
  BACKLIGHT_PWM_TIM->CCMR1 |= TIM_OCFAST_DISABLE;

  uint32_t tmpccmrx;
  uint32_t tmpccer;
  uint32_t tmpcr2;

  // Get the TIMx CCER register value
  tmpccer = BACKLIGHT_PWM_TIM->CCER;

  // Disable the Channel 1: Reset the CC1E Bit
  BACKLIGHT_PWM_TIM->CCER &= ~TIM_CCER_CC1E;
  tmpccer |= TIM_CCER_CC1E;

  // Get the TIMx CR2 register value
  tmpcr2 = BACKLIGHT_PWM_TIM->CR2;

  // Get the TIMx CCMR1 register value
  tmpccmrx = BACKLIGHT_PWM_TIM->CCMR1;

  // Reset the Output Compare Mode Bits
  tmpccmrx &= ~TIM_CCMR1_OC1M;
  tmpccmrx &= ~TIM_CCMR1_CC1S;
  // Select the Output Compare Mode
  tmpccmrx |= BACKLIGHT_PWM_TIM_OCMODE;

  // Reset the Output Polarity level
  tmpccer &= ~TIM_CCER_CC1P;
  // Set the Output Compare Polarity
  tmpccer |= TIM_OCPOLARITY_HIGH;

  if (IS_TIM_CCXN_INSTANCE(BACKLIGHT_PWM_TIM, TIM_CHANNEL_1)) {
    // Check parameters
    assert_param(IS_TIM_OCN_POLARITY(OC_Config->OCNPolarity));

    // Reset the Output N Polarity level
    tmpccer &= ~TIM_CCER_CC1NP;
    // Set the Output N Polarity
    tmpccer |= TIM_OCNPOLARITY_HIGH;
    // Set the Output N State
    tmpccer |= TIM_CCER_CC1NE;
  }

  if (IS_TIM_BREAK_INSTANCE(BACKLIGHT_PWM_TIM)) {
    // Check parameters
    assert_param(IS_TIM_OCNIDLE_STATE(OC_Config->OCNIdleState));
    assert_param(IS_TIM_OCIDLE_STATE(OC_Config->OCIdleState));

    // Reset the Output Compare and Output Compare N IDLE State
    tmpcr2 &= ~TIM_CR2_OIS1;
    tmpcr2 &= ~TIM_CR2_OIS1N;
    // Set the Output Idle state
    tmpcr2 |= TIM_OCIDLESTATE_SET;
    // Set the Output N Idle state
    tmpcr2 |= TIM_OCNIDLESTATE_SET;
  }

  // Write to TIMx CR2
  BACKLIGHT_PWM_TIM->CR2 = tmpcr2;
  // Write to TIMx CCMR1
  BACKLIGHT_PWM_TIM->CCMR1 = tmpccmrx;
  // Set the Capture Compare Register value
  BACKLIGHT_PWM_TIM->CCR1 = 0;
  // Write to TIMx CCER
  BACKLIGHT_PWM_TIM->CCER = tmpccer;

  BACKLIGHT_PWM_TIM->BDTR |= TIM_BDTR_MOE;
  BACKLIGHT_PWM_TIM->CR1 |= TIM_CR1_CEN;

  drv->initialized = true;

  backlight_pwm_set(initial_level);
}

void backlight_pwm_deinit(backlight_action_t action) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (!drv->initialized) {
    return;
  }

  if (action == BACKLIGHT_RETAIN) {
    // We keep both the GPIO and the timer running

#ifdef TREZOR_MODEL_T
    // This code here is for backward compatibility with the old
    // bootloader that used a different PWM settings.

// about 10Hz (with PSC = (SystemCoreClock / 1000000) - 1)
#define LED_PWM_SLOW_TIM_PERIOD (10000)
#define LED_PWM_PRESCALER_SLOW (SystemCoreClock / 1000000 - 1)  // 1 MHz

    BACKLIGHT_PWM_TIM->PSC = LED_PWM_PRESCALER_SLOW;
    BACKLIGHT_PWM_TIM->CR1 |= TIM_CR1_ARPE;
    BACKLIGHT_PWM_TIM->CR2 |= TIM_CR2_CCPC;
    BACKLIGHT_PWM_TIM->ARR = LED_PWM_SLOW_TIM_PERIOD - 1;
    BACKLIGHT_PWM_TIM->BACKLIGHT_PWM_TIM_CCR =
        (LED_PWM_SLOW_TIM_PERIOD * drv->current_level) / 255;
#endif
  } else {
    // TODO: deinitialize GPIOs and the TIMER
  }

  drv->initialized = false;
}

// Generate a pulse on the backlight control pin to wake up the TPS61043
static void backlight_pwm_wakeup_pulse(void) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};

  HAL_GPIO_WritePin(BACKLIGHT_PWM_PORT, BACKLIGHT_PWM_PIN, GPIO_PIN_SET);

  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Pin = BACKLIGHT_PWM_PIN;
  HAL_GPIO_Init(BACKLIGHT_PWM_PORT, &GPIO_InitStructure);

  hal_delay_us(500);

  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = BACKLIGHT_PWM_TIM_AF;
  GPIO_InitStructure.Pin = BACKLIGHT_PWM_PIN;
  HAL_GPIO_Init(BACKLIGHT_PWM_PORT, &GPIO_InitStructure);
}

int backlight_pwm_set(int level) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (!drv->initialized) {
    return 0;
  }

  if (level >= 0 && level <= 255) {
    // TPS61043 goes to shutdown when duty cycle is 0 (after 32ms),
    // so we need to set GPIO to high for at least 500us
    // to wake it up.
    if (BACKLIGHT_PWM_TIM->BACKLIGHT_PWM_TIM_CCR == 0 && level != 0) {
      backlight_pwm_wakeup_pulse();
    }

    BACKLIGHT_PWM_TIM->CCR1 = (LED_PWM_TIM_PERIOD * level) / 255;

    drv->current_level = level;
  }

  return drv->current_level;
}

int backlight_pwm_get(void) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->current_level;
}
