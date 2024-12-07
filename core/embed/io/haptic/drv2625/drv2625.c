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

#include <io/haptic.h>
#include <io/i2c_bus.h>
#include <sys/systick.h>

#include "drv2625.h"

#ifdef KERNEL_MODE

// Maximum amplitude of the vibration effect
// (DRV2625 supports 7-bit amplitude)
#define MAX_AMPLITUDE 127
// Amplitude of the vibration effect used for production test
#define PRODTEST_EFFECT_AMPLITUDE 127
// Amplitude of the button press effect
#define PRESS_EFFECT_AMPLITUDE 25
// Duration of the button press effect
#define PRESS_EFFECT_DURATION 10

// Actuator configuration
#include HAPTIC_ACTUATOR

#if defined ACTUATOR_CLOSED_LOOP
#define LIB_SEL 0x00
#define LOOP_SEL 0x00
#elif defined ACTUATOR_OPEN_LOOP
#define LIB_SEL DRV2625_REG_LIBRARY_OPENLOOP
#define LOOP_SEL DRV2625_REG_LRAERM_OPENLOOP
#else
#error "Must define either CLOSED_LOOP or OPEN_LOOP"
#endif

#if defined ACTUATOR_LRA
#define LRA_ERM_SEL DRV2625_REG_LRAERM_LRA
#elif defined ACTUATOR_ERM
#define LRA_ERM_SEL 0x00
#else
#error "Must define either LRA or ERM"
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
  bool playing_rtp;

} haptic_driver_t;

// Haptic driver instance
static haptic_driver_t g_haptic_driver = {
    .initialized = false,
};

static bool drv2625_set_reg(i2c_bus_t *bus, uint8_t addr, uint8_t value) {
  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 2,
          .data = {addr, value},
      },
  };

  i2c_packet_t pkt = {
      .address = DRV2625_I2C_ADDRESS,
      .op_count = ARRAY_LENGTH(ops),
      .ops = ops,
  };

  if (I2C_STATUS_OK != i2c_bus_submit_and_wait(bus, &pkt)) {
    return false;
  }

  return true;
}

bool haptic_init(void) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (driver->initialized) {
    return false;
  }

  memset(driver, 0, sizeof(haptic_driver_t));

  GPIO_InitTypeDef GPIO_InitStructure = {0};

#ifdef DRV2625_RESET_PIN
  DRV2625_RESET_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = DRV2625_RESET_PIN;
  HAL_GPIO_WritePin(DRV2625_RESET_PORT, DRV2625_RESET_PIN, GPIO_PIN_RESET);
  HAL_GPIO_Init(DRV2625_RESET_PORT, &GPIO_InitStructure);
  systick_delay_ms(1);
  HAL_GPIO_WritePin(DRV2625_RESET_PORT, DRV2625_RESET_PIN, GPIO_PIN_SET);
  systick_delay_ms(1);
#endif

  DRV2625_TRIG_CLK_ENA();
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = DRV2625_TRIG_PIN;
  GPIO_InitStructure.Alternate = DRV2625_TRIG_AF;
  HAL_GPIO_Init(DRV2625_TRIG_PORT, &GPIO_InitStructure);

  driver->i2c_bus = i2c_bus_open(DRV2625_I2C_INSTANCE);
  if (driver->i2c_bus == NULL) {
    goto cleanup;
  }

  // select library
  if (!drv2625_set_reg(driver->i2c_bus, DRV2625_REG_LIBRARY,
                       LIB_SEL | DRV2625_REG_LIBRARY_GAIN_25)) {
    goto cleanup;
  }

  if (!drv2625_set_reg(
          driver->i2c_bus, DRV2625_REG_LRAERM,
          LRA_ERM_SEL | LOOP_SEL | DRV2625_REG_LRAERM_AUTO_BRK_OL)) {
    goto cleanup;
  }

  if (!drv2625_set_reg(driver->i2c_bus, DRV2625_REG_OD_CLAMP,
                       ACTUATOR_OD_CLAMP)) {
    goto cleanup;
  }

  if (!drv2625_set_reg(driver->i2c_bus, DRV2625_REG_LRA_WAVE_SHAPE,
                       DRV2625_REG_LRA_WAVE_SHAPE_SINE)) {
    goto cleanup;
  }

  if (!drv2625_set_reg(driver->i2c_bus, DRV2625_REG_OL_LRA_PERIOD_LO,
                       ACTUATOR_LRA_PERIOD & 0xFF)) {
    goto cleanup;
  }

  if (!drv2625_set_reg(driver->i2c_bus, DRV2625_REG_OL_LRA_PERIOD_HI,
                       ACTUATOR_LRA_PERIOD >> 8)) {
    goto cleanup;
  }

  DRV2625_TRIG_TIM_CLK_ENA();
  TIM_HandleTypeDef TIM_Handle = {0};
  TIM_Handle.State = HAL_TIM_STATE_RESET;
  TIM_Handle.Instance = DRV2625_TRIG_TIM;
  TIM_Handle.Init.Period = 0;
  TIM_Handle.Init.Prescaler = SystemCoreClock / 10000;
  TIM_Handle.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
  TIM_Handle.Init.CounterMode = TIM_COUNTERMODE_UP;
  TIM_Handle.Init.RepetitionCounter = 0;
  HAL_TIM_OnePulse_Init(&TIM_Handle, TIM_OPMODE_SINGLE);

  TIM_OnePulse_InitTypeDef TIM_OP_InitStructure = {0};
  TIM_OP_InitStructure.OCMode = TIM_OCMODE_PWM2;
  TIM_OP_InitStructure.OCPolarity = TIM_OCPOLARITY_HIGH;
  TIM_OP_InitStructure.Pulse = 1;
  TIM_OP_InitStructure.OCNPolarity = TIM_OCNPOLARITY_HIGH;
  HAL_TIM_OnePulse_ConfigChannel(&TIM_Handle, &TIM_OP_InitStructure,
                                 TIM_CHANNEL_1, TIM_CHANNEL_2);

  HAL_TIM_OC_Start(&TIM_Handle, TIM_CHANNEL_1);

  DRV2625_TRIG_TIM->BDTR |= TIM_BDTR_MOE;

  driver->initialized = true;
  driver->enabled = true;

  return true;

