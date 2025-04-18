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

#include <sys/irq.h>
#include <sys/systick.h>
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/backlight.h>

#define BACKLIGHT_CONTROL_T_UP_US 30     // may be in range 1-75
#define BACKLIGHT_CONTROL_T_DOWN_US 198  // may be in range 180-300

//  unused - for reference
// #define BACKLIGHT_CONTROL_T_START_US 110  // may be in range 100-150
// #define BACKLIGHT_CONTROL_T_D_US 2
// #define BACKLIGHT_CONTROL_T_OFF_US 550

#define TIMER_PERIOD 32000      // 5 kHz @ 160MHz
#define MAX_PULSE_WIDTH_US 200  // 5kHz

#define TIM_PULSE(width) \
  (TIMER_PERIOD - (width) * TIMER_PERIOD / MAX_PULSE_WIDTH_US)

#define MAX_STEPS 32
#define DEFAULT_STEP 16  // DAC value after reset

// Backlight driver state
typedef struct {
  // Set if driver is initialized
  bool initialized;

  // Level requested (0-255)
  int requested_level;
  int current_level;

  // Current step in range 0-32
  int current_step;

  // Max backlight level
  int max_level;

  DMA_HandleTypeDef dma;
  TIM_HandleTypeDef tim;

  uint32_t pwm_data[MAX_STEPS + 2];  // max steps + 2 for start and end

} backlight_driver_t;

static backlight_driver_t g_backlight_driver = {
    .initialized = false,
};

static void backlight_control_up(uint32_t *data, int steps);
static void backlight_control_down(uint32_t *data, int steps);
static void backlight_shutdown();

void backlight_init(backlight_action_t action) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(backlight_driver_t));

  TPS61062_ILED_CLK_ENA();
  TPS61062_EN_CLK_ENA();

  // action = BACKLIGHT_RESET.
  // action = BACKLIGHT_RETAIN is not implemented

  // Initialize EN GPIO
  GPIO_InitTypeDef GPIO_EN_InitStructure = {0};
  GPIO_EN_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_EN_InitStructure.Pull = GPIO_NOPULL;
  GPIO_EN_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_EN_InitStructure.Pin = TPS61062_EN_PIN;
  HAL_GPIO_Init(TPS61062_EN_PORT, &GPIO_EN_InitStructure);

  HAL_GPIO_WritePin(TPS61062_EN_PORT, TPS61062_EN_PIN, GPIO_PIN_RESET);

  __HAL_RCC_TIM3_CLK_ENABLE();
  __HAL_RCC_TIM3_FORCE_RESET();
  __HAL_RCC_TIM3_RELEASE_RESET();
  drv->tim.State = HAL_TIM_STATE_RESET;
  drv->tim.Instance = TIM3;
  drv->tim.Init.Period = TIMER_PERIOD;
  drv->tim.Init.Prescaler = 0;
  drv->tim.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  drv->tim.Init.CounterMode = TIM_COUNTERMODE_UP;
  drv->tim.Init.RepetitionCounter = 0;
  HAL_TIM_PWM_Init(&drv->tim);

  TIM_OC_InitTypeDef TIM_OC_InitStructure = {0};
  TIM_OC_InitStructure.Pulse = 0;
  TIM_OC_InitStructure.OCMode = TIM_OCMODE_PWM1;
  TIM_OC_InitStructure.OCPolarity = TIM_OCPOLARITY_HIGH;
  TIM_OC_InitStructure.OCFastMode = TIM_OCFAST_DISABLE;
  TIM_OC_InitStructure.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  TIM_OC_InitStructure.OCIdleState = TIM_OCIDLESTATE_RESET;
  TIM_OC_InitStructure.OCNIdleState = TIM_OCNIDLESTATE_RESET;
  HAL_TIM_PWM_ConfigChannel(&drv->tim, &TIM_OC_InitStructure, TIM_CHANNEL_1);

  // Initialize ILED GPIO
  GPIO_InitTypeDef GPIO_ILED_InitStructure = {0};
  GPIO_ILED_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_ILED_InitStructure.Pull = GPIO_NOPULL;
  GPIO_ILED_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_ILED_InitStructure.Pin = TPS61062_ILED_PIN;
  GPIO_ILED_InitStructure.Alternate = GPIO_AF2_TIM3;
  HAL_GPIO_Init(TPS61062_ILED_PORT, &GPIO_ILED_InitStructure);

  __HAL_RCC_GPDMA1_CLK_ENABLE();
  drv->dma.Instance = GPDMA1_Channel3;
  drv->dma.Init.Direction = DMA_MEMORY_TO_PERIPH;
  drv->dma.Init.Mode = DMA_NORMAL;
  drv->dma.Init.Request = GPDMA1_REQUEST_TIM3_UP;
  drv->dma.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  drv->dma.Init.SrcInc = DMA_SINC_INCREMENTED;
  drv->dma.Init.DestInc = DMA_DINC_FIXED;
  drv->dma.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_WORD;
  drv->dma.Init.DestDataWidth = DMA_DEST_DATAWIDTH_WORD;
  drv->dma.Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  drv->dma.Init.SrcBurstLength = 1;
  drv->dma.Init.DestBurstLength = 1;
  drv->dma.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  drv->dma.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;

  HAL_DMA_Init(&drv->dma);
  HAL_DMA_ConfigChannelAttributes(
      &drv->dma, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC | DMA_CHANNEL_SRC_SEC |
                     DMA_CHANNEL_DEST_SEC);

  __HAL_TIM_ENABLE_DMA(&drv->tim, TIM_DMA_UPDATE);

  HAL_TIM_Base_Start(&drv->tim);
  HAL_TIM_PWM_Start(&drv->tim, TIM_CHANNEL_1);

  // Default no backlight max_level limit
  drv->max_level = BACKLIGHT_MAX_LEVEL;
  drv->requested_level = BACKLIGHT_MIN_LEVEL;

  drv->initialized = true;
}

