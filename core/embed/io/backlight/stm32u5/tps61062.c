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

#if 0
#pragma GCC optimize("O0")
#endif

#ifdef KERNEL_MODE

#include <sys/irq.h>
#include <sys/systick.h>
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/backlight.h>

#ifdef USE_DBG_CONSOLE
#include <sys/dbg_console.h>
#else
#define dbg_printf(...) ((void)0)
#endif

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

// TPS DAC steps (0-31) where 0 means ~15.6mV at Rs and 31 means ~500mV at
// Rs (1 steps ~15.6mV)
#define MAX_STEPS 31

// DAC value after reset
#define DEFAULT_STEP 16

// Approximated default level after reset
#define DEFAULT_LEVEL ((DEFAULT_STEP) * (BACKLIGHT_MAX_LEVEL) / (MAX_STEPS))

// API level range 0-255 is mapped to DAC steps 0-31
#define LEVEL_STEPS_RATIO 8
#define LEVEL_OFFSET 7

#define REG_LOOP_PERIOD_US 10000  // 10ms
#define DMA_BUF_LENGTH \
  (REG_LOOP_PERIOD_US / MAX_PULSE_WIDTH_US)  // number of samples per period

#define DMA_BUF_COUNT 2  // 2 buffers for double buffering

typedef enum { BACKLIGHT_OFF = 0, BACKLIGHT_ON = 1 } backlight_state_t;

// Backlight driver state
typedef struct {
  // Set if driver is initialized
  bool initialized;

  // Current state
  backlight_state_t state;

  // Requested values (via API)
  uint8_t requested_level;
  volatile uint8_t requested_level_limited;
  volatile uint8_t requested_step;
  volatile uint8_t requested_step_duty_cycle;

  // Latched values (currently being sent into TPS)
  volatile uint8_t latched_level[DMA_BUF_COUNT];
  volatile uint8_t latched_step[DMA_BUF_COUNT];
  volatile uint8_t latched_step_duty_cycle[DMA_BUF_COUNT];

  // Current values set (inside TPS)
  volatile uint8_t current_level;
  volatile uint8_t current_step;
  volatile uint8_t current_step_duty_cycle;

  // Max backlight level
  uint8_t max_level;

  TIM_HandleTypeDef tim;

  DMA_HandleTypeDef dma;

  DMA_NodeTypeDef dma_node[DMA_BUF_COUNT];
  DMA_QListTypeDef dma_queue;

  // Double buffer for DMA
  uint16_t pwm_data[DMA_BUF_COUNT][DMA_BUF_LENGTH];

  volatile uint8_t locked_buf_idx;
  volatile uint8_t prepare_buf_idx;

} backlight_driver_t;

static backlight_driver_t g_backlight_driver = {
    .initialized = false,
};

static void backlight_control_up(uint16_t *data, int steps);
static void backlight_control_down(uint16_t *data, int steps);
static void backlight_shutdown(void);

static void DMA_XferCpltCallback(DMA_HandleTypeDef *hdma);
#if 0
static void DMA_XferHalfCpltCallback(DMA_HandleTypeDef *hdma);
static void DMA_XferErrorCallback(DMA_HandleTypeDef *hdma);
static void DMA_XferAbortCallback(DMA_HandleTypeDef *hdma);
static void DMA_XferSuspendCallback(DMA_HandleTypeDef *hdma);
#endif

