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

#include <sec/rng.h>
#include <sys/mpu.h>

#ifdef KERNEL_MODE

#define SAMPLES 110
#define TIMER_PERIOD 16640  // cca 10 KHz @ 180MHz

#if defined BOARDLOADER
#error Not implemented for boardloader!
#endif

__attribute__((section(".buf"))) uint32_t pwm_data[SAMPLES] = {0};

void consumption_mask_randomize() {
  for (int i = 0; i < SAMPLES; i++) {
    pwm_data[i] = rng_get() % TIMER_PERIOD;
  }
}

void consumption_mask_init(void) {
  consumption_mask_randomize();

  __HAL_RCC_GPIOC_CLK_ENABLE();
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_HIGH;
  GPIO_InitStructure.Alternate = GPIO_AF3_TIM8;
  GPIO_InitStructure.Pin = GPIO_PIN_6;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);

  __HAL_RCC_TIM8_CLK_ENABLE();
  TIM_HandleTypeDef TIM8_Handle = {0};
  TIM8_Handle.State = HAL_TIM_STATE_RESET;
  TIM8_Handle.Instance = TIM8;
  TIM8_Handle.Init.Period = TIMER_PERIOD;
  TIM8_Handle.Init.Prescaler = 0;
  TIM8_Handle.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  TIM8_Handle.Init.CounterMode = TIM_COUNTERMODE_UP;
  TIM8_Handle.Init.RepetitionCounter = 0;
  HAL_TIM_PWM_Init(&TIM8_Handle);

  TIM_OC_InitTypeDef TIM_OC_InitStructure = {0};
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
  DMA_InitStructure.Init.Mode = DMA_CIRCULAR;
  DMA_InitStructure.Init.PeriphBurst = DMA_PBURST_SINGLE;
  DMA_InitStructure.Init.PeriphDataAlignment = DMA_PDATAALIGN_WORD;
  DMA_InitStructure.Init.PeriphInc = DMA_PINC_DISABLE;
  DMA_InitStructure.Init.Priority = DMA_PRIORITY_HIGH;
  HAL_DMA_Init(&DMA_InitStructure);

  TIM4->CR2 |= TIM_CR2_MMS_1;    // update event as TRGO
  TIM8->CR2 |= TIM_CR2_CCPC;     // preloading CCR register
  TIM8->CR2 |= TIM_CR2_CCUS;     // preload when TRGI
  TIM8->DIER |= TIM_DMA_UPDATE;  // allow DMA request from update event
  TIM8->CCR1 = 0;

  HAL_Delay(1);

  DMA2->LIFCR |= 0xFC0;
  DMA2_Stream1->M0AR = (uint32_t)pwm_data;
  DMA2_Stream1->PAR = (uint32_t)&TIM8->CCR1;
  DMA2_Stream1->NDTR = SAMPLES;
  DMA2_Stream1->CR |= DMA_SxCR_EN;

  HAL_TIM_Base_Start(&TIM8_Handle);
  HAL_TIM_PWM_Start(&TIM8_Handle, TIM_CHANNEL_1);
}

#endif  // KERNEL_MODE