void backlight_deinit(backlight_action_t action) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (!drv->initialized) {
    return;
  }

  if (HAL_DMA_GetState(&drv->dma) == HAL_DMA_STATE_BUSY) {
    while (HAL_DMA_PollForTransfer(&drv->dma, HAL_DMA_FULL_TRANSFER,
                                   HAL_MAX_DELAY) != HAL_OK) {
    }
  }

  if (action == BACKLIGHT_RESET) {
    backlight_shutdown();
    HAL_GPIO_DeInit(TPS61062_ILED_PORT, TPS61062_ILED_PIN);
    HAL_GPIO_DeInit(TPS61062_EN_PORT, TPS61062_EN_PIN);

    __HAL_RCC_TIM3_FORCE_RESET();
    __HAL_RCC_TIM3_RELEASE_RESET();
    __HAL_RCC_TIM3_CLK_DISABLE();
  }

  drv->initialized = false;
}

int backlight_set(int val) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (!drv->initialized) {
    return 0;
  }

  // Requested level out of range
  if (val < BACKLIGHT_MIN_LEVEL || val > BACKLIGHT_MAX_LEVEL) {
    return drv->current_level;
  }

  // Capture requested level.
  drv->requested_level = val;

  int requested_level_limited = drv->requested_level;
  if (drv->requested_level > drv->max_level) {
    requested_level_limited = drv->max_level;
  }

  // No action required
  if (requested_level_limited == drv->current_level) {
    return drv->current_level;
  }

  // New backlight level
  drv->current_level = requested_level_limited;

  int set_step = MAX_STEPS * drv->current_level / BACKLIGHT_MAX_LEVEL;

  if (set_step == 0) {
    backlight_shutdown();
    drv->current_step = 0;
    return drv->current_level;
  }

  if (HAL_DMA_GetState(&drv->dma) == HAL_DMA_STATE_BUSY) {
    while (HAL_DMA_PollForTransfer(&drv->dma, HAL_DMA_FULL_TRANSFER,
                                   HAL_MAX_DELAY) != HAL_OK) {
    }
  }

  int pwm_data_idx = 0;
  memset(drv->pwm_data, 0, sizeof(drv->pwm_data));

  if (drv->current_step == 0) {
    HAL_GPIO_WritePin(TPS61062_EN_PORT, TPS61062_EN_PIN, GPIO_PIN_SET);
    // if brightness control is shutdown, start with initial pulse
    drv->pwm_data[0] = TIMER_PERIOD;
    pwm_data_idx++;
    drv->current_step = DEFAULT_STEP;
  }

  if (set_step > drv->current_step) {
    int steps = set_step - drv->current_step;
    backlight_control_up(&drv->pwm_data[pwm_data_idx], steps);
    pwm_data_idx += steps;

  } else if (set_step < drv->current_step) {
    int steps = drv->current_step - set_step;
    backlight_control_down(&drv->pwm_data[pwm_data_idx], steps);
    pwm_data_idx += steps;
  }

  drv->pwm_data[pwm_data_idx] = TIMER_PERIOD;

  HAL_DMA_Start(&drv->dma, (uint32_t)drv->pwm_data,
                (uint32_t)&drv->tim.Instance->CCR1,
                (pwm_data_idx + 1) * sizeof(uint32_t));

  drv->current_step = set_step;

  return drv->current_level;
}

int backlight_get(void) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->current_level;
}

// Set maximal backlight level
int backlight_set_max_level(int max_level) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (!drv->initialized) {
    return 0;
  }

  if (max_level < BACKLIGHT_MIN_LEVEL) {
    max_level = BACKLIGHT_MIN_LEVEL;
  }

  if (max_level > BACKLIGHT_MAX_LEVEL) {
    max_level = BACKLIGHT_MAX_LEVEL;
  }

  drv->max_level = max_level;
  backlight_set(drv->requested_level);

  return drv->current_level;
}

static void backlight_control_up(uint32_t *data, int steps) {
  for (int i = 0; i < steps; i++) {
    data[i] = TIM_PULSE(BACKLIGHT_CONTROL_T_UP_US);
  }
}

static void backlight_control_down(uint32_t *data, int steps) {
  for (int i = 0; i < steps; i++) {
    data[i] = TIM_PULSE(BACKLIGHT_CONTROL_T_DOWN_US);
  }
}

static void backlight_shutdown() {
  HAL_GPIO_WritePin(TPS61062_EN_PORT, TPS61062_EN_PIN, GPIO_PIN_RESET);
}

#endif
