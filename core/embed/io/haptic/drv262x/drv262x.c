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

#include <math.h>
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/haptic.h>
#include <io/i2c_bus.h>
#include <rtl/logging.h>
#include <sys/systick.h>

#include "drv262x.h"

// Actuator configuration
#include DRV262X_ACTUATOR

LOG_DECLARE(haptic_driver);

#ifdef KERNEL_MODE

// Maximum amplitude of the vibration effect
// (DRV2625 supports 7-bit amplitude)
#define MAX_AMPLITUDE 127
// Amplitude of the button press effect
#define PRESS_EFFECT_AMPLITUDE 25
// Duration of the button press effect
#define PRESS_EFFECT_DURATION 10
// Amplitude of the bootloader entry effect
#define BOOTLOADER_ENTRY_EFFECT_AMPLITUDE 100
// Duration of the bootloader entry effect
#define BOOTLOADER_ENTRY_EFFECT_DURATION 300
// Amplitude of the power on effect
#define POWER_ON_EFFECT_AMPLITUDE 50
// Duration of the power on effect
#define POWER_ON_EFFECT_DURATION 50

#if !defined(ACTUATOR_LRA) && !defined(ACTUATOR_ERM)
#error "Actuator type (ACTUATOR_LRA or ACTUATOR_ERM) not defined"
#endif

#if defined(ACTUATOR_LRA) && defined(ACTUATOR_ERM)
#error "Both ACTUATOR_LRA and ACTUATOR_ERM defined, only one must be defined"
#endif

#if !defined(ACTUATOR_CLOSED_LOOP) && !defined(ACTUATOR_OPEN_LOOP)
#error \
    "Actuator control mode (ACTUATOR_CLOSED_LOOP or ACTUATOR_OPEN_LOOP) not defined"
#endif

#if !defined(ACTUATOR_RATED_VOLTAGE) || ACTUATOR_RATED_VOLTAGE > 255
#error "ACTUATOR_RATED_VOLTAGE must be defined and <= 255"
#endif

#if !defined(ACTUATOR_OD_CLAMP) || ACTUATOR_OD_CLAMP > 255
#error "ACTUATOR_OD_CLAMP must be defined and <= 255"
#endif

#if !defined(HAPTIC_CHIP_DRV2624) && !defined(HAPTIC_CHIP_DRV2625)
#error "HAPTIC_CHIP_DRV2624 or HAPTIC_CHIP_DRV2625 must be defined"
#endif

// Driver state
typedef struct {
  // Set if driver is initialized
  bool initialized;

  // I2c bus where the touch controller is connected
  i2c_bus_t *i2c_bus;

  // Set if driver is enabled
  bool enabled;

  // Set to if real-time playing is activated.
  // This prevents the repeated set of `DRV2625_REG_MODE` register
  // which would otherwise stop all playback.
  bool rtp_mode;
} drv262x_driver_t;

// Haptic driver instance
static drv262x_driver_t g_drv262x_driver = {
    .initialized = false,
};

static ts_t drv262x_read_reg(i2c_bus_t *bus, uint8_t addr, uint8_t *value) {
  TSH_DECLARE;

  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 1,
          .data = {addr},
      },
      {
          .flags = I2C_FLAG_RX,
          .size = sizeof(*value),
          .ptr = value,
      },
  };

  i2c_packet_t pkt = {
      .address = DRV262X_I2C_ADDRESS,
      .op_count = ARRAY_LENGTH(ops),
      .ops = ops,
  };

  TSH_CHECK(i2c_bus_submit_and_wait(bus, &pkt) == I2C_STATUS_OK, TS_EIO);

cleanup:
  TSH_RETURN;
}

static ts_t drv262x_set_reg(i2c_bus_t *bus, uint8_t addr, uint8_t value) {
  TSH_DECLARE;

  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 2,
          .data = {addr, value},
      },
  };

  i2c_packet_t pkt = {
      .address = DRV262X_I2C_ADDRESS,
      .op_count = ARRAY_LENGTH(ops),
      .ops = ops,
  };

  TSH_CHECK(i2c_bus_submit_and_wait(bus, &pkt) == I2C_STATUS_OK, TS_EIO);

cleanup:
  TSH_RETURN;
}

static ts_t drv262x_reg_mask_modify(i2c_bus_t *bus, uint8_t addr,
                                    uint8_t clear_mask, uint8_t set_mask) {
  TSH_DECLARE;
  ts_t status;

  uint8_t reg;
  status = drv262x_read_reg(bus, addr, &reg);
  TSH_CHECK_OK(status);

  reg &= ~clear_mask;
  reg |= set_mask;

  status = drv262x_set_reg(bus, addr, reg);
  TSH_CHECK_OK(status);

cleanup:
  TSH_RETURN;
}

