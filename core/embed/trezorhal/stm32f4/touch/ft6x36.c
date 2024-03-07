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
#include TREZOR_BOARD

#include <string.h>

#include "common.h"
#include "secbool.h"

#include "ft6x36.h"
#include "i2c.h"
#include "touch.h"

#define TOUCH_ADDRESS \
  (0x38U << 1)  // the HAL requires the 7-bit address to be shifted by one bit
#define TOUCH_PACKET_SIZE 7U
#define EVENT_PRESS_DOWN 0x00U
#define EVENT_CONTACT 0x80U
#define EVENT_LIFT_UP 0x40U
#define EVENT_NO_EVENT 0xC0U
#define GESTURE_NO_GESTURE 0x00U
#define X_POS_MSB (touch_data[3] & 0x0FU)
#define X_POS_LSB (touch_data[4])
#define Y_POS_MSB (touch_data[5] & 0x0FU)
#define Y_POS_LSB (touch_data[6])

#define EVENT_OLD_TIMEOUT_MS 2000
#define EVENT_MISSING_TIMEOUT_MS 50

static uint32_t touch_init_ticks = 0;

static void touch_default_pin_state(void) {
  GPIO_PinState state = HAL_GPIO_ReadPin(TOUCH_ON_PORT, TOUCH_ON_PIN);

  // set power off and other pins as per section 3.5 of FT6236 datasheet
  HAL_GPIO_WritePin(TOUCH_ON_PORT, TOUCH_ON_PIN,
                    GPIO_PIN_SET);  // CTP_ON (active low) i.e.- CTPM power
                                    // off when set/high/log 1
  HAL_GPIO_WritePin(TOUCH_INT_PORT, TOUCH_INT_PIN,
                    GPIO_PIN_RESET);  // CTP_INT normally an input, but drive
                                      // low as an output while powered off
  HAL_GPIO_WritePin(TOUCH_RST_PORT, TOUCH_RST_PIN,
                    GPIO_PIN_RESET);  // CTP_REST (active low) i.e.- CTPM
                                      // held in reset until released

  // set above pins to OUTPUT / NOPULL
  GPIO_InitTypeDef GPIO_InitStructure;

  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = TOUCH_INT_PIN;
  HAL_GPIO_Init(TOUCH_INT_PORT, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = TOUCH_RST_PIN;
  HAL_GPIO_Init(TOUCH_RST_PORT, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = TOUCH_ON_PIN;
  HAL_GPIO_Init(TOUCH_ON_PORT, &GPIO_InitStructure);

  // in-case power was on, or CTPM was active make sure to wait long enough
  // for these changes to take effect. a reset needs to be low for
  // a minimum of 5ms. also wait for power circuitry to stabilize (if it
  // changed).
  HAL_Delay(10);

  if (state == GPIO_PIN_SET) {
    HAL_Delay(90);  // add 90 ms for circuitry to stabilize (being conservative)
  }
}

static void touch_active_pin_state(void) {
  HAL_GPIO_WritePin(TOUCH_ON_PORT, TOUCH_ON_PIN, GPIO_PIN_RESET);  // CTP_ON
  HAL_Delay(10);  // we need to wait until the circuit fully kicks-in

  GPIO_InitTypeDef GPIO_InitStructure;

  // capacitive touch panel module (CTPM) interrupt (INT) input
  GPIO_InitStructure.Mode = GPIO_MODE_IT_RISING;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = TOUCH_INT_PIN;
  HAL_GPIO_Init(TOUCH_INT_PORT, &GPIO_InitStructure);
  __HAL_GPIO_EXTI_CLEAR_FLAG(TOUCH_INT_PIN);

  HAL_GPIO_WritePin(TOUCH_RST_PORT, TOUCH_RST_PIN,
                    GPIO_PIN_SET);  // release CTPM reset

  touch_init_ticks = hal_ticks_ms();

  HAL_Delay(5);
}

void touch_set_mode(void) {
  // set register 0xA4 G_MODE to interrupt trigger mode (0x01). basically, CTPM
  // generates a pulse when new data is available
  uint8_t touch_panel_config[] = {0xA4, 0x01};
  for (int i = 0; i < 3; i++) {
    if (HAL_OK == i2c_transmit(TOUCH_I2C_INSTANCE, TOUCH_ADDRESS,
                               touch_panel_config, sizeof(touch_panel_config),
                               10)) {
      return;
    }
    i2c_cycle(TOUCH_I2C_INSTANCE);
  }

  ensure(secfalse, "Touch screen panel was not loaded properly.");
}

void touch_power_on(void) {
  touch_default_pin_state();

  // turn on CTP circuitry
  touch_active_pin_state();
}

void touch_power_off(void) {
  // turn off CTP circuitry
  HAL_Delay(50);
  touch_default_pin_state();
}

void touch_init(void) {
  GPIO_InitTypeDef GPIO_InitStructure;

  // PC4 capacitive touch panel module (CTPM) interrupt (INT) input
  GPIO_InitStructure.Mode = GPIO_MODE_IT_RISING;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = TOUCH_INT_PIN;
  HAL_GPIO_Init(TOUCH_INT_PORT, &GPIO_InitStructure);
  __HAL_GPIO_EXTI_CLEAR_FLAG(TOUCH_INT_PIN);

  touch_set_mode();
  touch_sensitivity(TOUCH_SENSITIVITY);
}

void touch_wait_until_ready(void) {
  // wait for the touch controller to be ready
  while (hal_ticks_ms() - touch_init_ticks < 310) {
    HAL_Delay(1);
  }
}

void touch_sensitivity(uint8_t value) {
  // set panel threshold (TH_GROUP) - default value is 0x12
  uint8_t touch_panel_threshold[] = {0x80, value};
  for (int i = 0; i < 3; i++) {
    if (HAL_OK == i2c_transmit(TOUCH_I2C_INSTANCE, TOUCH_ADDRESS,
                               touch_panel_threshold,
                               sizeof(touch_panel_threshold), 10)) {
      return;
    }
    i2c_cycle(TOUCH_I2C_INSTANCE);
  }

  ensure(secfalse, "Touch screen panel was not loaded properly.");
}

uint32_t touch_is_detected(void) {
  // check the interrupt line coming in from the CTPM.
  // the line make a short pulse, which sets an interrupt flag when new data is
  // available.
  // Reference section 1.2 of "Application Note for FT6x06 CTPM". we
  // configure the touch controller to use "interrupt trigger mode".

  uint32_t event = __HAL_GPIO_EXTI_GET_FLAG(TOUCH_INT_PIN);
  if (event != 0) {
    __HAL_GPIO_EXTI_CLEAR_FLAG(TOUCH_INT_PIN);
  }

  return event;
}

uint32_t check_timeout(uint32_t prev, uint32_t timeout) {
  uint32_t current = hal_ticks_ms();
  uint32_t diff = current - prev;

  if (diff >= timeout) {
    return 1;
  }

  return 0;
}

uint32_t touch_read(void) {
  static uint8_t touch_data[TOUCH_PACKET_SIZE],
      previous_touch_data[TOUCH_PACKET_SIZE];
  static uint32_t xy;
  static uint32_t last_check_time = 0;
  static uint32_t last_event_time = 0;
  static int touching = 0;

  uint32_t detected = touch_is_detected();

  if (detected == 0) {
    last_check_time = hal_ticks_ms();

    if (touching && check_timeout(last_event_time, EVENT_MISSING_TIMEOUT_MS)) {
      // we didn't detect an event for a long time, but there was an active
      // touch: send END event, as we probably missed the END event
      touching = 0;
      return TOUCH_END | xy;
    }

    return 0;
  }

  if ((touching == 0) &&
      (check_timeout(last_check_time, EVENT_OLD_TIMEOUT_MS))) {
    // we have detected an event, but it might be too old, rather drop it
    // (only dropping old events if there was no touch active)
    last_check_time = hal_ticks_ms();
    return 0;
  }

  last_check_time = hal_ticks_ms();

  uint8_t outgoing[] = {0x00};  // start reading from address 0x00
  int result = i2c_transmit(TOUCH_I2C_INSTANCE, TOUCH_ADDRESS, outgoing,
                            sizeof(outgoing), 1);
  if (result != HAL_OK) {
    if (result == HAL_BUSY) i2c_cycle(TOUCH_I2C_INSTANCE);
    return 0;
  }

  if (HAL_OK != i2c_receive(TOUCH_I2C_INSTANCE, TOUCH_ADDRESS, touch_data,
                            TOUCH_PACKET_SIZE, 1)) {
    return 0;  // read failure
  }

  last_event_time = hal_ticks_ms();

  if (0 == memcmp(previous_touch_data, touch_data, TOUCH_PACKET_SIZE)) {
    return 0;  // same data, filter it out
  } else {
    memcpy(previous_touch_data, touch_data, TOUCH_PACKET_SIZE);
  }

  const uint32_t number_of_touch_points =
      touch_data[2] & 0x0F;  // valid values are 0, 1, 2 (invalid 0xF before
                             // first touch) (tested with FT6206)
  const uint32_t event_flag = touch_data[3] & 0xC0;
  if (touch_data[1] == GESTURE_NO_GESTURE) {
    xy = TRANSFORM_TOUCH_COORDS((X_POS_MSB << 8) | X_POS_LSB,
                                (Y_POS_MSB << 8) | Y_POS_LSB);
    if ((number_of_touch_points == 1) && (event_flag == EVENT_PRESS_DOWN)) {
      touching = 1;
      return TOUCH_START | xy;
    } else if ((number_of_touch_points == 1) && (event_flag == EVENT_CONTACT)) {
      if (touching) {
        return TOUCH_MOVE | xy;
      } else {
        touching = 1;
        return TOUCH_START | xy;
      }
    } else if ((number_of_touch_points == 0) && (event_flag == EVENT_LIFT_UP)) {
      touching = 0;
      return TOUCH_END | xy;
    }
  }

  return 0;
}