cleanup:
  i2c_bus_close(driver->i2c_bus);
  memset(driver, 0, sizeof(haptic_driver_t));
#ifdef DRV2625_RESET_PIN
  HAL_GPIO_WritePin(DRV2625_RESET_PORT, DRV2625_RESET_PIN, GPIO_PIN_RESET);
#endif
  return false;
}

void haptic_deinit(void) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return;
  }

  i2c_bus_close(driver->i2c_bus);

  // TODO: deinitialize GPIOs and the TIMER

  memset(driver, 0, sizeof(haptic_driver_t));
}

void haptic_set_enabled(bool enabled) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return;
  }

  driver->enabled = enabled;
}

bool haptic_get_enabled(void) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return false;
  }

  return driver->enabled;
}

static bool haptic_play_rtp(int8_t amplitude, uint16_t duration_ms) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return false;
  }

  if (!driver->playing_rtp) {
    if (!drv2625_set_reg(
            driver->i2c_bus, DRV2625_REG_MODE,
            DRV2625_REG_MODE_RTP | DRV2625_REG_MODE_TRGFUNC_ENABLE)) {
      return false;
    }

    driver->playing_rtp = true;
  }

  if (!drv2625_set_reg(driver->i2c_bus, DRV2625_REG_RTP, (uint8_t)amplitude)) {
    return false;
  }

  if (duration_ms > 6500) {
    duration_ms = 6500;
  }
  if (duration_ms == 0) {
    return true;
  }

  DRV2625_TRIG_TIM->CNT = 1;
  DRV2625_TRIG_TIM->CCR1 = 1;
  DRV2625_TRIG_TIM->ARR = duration_ms * 10;
  DRV2625_TRIG_TIM->CR1 |= TIM_CR1_CEN;

  return true;
}

static bool haptic_play_lib(drv2625_lib_effect_t effect) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return false;
  }

  driver->playing_rtp = false;

  if (!drv2625_set_reg(driver->i2c_bus, DRV2625_REG_MODE,
                       DRV2625_REG_MODE_WAVEFORM)) {
    return false;
  }

  if (!drv2625_set_reg(driver->i2c_bus, DRV2625_REG_WAVESEQ1, effect)) {
    return false;
  }

  if (!drv2625_set_reg(driver->i2c_bus, DRV2625_REG_WAVESEQ2, 0)) {
    return false;
  }

  if (!drv2625_set_reg(driver->i2c_bus, DRV2625_REG_GO, DRV2625_REG_GO_GO)) {
    return false;
  }

  return true;
}

bool haptic_play(haptic_effect_t effect) {
  haptic_driver_t *driver = &g_haptic_driver;

  if (!driver->initialized) {
    return false;
  }

  if (!driver->enabled) {
    return true;
  }

  switch (effect) {
    case HAPTIC_BUTTON_PRESS:
      return haptic_play_rtp(PRESS_EFFECT_AMPLITUDE, PRESS_EFFECT_DURATION);
      break;
    case HAPTIC_HOLD_TO_CONFIRM:
      return haptic_play_lib(DOUBLE_CLICK_60);
      break;
    default:
      break;
  }

  return false;
}

bool haptic_play_custom(int8_t amplitude_pct, uint16_t duration_ms) {
  if (amplitude_pct < 0) {
    amplitude_pct = 0;
  } else if (amplitude_pct > 100) {
    amplitude_pct = 100;
  }

  return haptic_play_rtp((int8_t)((amplitude_pct * MAX_AMPLITUDE) / 100),
                         duration_ms);
}

bool haptic_test(uint16_t duration_ms) {
  return haptic_play_rtp(PRODTEST_EFFECT_AMPLITUDE, duration_ms);
}

#endif  // KERNEL_MODE