#ifdef HAPTIC_CHIP_DRV2624

#define DRV2624_LIB_MAX_SEQ_LEN 15
#define DRV2624_LIB_MAX_WAVEFORMS 20
#define DRV2624_RAM_SIZE 1024

// DRV2624 custom waveform definition
typedef struct {
  uint8_t sequence[DRV2624_LIB_MAX_SEQ_LEN];
  uint8_t time[DRV2624_LIB_MAX_SEQ_LEN];
  uint8_t length;
  uint8_t repeat;  // 0-single run, 2-three runs, 7(max)-infinite runs.
  bool linear_ramp;
  bool short_timing;  // true = 1ms units, false = 5ms units
} drv2624_waveform_t;

// List of DRV2624 registered custom waveforms
typedef struct {
  drv2624_waveform_t *waveforms[DRV2624_LIB_MAX_WAVEFORMS];
  uint8_t registered_waveforms;
} drv2624_waveform_list_t;

// Sharp btn click effect waveform
drv2624_waveform_t sharp_btn_click_effect = {
    .sequence = {45, 63, 55, 120, 15, 100, 8, 90, 3, 0, 0, 0, 0, 0, 0},
    .time = {3, 2, 3, 1, 4, 2, 5, 3, 8, 0, 0, 0, 0, 0, 0},
    .length = 9,
    .repeat = 0,
    .linear_ramp = false,
    .short_timing = true,
};

static drv2624_waveform_list_t g_waveform_list = {.registered_waveforms = 0};

static ts_t drv2624_register_waveform(drv2624_waveform_list_t *list,
                                      drv2624_waveform_t *waveform) {
  TSH_DECLARE;

  TSH_CHECK_ARG(waveform->length != 0 &&
                waveform->length <= DRV2624_LIB_MAX_SEQ_LEN);

  TSH_CHECK_ARG(waveform->repeat <= 7);

  list->waveforms[list->registered_waveforms] = waveform;
  list->registered_waveforms++;

cleanup:
  TSH_RETURN;
}

static ts_t drv2624_load_ram(drv2624_waveform_list_t *wave_list) {
  drv262x_driver_t *drv = &g_drv262x_driver;

  TSH_DECLARE;
  ts_t status;

  status = drv262x_set_reg(drv->i2c_bus, 0xFD, 0x00);
  TSH_CHECK_OK(status);
  status = drv262x_set_reg(drv->i2c_bus, 0xFE, 0x00);
  TSH_CHECK_OK(status);
  status = drv262x_set_reg(drv->i2c_bus, 0xFF, 0x00);  // RAM revision byte 0x00
  TSH_CHECK_OK(status);

  uint16_t waveform_data_start_address =
      0x0001 + wave_list->registered_waveforms * 3;

  uint16_t addr_pointer = waveform_data_start_address;
  TSH_CHECK(waveform_data_start_address + 2 * DRV2624_LIB_MAX_SEQ_LEN <
                DRV2624_RAM_SIZE,
            TS_ENOMEM);

  // RAM Header
  for (int i = 0; i < wave_list->registered_waveforms; i++) {
    drv2624_waveform_t *wav = wave_list->waveforms[i];

    status = drv262x_set_reg(
        drv->i2c_bus, 0xFF,
        (addr_pointer >> 8) & 0xFF);  // Start address upper byte
    TSH_CHECK_OK(status);

    status =
        drv262x_set_reg(drv->i2c_bus, 0xFF,
                        (addr_pointer) & 0xFF);  // Start address lower byte
    TSH_CHECK_OK(status);
    status = drv262x_set_reg(drv->i2c_bus, 0xFF,
                             ((wav->length * 2) & 0x3F) | (wav->repeat << 6));
    TSH_CHECK_OK(status);

    addr_pointer += wav->length * 2;
    TSH_CHECK(addr_pointer + DRV2624_LIB_MAX_SEQ_LEN <= DRV2624_RAM_SIZE,
              TS_ENOMEM);
  }

  // Copy waveform data
  addr_pointer = waveform_data_start_address;
  for (int i = 0; i < wave_list->registered_waveforms; i++) {
    drv2624_waveform_t *wav = wave_list->waveforms[i];

    for (int j = 0; j < wav->length; j++) {
      if (wav->linear_ramp) {
        status = drv262x_set_reg(drv->i2c_bus, 0xFF,
                                 (wav->sequence[j] & 0x7F) | (1 << 7));
      } else {
        status = drv262x_set_reg(drv->i2c_bus, 0xFF, (wav->sequence[j] & 0x7F));
      }
      TSH_CHECK_OK(status);

      status = drv262x_set_reg(drv->i2c_bus, 0xFF, wav->time[j]);
      TSH_CHECK_OK(status);
    }

    addr_pointer += wav->length * 2;
    TSH_CHECK(addr_pointer <= DRV2624_RAM_SIZE, TS_ENOMEM);
  }

cleanup:
  TSH_RETURN;
}

