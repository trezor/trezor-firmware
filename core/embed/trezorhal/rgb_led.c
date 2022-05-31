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

/*
 * Implements driver for IN-PI15TAT5R5G5B 1515 RGB LED 4-Pin with Integrated IC
 *
 * The communication protocol prescribes encoding of 0 as a short pulse
 * (200-400ns) and 1 as a long pulse (580ns-1us). Before sending the data reset
 * period is required: at least 80us without pulses.
 *
 * The data send to LED is 24 bit RGB. These data are encoded as the long and
 * short pulses.
 *
 * After data is sent, the PWM compare level is set to 0 to stop pulsing.
 *
 * For pulse generation with precise timing PWM implemented via TIM8 is used.
 * To avoid any glitches when setting the CCR register, preloading is used,
 * therefore sync with TIM4 is needed (to generate COM event on TIM update)
 *
 * DMA is used to set the CCR register to avoid need for interrupt after every
 * bit is sent.
 */

#include "common.h"

#include STM32_HAL_H

#define RESET_DATA_LEN 18  // >80us no pulse before sending data
#define DATA_LEN 25        // 24 RGB bits and a final zero
#define TIMER_PERIOD 832   // cca 200 KHz @ 180MHz
#define BIT_0_LEN 52       // 312ns
#define BIT_1_LEN 125      // 750ns

#if defined BOARDLOADER
#error Not implemented for boardloader!
#endif

#if defined BOOTLOADER
__attribute__((section(".buf")))
#endif
uint32_t rgb_led_data[RESET_DATA_LEN + DATA_LEN] = {0};

static void rgb_led_set(uint32_t* start, uint8_t color) {
  for (int i = 0; i < 8; i++) {
    uint32_t bit_mask = (1 << (7 - i));
    if (color & bit_mask) {
      start[i] = BIT_1_LEN;
    } else {
      start[i] = BIT_0_LEN;
    }
  }
}

void rgb_led_set_color(uint32_t color) {
  uint16_t red = (0xFF0000 & color) >> 16;
  uint16_t green = (0xFF00 & color) >> 8;
  uint16_t blue = (0xFF & color);

  // wait for previous command to finish
  while (DMA2_Stream1->CR & DMA_SxCR_EN)
    ;

  rgb_led_set(&rgb_led_data[RESET_DATA_LEN + 0], green);
  rgb_led_set(&rgb_led_data[RESET_DATA_LEN + 8], red);
  rgb_led_set(&rgb_led_data[RESET_DATA_LEN + 16], blue);
  rgb_led_data[RESET_DATA_LEN + DATA_LEN - 1] = 0;

  DMA2->LIFCR |= 0xFC0;
  DMA2_Stream1->M0AR = (uint32_t)rgb_led_data;
  DMA2_Stream1->PAR = (uint32_t)&TIM8->CCR1;
  DMA2_Stream1->NDTR = RESET_DATA_LEN + DATA_LEN;
  DMA2_Stream1->CR |= DMA_SxCR_EN;
}