bool backlight_init(backlight_action_t action) {
  backlight_driver_t *drv = &g_backlight_driver;
  HAL_StatusTypeDef ret = HAL_OK;

  if (drv->initialized) {
    return true;
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
  ret |= HAL_TIM_PWM_Init(&drv->tim);

  TIM_OC_InitTypeDef TIM_OC_InitStructure = {0};
  // Make ILED to log 1 (by TIM.CCR1 value >= TIM.ARR) =>
  // when EN gets activated, TPS will be IDLE (we don't risk
  // it going into programming switched off state and
  // maximizing its output current)
  TIM_OC_InitStructure.Pulse = UINT16_MAX;
  TIM_OC_InitStructure.OCMode = TIM_OCMODE_PWM1;
  TIM_OC_InitStructure.OCPolarity = TIM_OCPOLARITY_HIGH;
  TIM_OC_InitStructure.OCFastMode = TIM_OCFAST_DISABLE;
  TIM_OC_InitStructure.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  TIM_OC_InitStructure.OCIdleState = TIM_OCIDLESTATE_RESET;
  TIM_OC_InitStructure.OCNIdleState = TIM_OCNIDLESTATE_RESET;
  ret |= HAL_TIM_PWM_ConfigChannel(&drv->tim, &TIM_OC_InitStructure,
                                   TIM_CHANNEL_1);

  // Initialize ILED GPIO
  GPIO_InitTypeDef GPIO_ILED_InitStructure = {0};
  GPIO_ILED_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_ILED_InitStructure.Pull = GPIO_NOPULL;
  GPIO_ILED_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_ILED_InitStructure.Pin = TPS61062_ILED_PIN;
  GPIO_ILED_InitStructure.Alternate = GPIO_AF2_TIM3;
  HAL_GPIO_Init(TPS61062_ILED_PORT, &GPIO_ILED_InitStructure);

  // GPDMA init (circular linked list mode with 2 nodes forming double buffer 1
  // one buffer is at a time, the 2nd is prepared at DMA.TC event which occurs
  // after buffers gets transferred)
  __HAL_RCC_GPDMA1_CLK_ENABLE();

  drv->dma.Instance = GPDMA1_Channel3;
  drv->dma.InitLinkedList.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  drv->dma.InitLinkedList.LinkStepMode = DMA_LSM_FULL_EXECUTION;
  drv->dma.InitLinkedList.LinkAllocatedPort = DMA_LINK_ALLOCATED_PORT1;
  drv->dma.InitLinkedList.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  drv->dma.InitLinkedList.LinkedListMode = DMA_LINKEDLIST_CIRCULAR;
  ret |= HAL_DMAEx_List_Init(&drv->dma);
#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
  ret |= HAL_DMA_ConfigChannelAttributes(
      &drv->dma, DMA_CHANNEL_PRIV | DMA_CHANNEL_SEC | DMA_CHANNEL_SRC_SEC |
                     DMA_CHANNEL_DEST_SEC);
#endif  // defined (__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)

  DMA_NodeConfTypeDef pNodeConfig;

  pNodeConfig.NodeType = DMA_GPDMA_LINEAR_NODE;
  pNodeConfig.Init.Request = GPDMA1_REQUEST_TIM3_UP;
  pNodeConfig.Init.BlkHWRequest = DMA_BREQ_SINGLE_BURST;
  pNodeConfig.Init.Direction = DMA_MEMORY_TO_PERIPH;
  pNodeConfig.Init.Priority = DMA_LOW_PRIORITY_HIGH_WEIGHT;
  pNodeConfig.Init.SrcInc = DMA_SINC_INCREMENTED;
  pNodeConfig.Init.DestInc = DMA_DINC_FIXED;
  pNodeConfig.Init.SrcDataWidth = DMA_SRC_DATAWIDTH_HALFWORD;
  pNodeConfig.Init.DestDataWidth = DMA_DEST_DATAWIDTH_WORD;
  pNodeConfig.Init.SrcBurstLength = 1;
  pNodeConfig.Init.DestBurstLength = 1;
  pNodeConfig.Init.TransferAllocatedPort =
      DMA_SRC_ALLOCATED_PORT1 | DMA_DEST_ALLOCATED_PORT0;
  pNodeConfig.Init.TransferEventMode = DMA_TCEM_BLOCK_TRANSFER;
  pNodeConfig.TriggerConfig.TriggerPolarity = DMA_TRIG_POLARITY_MASKED;
  pNodeConfig.DataHandlingConfig.DataExchange = DMA_EXCHANGE_NONE;
  pNodeConfig.DataHandlingConfig.DataAlignment = DMA_DATA_RIGHTALIGN_ZEROPADDED;
  pNodeConfig.SrcAddress = (uint32_t)drv->pwm_data[0];
  pNodeConfig.DstAddress = (uint32_t)&drv->tim.Instance->CCR1;
  pNodeConfig.DataSize = sizeof(drv->pwm_data[0]);
#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
  pNodeConfig.SrcSecure = DMA_CHANNEL_SRC_SEC;
  pNodeConfig.DestSecure = DMA_CHANNEL_DEST_SEC;
#endif  // defined (__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)

  // Build dma_node Node
  ret |= HAL_DMAEx_List_BuildNode(&pNodeConfig, &drv->dma_node[0]);
  memset(drv->pwm_data[0], UINT8_MAX, sizeof(drv->pwm_data[0]));

  // Insert dma_node to Queue
  ret |= HAL_DMAEx_List_InsertNode_Tail(&drv->dma_queue, &drv->dma_node[0]);

  // Prepare second node for regular operation
  pNodeConfig.SrcAddress = (uint32_t)drv->pwm_data[1];
  pNodeConfig.DataSize = sizeof(drv->pwm_data[1]);

  // Build dma_node Node
  ret |= HAL_DMAEx_List_BuildNode(&pNodeConfig, &drv->dma_node[1]);
  memset(drv->pwm_data[1], UINT8_MAX, sizeof(drv->pwm_data[1]));

  // Insert dma_node to Queue
  ret |= HAL_DMAEx_List_InsertNode_Tail(&drv->dma_queue, &drv->dma_node[1]);

  // Set circular mode
  ret |= HAL_DMAEx_List_SetCircularMode(&drv->dma_queue);

  // Link the Queue to the DMA channel
  ret |= HAL_DMAEx_List_LinkQ(&drv->dma, &drv->dma_queue);

  // Enable TIM DMA requests
  __HAL_TIM_ENABLE_DMA(&drv->tim, TIM_DMA_UPDATE);

  // Start TIM
  ret |= HAL_TIM_Base_Start(&drv->tim);
  ret |= HAL_TIM_PWM_Start(&drv->tim, TIM_CHANNEL_1);

  // Register DMA callbacks
  ret |= HAL_DMA_RegisterCallback(&drv->dma, HAL_DMA_XFER_CPLT_CB_ID,
                                  &DMA_XferCpltCallback);
#if 0
  ret |= HAL_DMA_RegisterCallback(&drv->dma, HAL_DMA_XFER_HALFCPLT_CB_ID,
  &DMA_XferHalfCpltCallback);
  ret |= HAL_DMA_RegisterCallback(&drv->dma, HAL_DMA_XFER_ERROR_CB_ID,
  &DMA_XferErrorCallback);
  ret |= HAL_DMA_RegisterCallback(&drv->dma, HAL_DMA_XFER_ABORT_CB_ID,
  &DMA_XferAbortCallback);
  ret |= HAL_DMA_RegisterCallback(&drv->dma, HAL_DMA_XFER_SUSPEND_CB_ID,
  &DMA_XferSuspendCallback);
#endif

  if (HAL_OK != ret) {
    // Failure
    // TODO: ++low level deinit function not requiring drv->initialized == true
    // as the backlight_deinit() function does.
    return false;
  }

  // Configure and enable DMA IRQ
  NVIC_SetPriority(GPDMA1_Channel3_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(GPDMA1_Channel3_IRQn);

  // Set active buffer to the first one
  drv->prepare_buf_idx = 0;
  drv->locked_buf_idx = 1;

  // Default no backlight max_level limit
  drv->max_level = BACKLIGHT_MAX_LEVEL;
  drv->requested_level = BACKLIGHT_MIN_LEVEL;

  drv->initialized = true;

  dbg_printf("%s:%d\n", __FILE_NAME__, __LINE__);
  dbg_printf("%s:%s(..) executed\n", __FILE_NAME__, __func__);

  return true;
}

void backlight_deinit(backlight_action_t action) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (!drv->initialized) {
    return;
  }

  if (action == BACKLIGHT_RESET) {
    HAL_StatusTypeDef ret = HAL_OK;

    irq_key_t key = irq_lock();

    // Abort the DMA. It's unclear what last data is transferred to TIM_CCR
    // register and in what state the respective GPIO pin will be left in. CCR
    // register is set to UINT16_MAX value inside "backlight_shutdown()"
    // function.
    if (drv->dma.State == HAL_DMA_STATE_BUSY) {
      ret |= HAL_DMA_Abort(
          &drv->dma);  // TODO: could be replaced with interrupt based variant
    }

    irq_unlock(key);

    backlight_shutdown();

    NVIC_DisableIRQ(GPDMA1_Channel3_IRQn);

    ret |= HAL_DMA_UnRegisterCallback(&drv->dma, HAL_DMA_XFER_CPLT_CB_ID);
#if 0
    ret |= HAL_DMA_UnRegisterCallback(&drv->dma, HAL_DMA_XFER_HALFCPLT_CB_ID);
    ret |= HAL_DMA_UnRegisterCallback(&drv->dma, HAL_DMA_XFER_ERROR_CB_ID);
    ret |= HAL_DMA_UnRegisterCallback(&drv->dma, HAL_DMA_XFER_ABORT_CB_ID);
    ret |= HAL_DMA_UnRegisterCallback(&drv->dma, HAL_DMA_XFER_SUSPEND_CB_ID);
#endif

    ret |= HAL_DMAEx_List_UnLinkQ(&drv->dma);
    ret |= HAL_DMAEx_List_DeInit(&drv->dma);

    if (HAL_OK != ret) {
      // Failure
      // TODO: should we react anyhow?
    }

    HAL_GPIO_DeInit(TPS61062_ILED_PORT, TPS61062_ILED_PIN);
    HAL_GPIO_DeInit(TPS61062_EN_PORT, TPS61062_EN_PIN);

    __HAL_RCC_TIM3_FORCE_RESET();
    __HAL_RCC_TIM3_RELEASE_RESET();
    __HAL_RCC_TIM3_CLK_DISABLE();

    // Move the state to OFF
    drv->state = BACKLIGHT_OFF;
  }

  drv->initialized = false;
}

bool backlight_set(uint8_t val) {
  backlight_driver_t *drv = &g_backlight_driver;
  HAL_StatusTypeDef ret = HAL_OK;

  if (!drv->initialized) {
    return false;
  }

  // Capture requested level.
  drv->requested_level = val;

  // Limit requested level by max_level
  uint8_t requested_level_limited = MIN(drv->requested_level, drv->max_level);

  // No action required
  if (requested_level_limited == drv->requested_level_limited) {
    return true;
  }

  dbg_printf("%s:%d:: val = %d, level, : %d\n", __FILE_NAME__, __LINE__, val,
             drv->requested_level);

  irq_key_t key = irq_lock();

  // Save the new value into the shared variable so that it can be used inside
  // DMA callback
  drv->requested_level_limited = requested_level_limited;

  // Calculate the mapping of requested level to steps (quotient)
  drv->requested_step =
      (MAX(drv->requested_level_limited, LEVEL_OFFSET) - LEVEL_OFFSET) /
      LEVEL_STEPS_RATIO;

  // Calculate the mapping of requested level to steps (remainder => duty cycle
  // of PWM regulation of the step)
  drv->requested_step_duty_cycle =
      (MAX(drv->requested_level_limited, LEVEL_OFFSET) - LEVEL_OFFSET) %
      LEVEL_STEPS_RATIO;
  drv->requested_step_duty_cycle =
      (drv->requested_step_duty_cycle * DMA_BUF_LENGTH) / LEVEL_STEPS_RATIO;

  // Requested level is below LEVEL_OFFSET => shutdown backlight
  if (drv->requested_level_limited < LEVEL_OFFSET) {
    if (drv->dma.State == HAL_DMA_STATE_BUSY) {
      ret |= HAL_DMA_Abort(
          &drv->dma);  // TODO: could be replaced with interrupt based variant

      if (HAL_OK != ret) {
        // Failure
        // TODO: should we react anyhow?
      }
    }

    irq_unlock(key);

    backlight_shutdown();

    // Clearing buffer, preparation for the next time
    memset(drv->pwm_data, UINT8_MAX, sizeof(drv->pwm_data));

    // Clear the control data
    for (int i = 0; i < DMA_BUF_COUNT; i++) {
      drv->latched_level[i] = 0;
      drv->latched_step[i] = 0;
      drv->latched_step_duty_cycle[i] = 0;
    }

    // Update values to reflect the backlight is off
    drv->current_level = 0;
    drv->current_step = 0;
    drv->current_step_duty_cycle = 0;

    // Set active buffer to the first one
    drv->prepare_buf_idx = 0;
    drv->locked_buf_idx = 1;

    // Move the state to OFF
    drv->state = BACKLIGHT_OFF;

    return true;
  }

  irq_unlock(key);

  // In case this functions is called first time after init or in case backlight
  // was switched off before, we need to prepare the buffers, DMA, etc. The DMA
  // is not running in this case, nor its interrupts => no need to disable them.
  if (drv->state == BACKLIGHT_OFF) {
    if (HAL_DMA_GetState(&drv->dma) == HAL_DMA_STATE_READY) {
      // Calculate the difference between the default state (the TPS EN pin
      // shall be activated at the end of this scope, the TPS sets itself to
      // default state = DEFAULT_STEP) and the wanted one
      if (drv->requested_step > DEFAULT_STEP) {
        // Start from index 1, index 0 is already set (with buffer clear to make
        // TIM not generate any pulse)
        backlight_control_up(&drv->pwm_data[drv->prepare_buf_idx][1],
                             drv->requested_step - DEFAULT_STEP);
      } else {
        // Start from index 1, index 0 is already set (with buffer clear to make
        // TIM not generate any pulse)
        backlight_control_down(&drv->pwm_data[drv->prepare_buf_idx][1],
                               DEFAULT_STEP - drv->requested_step);
      }

      // If the requested level can't exactly be mapped to steps, we need to
      // prepare the PWM regulation of the step. No need to clear the buffer,
      // it's already cleared (the backlight was switched off).
      if (drv->requested_step_duty_cycle > 0) {
        // First sample increases the steps by 1 (start of PWM period)
        drv->pwm_data[drv->locked_buf_idx][0] =
            TIM_PULSE(BACKLIGHT_CONTROL_T_UP_US);

        // "drv->requested_step_duty_cycle" sample returns to the original
        // steps' value (2nd half of PWM period)
        drv->pwm_data[drv->locked_buf_idx][drv->requested_step_duty_cycle] =
            TIM_PULSE(BACKLIGHT_CONTROL_T_DOWN_US);
      }

      // Set the current values to reflect the state after TPS EN gets activated
      drv->current_level = DEFAULT_LEVEL;
      drv->current_step = DEFAULT_STEP;
      drv->current_step_duty_cycle = 0;

      // Update the latched values to reflect what's about to happen when the
      // DMA is started
      drv->latched_level[drv->prepare_buf_idx] = drv->requested_level_limited;
      drv->latched_level[drv->locked_buf_idx] = drv->requested_level_limited;
      drv->latched_step[drv->prepare_buf_idx] = drv->requested_step;
      drv->latched_step[drv->locked_buf_idx] = drv->requested_step;
      drv->latched_step_duty_cycle[drv->prepare_buf_idx] =
          0;  // 0 - pulse set sequence ongoing
      drv->latched_step_duty_cycle[drv->locked_buf_idx] =
          drv->requested_step_duty_cycle;

      // Swap indices (the buffer prepared now will be locked next time, the
      // other one will be prepared next time)
      drv->locked_buf_idx = drv->prepare_buf_idx;
      drv->prepare_buf_idx = (drv->prepare_buf_idx + 1) % DMA_BUF_COUNT;

      // Enable TPS
      HAL_GPIO_WritePin(TPS61062_EN_PORT, TPS61062_EN_PIN, GPIO_PIN_SET);

      // Start the DMA
      ret |= HAL_DMAEx_List_Start_IT(&drv->dma);

      if (HAL_OK != ret) {
        // Failure
        // TODO: should we react anyhow?
      }

      // Move the state to ON
      drv->state = BACKLIGHT_ON;
    } else {
      // Some serious problem occured - DMA is not in READY state.
      // TODO: how to react?
    }
  }

  UNUSED(ret);

  return true;
}

uint8_t backlight_get(void) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (!drv->initialized) {
    return 0;
  }

  // Returning the limited requested value as the current value
  // is slightly delayed
  return drv->requested_level_limited;
}