static ts_t drv2624_waveform_configuration(void) {
  TSH_DECLARE;
  ts_t status;

  drv2624_waveform_list_t *wave_list = &g_waveform_list;

  // Clear waveform list
  memset(wave_list, 0, sizeof(drv2624_waveform_list_t));

  // Register haptic waveforms, waveforms are assigned IDs based on the order
  // of registration starting from 1.

  TSH_CHECK_OK(
      drv2624_register_waveform(wave_list, &sharp_btn_click_effect));  // ID:1

  /** Add more waveforms here ..  */
  // TSH_CHECK_OK(drv2624_register_waveform(wave_list, &waveform2));

  status = drv2624_load_ram(wave_list);
  TSH_CHECK_OK(status);

cleanup:
  TSH_RETURN;
}

static ts_t drv2624_play_waveform(uint8_t waveform_id) {
  drv262x_driver_t *drv = &g_drv262x_driver;

  TSH_DECLARE;
  ts_t status;

  TSH_CHECK_ARG(waveform_id > 0 &&
                waveform_id <= g_waveform_list.registered_waveforms);

  drv->rtp_mode = false;

  // Set driver to waveform mode
  status = drv262x_reg_mask_modify(
      drv->i2c_bus, DRV262X_R7, DRV262X_R7_MODE_MASK,
      (DRV262X_R7_MODE_WAVEFORM << DRV262X_R7_MODE_POS) & DRV262X_R7_MODE_MASK);
  TSH_CHECK_OK(status);

  status = drv262x_reg_mask_modify(
      drv->i2c_bus, DRV262X_R7, DRV262X_R7_TRIG_PIN_FUNC_MASK,
      (DRV262X_R7_TRIG_PIN_FUNC_INT << DRV262X_R7_TRIG_PIN_FUNC_POS) &
          DRV262X_R7_TRIG_PIN_FUNC_MASK);
  TSH_CHECK_OK(status);

  // DRV2424 could play waveforms from RAM with different timing resolution
  // set the timing according to waveform settings.
  if (g_waveform_list.waveforms[waveform_id - 1]->short_timing) {
    status = drv262x_reg_mask_modify(drv->i2c_bus, DRV262X_RD,
                                     DRV262X_RD_PLAYBACK_INTERVAL_MASK,
                                     0x1 << DRV262X_RD_PLAYBACK_INTERVAL_POS);
    TSH_CHECK_OK(status);

  } else {
    status = drv262x_reg_mask_modify(drv->i2c_bus, DRV262X_RD,
                                     DRV262X_RD_PLAYBACK_INTERVAL_MASK,
                                     0x0 << DRV262X_RD_PLAYBACK_INTERVAL_POS);
    TSH_CHECK_OK(status);
  }

  // Set first waveform slot
  status = drv262x_set_reg(drv->i2c_bus, DRV262X_RF, waveform_id);
  TSH_CHECK_OK(status);

  // Make sure that the second slot is empty (end of sequence)
  status = drv262x_set_reg(drv->i2c_bus, DRV262X_R10, 0);
  TSH_CHECK_OK(status);

  // Start playback with GO bit
  status = drv262x_set_reg(drv->i2c_bus, DRV262X_RC, DRV262X_RC_GO_MASK);
  TSH_CHECK_OK(status);

cleanup:
  TSH_RETURN;
}

#endif  // HAPTIC_CHIP_DRV2624