void rgb_led_init(void) {
  __HAL_RCC_GPIOC_CLK_ENABLE();
  GPIO_InitTypeDef GPIO_InitStructure;
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_HIGH;
  GPIO_InitStructure.Alternate = GPIO_AF3_TIM8;
  GPIO_InitStructure.Pin = GPIO_PIN_6;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);

  __HAL_RCC_TIM4_CLK_ENABLE();
  TIM_HandleTypeDef TIM4_Handle;
  TIM4_Handle.State = HAL_TIM_STATE_RESET;
  TIM4_Handle.Instance = TIM4;
  TIM4_Handle.Init.Period = TIMER_PERIOD;
  TIM4_Handle.Init.Prescaler = 0;
  TIM4_Handle.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  TIM4_Handle.Init.CounterMode = TIM_COUNTERMODE_UP;
  TIM4_Handle.Init.RepetitionCounter = 0;
  HAL_TIM_PWM_Init(&TIM4_Handle);

  __HAL_RCC_TIM8_CLK_ENABLE();
  TIM_HandleTypeDef TIM8_Handle;
  TIM8_Handle.State = HAL_TIM_STATE_RESET;
  TIM8_Handle.Instance = TIM8;
  TIM8_Handle.Init.Period = TIMER_PERIOD;
  TIM8_Handle.Init.Prescaler = 0;
  TIM8_Handle.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  TIM8_Handle.Init.CounterMode = TIM_COUNTERMODE_UP;
  TIM8_Handle.Init.RepetitionCounter = 0;
  HAL_TIM_PWM_Init(&TIM8_Handle);

  TIM_OC_InitTypeDef TIM_OC_InitStructure;
  TIM_OC_InitStructure.Pulse = 0;
  TIM_OC_InitStructure.OCMode = TIM_OCMODE_PWM1;
  TIM_OC_InitStructure.OCPolarity = TIM_OCPOLARITY_LOW;
  TIM_OC_InitStructure.OCFastMode = TIM_OCFAST_DISABLE;
  TIM_OC_InitStructure.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  TIM_OC_InitStructure.OCIdleState = TIM_OCIDLESTATE_SET;
  TIM_OC_InitStructure.OCNIdleState = TIM_OCNIDLESTATE_SET;
  HAL_TIM_PWM_ConfigChannel(&TIM8_Handle, &TIM_OC_InitStructure, TIM_CHANNEL_1);

  __HAL_RCC_DMA2_CLK_ENABLE();
  DMA_HandleTypeDef DMA_InitStructure = {0};
  DMA_InitStructure.Instance = DMA2_Stream1;
  DMA_InitStructure.State = HAL_DMA_STATE_RESET;
  DMA_InitStructure.Init.Channel = DMA_CHANNEL_7;
  DMA_InitStructure.Init.Direction = DMA_MEMORY_TO_PERIPH;
  DMA_InitStructure.Init.FIFOMode = DMA_FIFOMODE_DISABLE;
  DMA_InitStructure.Init.FIFOThreshold = DMA_FIFO_THRESHOLD_1QUARTERFULL;
  DMA_InitStructure.Init.MemBurst = DMA_MBURST_SINGLE;
  DMA_InitStructure.Init.MemDataAlignment = DMA_MDATAALIGN_WORD;
  DMA_InitStructure.Init.MemInc = DMA_MINC_ENABLE;
  DMA_InitStructure.Init.Mode = DMA_NORMAL;
  DMA_InitStructure.Init.PeriphBurst = DMA_PBURST_SINGLE;
  DMA_InitStructure.Init.PeriphDataAlignment = DMA_PDATAALIGN_WORD;
  DMA_InitStructure.Init.PeriphInc = DMA_PINC_DISABLE;
  DMA_InitStructure.Init.Priority = DMA_PRIORITY_HIGH;
  HAL_DMA_Init(&DMA_InitStructure);

  TIM4->CR2 |= TIM_CR2_MMS_1;  // update event as TRGO

  TIM8->CR2 |= TIM_CR2_CCPC;     // preloading CCR register
  TIM8->CR2 |= TIM_CR2_CCUS;     // preload when TRGI
  TIM8->SMCR |= TIM_SMCR_SMS_2;  // reset mode - sync timers
  TIM8->SMCR |= TIM_SMCR_TS_1;   // sync with TIM 4

  TIM8->DIER |= TIM_DMA_UPDATE;  // allow DMA request from update event
  TIM8->CCR1 = 0;

  // NVIC configuration for SDIO interrupts
  HAL_TIM_Base_Start(&TIM4_Handle);
  HAL_TIM_Base_Start(&TIM8_Handle);
  HAL_TIM_PWM_Start(&TIM8_Handle, TIM_CHANNEL_1);

  // turns off the LED
  rgb_led_set_color(0x000000);
}