// Set maximal backlight level
bool backlight_set_max_level(uint8_t max_level) {
  backlight_driver_t *drv = &g_backlight_driver;

  if (!drv->initialized) {
    return false;
  }

  drv->max_level = max_level;

  // The maximum value has been changed, so we need to reapply
  // the requested value
  return backlight_set(drv->requested_level);
}

static void backlight_control_up(uint16_t *data, int steps) {
  for (int i = 0; i < steps; i++) {
    data[i] = TIM_PULSE(BACKLIGHT_CONTROL_T_UP_US);
  }
}

static void backlight_control_down(uint16_t *data, int steps) {
  for (int i = 0; i < steps; i++) {
    data[i] = TIM_PULSE(BACKLIGHT_CONTROL_T_DOWN_US);
  }
}

static void backlight_shutdown(void) {
  backlight_driver_t *drv = &g_backlight_driver;

  drv->tim.Instance->CCR1 = UINT16_MAX;
  HAL_GPIO_WritePin(TPS61062_EN_PORT, TPS61062_EN_PIN, GPIO_PIN_RESET);
}

// Transfer complete callback
static void DMA_XferCpltCallback(DMA_HandleTypeDef *hdma) {
  backlight_driver_t *drv = &g_backlight_driver;
  uint32_t dma_CSAR_tmp, dma_BNDT_tmp;

  uint64_t tdiff;
  static uint64_t tmax = 0;

  tdiff = systick_us();

#if 0
  dbg_printf("%s:%d:: dma_CSAR_tmp = %08x", __FILE_NAME__, __LINE__, dma_CSAR_tmp);
  dbg_printf(", &pwm_data[drv->locked_buf_idx][0] = %08x", (uint32_t)&drv->pwm_data[drv->locked_buf_idx][0]);
  dbg_printf(", &pwm_data[drv->locked_buf_idx][49] = %08x\n", (uint32_t)&drv->pwm_data[drv->locked_buf_idx][DMA_BUF_COUNT - 1]);
#endif

  // There is a possibility of entering the ISR late e.g. just before
  // DMA finishes another transfer. Such case needs to be handled properly.
  dma_BNDT_tmp = __HAL_DMA_GET_COUNTER(&drv->dma);

  if (dma_BNDT_tmp < sizeof(drv->pwm_data[0]) / 5) {
    // The DMA is about to finish another transfer => skip this interrupt
    // "sizeof(drv->pwm_data[0]) / 5" means 20% of the buffer left => 2ms
    return;
  }

  // Back up the CSAR register so that it doesn't have to be accessed again
  dma_CSAR_tmp = drv->dma.Instance->CSAR;

  // Compare whether the CSAR points to the right buffer (in case the interrupts
  // have been switched off for too long and the DMA buffers' track has been
  // lost)
  if ((uint32_t)&drv->pwm_data[drv->locked_buf_idx][0] <= dma_CSAR_tmp &&
      (uint32_t)&drv->pwm_data[drv->locked_buf_idx][DMA_BUF_COUNT - 1] >=
          dma_CSAR_tmp) {
    // The CSAR points to the wrong buffer => we need to switch the buffers
    // Locked buffer is the one which has just been transferred
    drv->locked_buf_idx = drv->prepare_buf_idx;
    drv->prepare_buf_idx = (drv->prepare_buf_idx + 1) % DMA_BUF_COUNT;
  }

  // Update the current values with the latched ones as the data transfer
  // has finished.
  drv->current_level = drv->latched_level[drv->locked_buf_idx];
  drv->current_step = drv->latched_step[drv->locked_buf_idx];
  // The current duty cycle equals to the one which is currently being used.
  drv->current_step_duty_cycle =
      drv->latched_step_duty_cycle[drv->prepare_buf_idx];

  // Switch active buffer
  drv->locked_buf_idx = drv->prepare_buf_idx;
  drv->prepare_buf_idx = (drv->prepare_buf_idx + 1) % DMA_BUF_COUNT;

  // Check if we need to change the step value
  if (drv->requested_step != drv->latched_step[drv->locked_buf_idx]) {
    // Clear the buffer
    memset(drv->pwm_data[drv->prepare_buf_idx], UINT8_MAX,
           sizeof(drv->pwm_data[drv->prepare_buf_idx]));

    // Calculate the difference between the latched state and the requested one
    if (drv->requested_step > drv->latched_step[drv->locked_buf_idx]) {
      backlight_control_up(
          &drv->pwm_data[drv->prepare_buf_idx][0],
          drv->requested_step - drv->latched_step[drv->locked_buf_idx]);
    } else {
      backlight_control_down(
          &drv->pwm_data[drv->prepare_buf_idx][0],
          drv->latched_step[drv->locked_buf_idx] - drv->requested_step);
    }

    // The buffer has been precalculated to reach the drv->requested_step value
    // => update the latched values
    drv->latched_level[drv->prepare_buf_idx] = drv->requested_level_limited;
    drv->latched_step[drv->prepare_buf_idx] = drv->requested_step;
    // Set the latched duty cycle to 0 - steps' set sequence ongoing, no
    // regulation.
    drv->latched_step_duty_cycle[drv->prepare_buf_idx] = 0;
  } else {
    // Check if the duty cycle needs to be changed for the prepare buffer OR
    // if the buffer content is not initialized (not cleared) e.g. from previous
    // transfer
    if (drv->requested_step_duty_cycle !=
            drv->latched_step_duty_cycle[drv->prepare_buf_idx] ||
        drv->pwm_data[drv->prepare_buf_idx][0] != UINT16_MAX) {
      // Clear the buffer
      memset(drv->pwm_data[drv->prepare_buf_idx], UINT8_MAX,
             sizeof(drv->pwm_data[drv->prepare_buf_idx]));

      // If the requested level can't exactly be mapped to steps, we need to
      // prepare the PWM regulation of the step.
      if (drv->requested_step_duty_cycle > 0) {
        // First sample increases the steps by 1 (start of PWM period)
        drv->pwm_data[drv->prepare_buf_idx][0] =
            TIM_PULSE(BACKLIGHT_CONTROL_T_UP_US);

        // "drv->requested_step_duty_cycle" sample returns to the original
        // steps' value (2nd half of PWM period)
        drv->pwm_data[drv->prepare_buf_idx][drv->requested_step_duty_cycle] =
            TIM_PULSE(BACKLIGHT_CONTROL_T_DOWN_US);
      }
    }

    // The buffer has been precalculated with the respective PWM duty cycle data
    // => update the latched values
    drv->latched_level[drv->prepare_buf_idx] = drv->requested_level_limited;
    drv->latched_step[drv->prepare_buf_idx] = drv->requested_step;
    // The to be used duty cycle is set to the requested one.
    drv->latched_step_duty_cycle[drv->prepare_buf_idx] =
        drv->requested_step_duty_cycle;
  }

  tdiff = systick_us() - tdiff;
  tmax = MAX(tmax, tdiff);
  dbg_printf("execution time = %d us, max execution time = %d us\n",
             (uint32_t)tdiff, (uint32_t)tmax);

  UNUSED(hdma);
}

#if 0
// Half transfer complete callback
static void DMA_XferHalfCpltCallback(DMA_HandleTypeDef *hdma)
{
  UNUSED(hdma);
}

// Error callback
static void DMA_XferErrorCallback(DMA_HandleTypeDef *hdma)
{
  UNUSED(hdma);
}

// Abort callback
static void DMA_XferAbortCallback(DMA_HandleTypeDef *hdma)
{
  UNUSED(hdma);
}

// Suspend callback
static void DMA_XferSuspendCallback(DMA_HandleTypeDef *hdma)
{
  UNUSED(hdma);
}
#endif

void GPDMA1_Channel3_IRQHandler(void) {
  IRQ_LOG_ENTER();

  backlight_driver_t *drv = &g_backlight_driver;

  HAL_DMA_IRQHandler(&drv->dma);

  IRQ_LOG_EXIT();
}

#endif