static ts_t drv262x_actuator_configuration() {
  drv262x_driver_t *drv = &g_drv262x_driver;

  TSH_DECLARE;
  ts_t status;

  uint8_t reg_mask = DRV262X_R8_AUTO_BRK_INT_O_STBY_MASK;

#ifdef ACTUATOR_LRA
  reg_mask |= DRV262X_R8_LRA_ERM_MASK;  // Set LRA acuator
#endif

#ifdef ACTUATOR_OPEN_LOOP
  reg_mask |= DRV262X_R8_CONTROL_LOOP_MASK;  // Open loop control
#endif

  status = drv262x_set_reg(drv->i2c_bus, DRV262X_R8, reg_mask);
  TSH_CHECK_OK(status);

  // Set RATED_VOLTAGE
  status = drv262x_set_reg(drv->i2c_bus, DRV262X_R1F, ACTUATOR_RATED_VOLTAGE);
  TSH_CHECK_OK(status);

  // SET OD_CLAMP
  status = drv262x_set_reg(drv->i2c_bus, DRV262X_R20, ACTUATOR_OD_CLAMP);
  TSH_CHECK_OK(status);

#ifdef ACTUATOR_OPEN_LOOP

  status =
      drv262x_set_reg(drv->i2c_bus, DRV262X_R2F, ACTUATOR_LRA_PERIOD & 0xFF);
  TSH_CHECK_OK(status);
  status = drv262x_set_reg(drv->i2c_bus, DRV262X_R2E, ACTUATOR_LRA_PERIOD >> 8);
  TSH_CHECK_OK(status);

  // Set sin-wave driving shape
  status = drv262x_reg_mask_modify(drv->i2c_bus, DRV262X_R2C,
                                   DRV262X_R2C_LRA_WAVE_SHAPE_MASK,
                                   DRV262X_R2C_LRA_WAVE_SHAPE_MASK);
  TSH_CHECK_OK(status);

#endif

  // Set FB_BREAK_FACTOR, LOOP_GAIN, BEMF_GAIN
  status = drv262x_set_reg(
      drv->i2c_bus, DRV262X_R23,
      ((ACTUATOR_FB_BRK_FACTOR << DRV262X_R23_FB_BREAK_FACTOR_POS) &
       DRV262X_R23_FB_BREAK_FACTOR_MASK) |
          ((ACTUATOR_LOOP_GAIN << DRV262X_R23_LOOP_GAIN_POS) &
           DRV262X_R23_LOOP_GAIN_MASK) |
          ((ACTUATOR_BEMF_GAIN << DRV262X_R23_BEMF_GAIN_POS) &
           DRV262X_R23_BEMF_GAIN_MASK));
  TSH_CHECK_OK(status);

  // Set DRIVE_TIME
  status = drv262x_reg_mask_modify(
      drv->i2c_bus, DRV262X_R27, DRV262X_R27_DRIVE_TIME_MASK,
      (ACTUATOR_DRIVE_TIME << DRV262X_R27_DRIVE_TIME_POS) &
          DRV262X_R27_DRIVE_TIME_MASK);
  TSH_CHECK_OK(status);

  // Set BLANKING_TIME, IDISS_TIME
  status =
      drv262x_set_reg(drv->i2c_bus, DRV262X_R28,
                      ((ACTUATOR_IDISS_TIME << DRV262X_R28_IDISS_TIME_POS) &
                       DRV262X_R28_IDISS_TIME_MASK) |
                          ((ACTUATOR_BLANK_TIME << DRV262X_R28_BLANK_TIME_POS) &
                           DRV262X_R28_BLANK_TIME_MASK));
  TSH_CHECK_OK(status);

  // Set ZC_DET_TIME, SAMPLE_TIME
  status = drv262x_reg_mask_modify(
      drv->i2c_bus, DRV262X_R29,
      DRV262X_R29_ZC_DET_TIME_MASK | DRV262X_R29_SAMPLE_TIME_MASK,
      ((ACTUATOR_ZC_DET_TIME << DRV262X_R29_ZC_DET_TIME_POS) &
       DRV262X_R29_ZC_DET_TIME_MASK) |
          ((ACTUATOR_SAMPLE_TIME << DRV262X_R29_SAMPLE_TIME_POS) &
           DRV262X_R29_SAMPLE_TIME_MASK));
  TSH_CHECK_OK(status);

#ifdef HAPTIC_CHIP_DRV2624
  // DRV2624 do not have a predefined waveform library, but instead it has a
  // dedicated 1KB RAM which could be filled with custom waveforms data.
  status = drv2624_waveform_configuration();
  TSH_CHECK_OK(status);
#endif

cleanup:
  TSH_RETURN;
}

