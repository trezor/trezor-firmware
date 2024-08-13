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

#include STM32_HAL_H
#include "rng.h"

#ifdef KERNEL_MODE

#define SAMPLES 119
#define TIMER_PERIOD 16000  // cca 10 KHz @ 160MHz

uint32_t pwm_data[SAMPLES] = {0};

static DMA_NodeTypeDef Node1;
static DMA_QListTypeDef Queue;

void consumption_mask_randomize() {
  for (int i = 0; i < SAMPLES; i++) {
    pwm_data[i] = rng_get() % TIMER_PERIOD;
  }
}

void consumption_mask_init(void) {
  consumption_mask_randomize();

  __HAL_RCC_GPIOA_CLK_ENABLE();
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Alternate = GPIO_AF1_TIM2;
  GPIO_InitStructure.Pin = GPIO_PIN_5;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  __HAL_RCC_TIM2_CLK_ENABLE();
  TIM_HandleTypeDef TIM2_Handle = {0};
  TIM2_Handle.State = HAL_TIM_STATE_RESET;
  TIM2_Handle.Instance = TIM2;
  TIM2_Handle.Init.Period = TIMER_PERIOD;
  TIM2_Handle.Init.Prescaler = 0;
  TIM2_Handle.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  TIM2_Handle.Init.CounterMode = TIM_COUNTERMODE_UP;
  TIM2_Handle.Init.RepetitionCounter = 0;
  HAL_TIM_PWM_Init(&TIM2_Handle);

  TIM_OC_InitTypeDef TIM_OC_InitStructure = {0};
  TIM_OC_InitStructure.Pulse = 0;
  TIM_OC_InitStructure.OCMode = TIM_OCMODE_PWM1;
  TIM_OC_InitStructure.OCPolarity = TIM_OCPOLARITY_LOW;
  TIM_OC_InitStructure.OCFastMode = TIM_OCFAST_DISABLE;
  TIM_OC_InitStructure.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  TIM_OC_InitStructure.OCIdleState = TIM_OCIDLESTATE_SET;
  TIM_OC_InitStructure.OCNIdleState = TIM_OCNIDLESTATE_SET;
  HAL_TIM_PWM_ConfigChannel(&TIM2_Handle, &TIM_OC_InitStructure, TIM_CHANNEL_1);

  __HAL_RCC_GPDMA1_CLK_ENABLE();
  DMA_HandleTypeDef dma_handle = {0};

  /* USER CODE END GPDMA1_Init 1 */
  dma_handle.Instance = GPDMA1_Channel1;
  dma_handle.InitLinkedList.Priority = DMA_HIGH_PRIORITY;
  dma_handle.InitLinkedList.LinkStepMode = DMA_LSM_FULL_EXECUTION;
  dma_handle.InitLinkedList.LinkAllocatedPort = DMA_LINK_ALLOCATED_PORT1;
  dma_handle.InitLinkedList.TransferEventMode = DMA_TCEM_LAST_LL_ITEM_TRANSFER;
  dma_handle.InitLinkedList.LinkedListMode = DMA_LINKEDLIST_CIRCULAR;
  HAL_DMAEx_List_Init(&dma_handle);

  HAL_DMA_ConfigChannelAttributes(&dma_handle, DMA_CHANNEL_SEC |
                                                   DMA_CHANNEL_SRC_SEC |
                                                   DMA_CHANNEL_DEST_SEC);

  /* DMA node configuration declaration */
  DMA_NodeConfTypeDef pNodeConfig = {0};

  /* Set node configuration ################################################*/
  pNodeConfig.NodeType = DMA_GPDMA_LINEAR_NODE;
  pNodeConfig.Init.Request = GPDMA1_REQUEST_TIM2_UP;
  pNodeConfig.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  pNodeConfig.Init.Direction = DMA_MEMORY_TO_PERIPH;
  pNodeConfig.Init.SrcInc = DMA_SINC_INCREMENTED;
  pNodeConfig.Init.DestInc = DMA_DINC_FIXED;
  pNodeConfig.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_WORD;
  pNodeConfig.Init.DestDataWidth = DMA_DEST_DATAWIDTH_WORD;
  pNodeConfig.Init.SrcBurstLength = 1;
  pNodeConfig.Init.DestBurstLength = 1;
  pNodeConfig.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT0 | DMA_DEST_ALLOCATED_PORT0;
  pNodeConfig.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  pNodeConfig.RepeatBlockConfig.RepeatCount = 1;
  pNodeConfig.RepeatBlockConfig.SrcAddrOffset = 0;
  pNodeConfig.RepeatBlockConfig.DestAddrOffset = 0;
  pNodeConfig.RepeatBlockConfig.BlkSrcAddrOffset = 0;
  pNodeConfig.RepeatBlockConfig.BlkDestAddrOffset = 0;
  pNodeConfig.TriggerConfig.TriggerPolarity = DMA_TRIG_POLARITY_MASKED;
  pNodeConfig.DataHandlingConfig.DataExchange = DMA_EXCHANGE_NONE;
  pNodeConfig.DataHandlingConfig.DataAlignment = DMA_DATA_RIGHTALIGN_ZEROPADDED;
  pNodeConfig.SrcAddress = (uint32_t)pwm_data;
  pNodeConfig.DstAddress = (uint32_t)&TIM2->CCR1;
  pNodeConfig.DataSize = SAMPLES * sizeof(uint32_t);
  pNodeConfig.DestSecure = DMA_CHANNEL_DEST_SEC;
  pNodeConfig.SrcSecure = DMA_CHANNEL_SRC_SEC;

  /* Build Node1 Node */
  HAL_DMAEx_List_BuildNode(&pNodeConfig, &Node1);

  /* Insert Node1 to Queue */
  HAL_DMAEx_List_InsertNode_Tail(&Queue, &Node1);

  HAL_DMAEx_List_SetCircularModeConfig(&Queue, &Node1);
  HAL_DMAEx_List_SetCircularMode(&Queue);

  /* Link created queue to DMA channel #######################################*/
  HAL_DMAEx_List_LinkQ(&dma_handle, &Queue);

  TIM2->CR2 |= TIM_CR2_CCPC;     // preloading CCR register
  TIM2->CR2 |= TIM_CR2_CCUS;     // preload when TRGI
  TIM2->DIER |= TIM_DMA_UPDATE;  // allow DMA request from update event
  TIM2->CCR1 = 0;

  HAL_Delay(1);

  HAL_TIM_Base_Start(&TIM2_Handle);
  HAL_TIM_PWM_Start(&TIM2_Handle, TIM_CHANNEL_1);

  HAL_DMAEx_List_Start(&dma_handle);
}

#endif  // KERNEL_MODE