static ts_t drv262x_play_rtp(int8_t amplitude, uint16_t duration_ms) {
  drv262x_driver_t *drv = &g_drv262x_driver;

  TSH_DECLARE;
  ts_t status;

  if (!drv->rtp_mode) {
    // Switch to RTP mode
    status = drv262x_reg_mask_modify(
        drv->i2c_bus, DRV262X_R7, DRV262X_R7_MODE_MASK,
        (DRV262X_R7_MODE_RTP << DRV262X_R7_MODE_POS) & DRV262X_R7_MODE_MASK);
    TSH_CHECK_OK(status);

    status = drv262x_reg_mask_modify(
        drv->i2c_bus, DRV262X_R7, DRV262X_R7_TRIG_PIN_FUNC_MASK,
        (DRV262X_R7_TRIG_PIN_FUNC_EXT_TRIG << DRV262X_R7_TRIG_PIN_FUNC_POS) &
            DRV262X_R7_TRIG_PIN_FUNC_MASK);
    TSH_CHECK_OK(status);

    drv->rtp_mode = true;
  }

  // Set RTP amplitude
  status = drv262x_set_reg(drv->i2c_bus, DRV262X_RE, (uint8_t)amplitude);
  TSH_CHECK_OK(status);

  duration_ms = MIN(duration_ms, 6500);

  if (duration_ms > 0) {
    DRV262X_TRIG_TIM->CNT = 1;
    DRV262X_TRIG_TIM->CCR1 = 1;
    DRV262X_TRIG_TIM->ARR = duration_ms * 10;
    DRV262X_TRIG_TIM->CR1 |= TIM_CR1_CEN;
  }

cleanup:
  TSH_RETURN;
}

ts_t haptic_init(void) {
  drv262x_driver_t *drv = &g_drv262x_driver;

  if (drv->initialized) {
    return TS_OK;
  }

  TSH_DECLARE;
  ts_t status;

  memset(drv, 0, sizeof(drv262x_driver_t));

  GPIO_InitTypeDef GPIO_InitStructure = {0};

#ifdef DRV262X_RESET_PIN
  DRV262X_RESET_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = DRV262X_RESET_PIN;
  HAL_GPIO_WritePin(DRV262X_RESET_PORT, DRV262X_RESET_PIN, GPIO_PIN_RESET);
  HAL_GPIO_Init(DRV262X_RESET_PORT, &GPIO_InitStructure);
  systick_delay_ms(1);
  HAL_GPIO_WritePin(DRV262X_RESET_PORT, DRV262X_RESET_PIN, GPIO_PIN_SET);
  systick_delay_ms(1);
#endif

  DRV262X_TRIG_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = DRV262X_TRIG_PIN;
  GPIO_InitStructure.Alternate = DRV262X_TRIG_AF;
  HAL_GPIO_Init(DRV262X_TRIG_PORT, &GPIO_InitStructure);

  drv->i2c_bus = i2c_bus_open(DRV262X_I2C_INSTANCE);
  TSH_CHECK(drv->i2c_bus != NULL, TS_EIO);

  // Read haptic driver model and revision
  uint8_t reg_value;
  status = drv262x_read_reg(drv->i2c_bus, DRV262X_R0, &reg_value);
  TSH_CHECK_OK(status);

#if defined(HAPTIC_CHIP_DRV2624)
  TSH_CHECK((reg_value >> 4) == 0x0, TS_EINVAL);
#elif defined(HAPTIC_CHIP_DRV2625)
  TSH_CHECK((reg_value >> 4) == 0x1, TS_EINVAL);
#endif

  status = drv262x_actuator_configuration();
  TSH_CHECK_OK(status);

  DRV262X_TRIG_TIM_FORCE_RESET();
  DRV262X_TRIG_TIM_RELEASE_RESET();
  DRV262X_TRIG_TIM_CLK_ENA();

  TIM_HandleTypeDef TIM_Handle = {0};
  TIM_Handle.State = HAL_TIM_STATE_RESET;
  TIM_Handle.Instance = DRV262X_TRIG_TIM;
  TIM_Handle.Init.Period = 0;
  TIM_Handle.Init.Prescaler = SystemCoreClock / 10000;
  TIM_Handle.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  TIM_Handle.Init.CounterMode = TIM_COUNTERMODE_UP;
  TIM_Handle.Init.RepetitionCounter = 0;
  status =
      hal_status_to_ts(HAL_TIM_OnePulse_Init(&TIM_Handle, TIM_OPMODE_SINGLE));
  TSH_CHECK_OK(status);

  TIM_OnePulse_InitTypeDef TIM_OP_InitStructure = {0};
  TIM_OP_InitStructure.OCMode = TIM_OCMODE_PWM2;
  TIM_OP_InitStructure.OCPolarity = TIM_OCPOLARITY_HIGH;
  TIM_OP_InitStructure.Pulse = 1;
  TIM_OP_InitStructure.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  status = hal_status_to_ts(HAL_TIM_OnePulse_ConfigChannel(
      &TIM_Handle, &TIM_OP_InitStructure, TIM_CHANNEL_1, TIM_CHANNEL_2));
  TSH_CHECK_OK(status);

  status = hal_status_to_ts(HAL_TIM_OC_Start(&TIM_Handle, TIM_CHANNEL_1));
  TSH_CHECK_OK(status);

  DRV262X_TRIG_TIM->BDTR |= TIM_BDTR_MOE;

  drv->initialized = true;
  drv->enabled = true;

  TSH_RETURN;

cleanup:
  LOG_INF("Haptic driver initialization failed, cleaning up");
  haptic_deinit();
  TSH_RETURN;
}

void haptic_deinit(void) {
  drv262x_driver_t *drv = &g_drv262x_driver;

  i2c_bus_close(drv->i2c_bus);

  GPIO_InitTypeDef GPIO_InitStructure = {0};

#ifdef DRV262X_RESET_PIN
  // External pull-down on NRST pin ensures that the DRV262X goes into
  // shutdown mode when the reset GPIO is deinitialized.
  GPIO_InitStructure.Mode = GPIO_MODE_ANALOG;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = DRV262X_RESET_PIN;
  HAL_GPIO_Init(DRV262X_RESET_PORT, &GPIO_InitStructure);
#endif

  GPIO_InitStructure.Mode = GPIO_MODE_ANALOG;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = DRV262X_TRIG_PIN;
  HAL_GPIO_Init(DRV262X_TRIG_PORT, &GPIO_InitStructure);

  DRV262X_TRIG_TIM_FORCE_RESET();
  DRV262X_TRIG_TIM_RELEASE_RESET();
  DRV262X_TRIG_TIM_CLK_DIS();

  memset(drv, 0, sizeof(drv262x_driver_t));
}

ts_t haptic_set_enabled(bool enabled) {
  drv262x_driver_t *drv = &g_drv262x_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  drv->enabled = enabled;

  return TS_OK;
}

bool haptic_get_enabled(void) {
  drv262x_driver_t *drv = &g_drv262x_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->enabled;
}

ts_t haptic_play(haptic_effect_t effect) {
  drv262x_driver_t *drv = &g_drv262x_driver;

  TSH_DECLARE;
  ts_t status;

  TSH_CHECK(drv->initialized, TS_ENOINIT);
  TSH_CHECK(drv->enabled, TS_ENOEN);

  switch (effect) {
    case HAPTIC_BUTTON_PRESS:

#if defined(HAPTIC_CHIP_DRV2624)
      status = drv2624_play_waveform(1);  // Sharp button click effect
      TSH_CHECK_OK(status);
#elif defined(HAPTIC_CHIP_DRV2625)
      status = drv262x_play_rtp(PRESS_EFFECT_AMPLITUDE, PRESS_EFFECT_DURATION);
      TSH_CHECK_OK(status);
#endif
      break;
    case HAPTIC_BOOTLOADER_ENTRY:
      status = drv262x_play_rtp(BOOTLOADER_ENTRY_EFFECT_AMPLITUDE,
                                BOOTLOADER_ENTRY_EFFECT_DURATION);
      TSH_CHECK_OK(status);
      break;
    case HAPTIC_POWER_ON:
      status =
          drv262x_play_rtp(POWER_ON_EFFECT_AMPLITUDE, POWER_ON_EFFECT_DURATION);
      TSH_CHECK_OK(status);
    default:
      break;
  }

cleanup:
  TSH_RETURN;
}

ts_t haptic_play_custom(int8_t amplitude_pct, uint16_t duration_ms) {
  drv262x_driver_t *drv = &g_drv262x_driver;

  TSH_DECLARE;
  ts_t status;

  TSH_CHECK(drv->initialized, TS_ENOINIT);
  TSH_CHECK(drv->enabled, TS_ENOEN);

  // Clamp amplitude percentage to 0-100%
  amplitude_pct = MIN(MAX(amplitude_pct, 0), 100);

  status = drv262x_play_rtp((int8_t)((amplitude_pct * MAX_AMPLITUDE) / 100),
                            duration_ms);
  TSH_CHECK_OK(status);

cleanup:
  TSH_RETURN;
}

#endif  // KERNEL_MODE
