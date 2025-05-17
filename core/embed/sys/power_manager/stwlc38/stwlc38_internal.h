
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

#pragma once

#include <io/i2c_bus.h>
#include <trezor_types.h>

#ifdef KERNEL_MODE

// !@# TODO: put following constants the board file
#define STWLC38_INT_PIN GPIO_PIN_15
#define STWLC38_INT_PORT GPIOG
#define STWLC38_INT_PIN_CLK_ENA __HAL_RCC_GPIOG_CLK_ENABLE
#define STWLC38_EXTI_INTERRUPT_GPIOSEL EXTI_GPIOG
#define STWLC38_EXTI_INTERRUPT_LINE EXTI_LINE_15
#define STWLC38_EXTI_INTERRUPT_NUM EXTI15_IRQn
#define STWLC38_EXTI_INTERRUPT_HANDLER EXTI15_IRQHandler
#define STWLC38_ENB_PIN GPIO_PIN_3
#define STWLC38_ENB_PORT GPIOD
#define STWLC38_ENB_PIN_CLK_ENA __HAL_RCC_GPIOD_CLK_ENABLE

// Period of the report readout [ms]
#define STWLC38_REPORT_READOUT_INTERVAL_MS 500

// STWLC38 FSM states
typedef enum {
  STWLC38_STATE_POWER_DOWN = 0,
  STWLC38_STATE_IDLE,
  STWLC38_STATE_VOUT_ENABLE,
  STWLC38_STATE_VOUT_DISABLE,
  STWLC38_STATE_REPORT_READOUT,
} stwlc38_fsm_state_t;

typedef struct {
  // Rectified voltage [mV]
  uint16_t vrect;
  // Main LDO voltage output [mV]
  uint16_t vout;
  // Output current [mA]
  uint16_t icur;
  // Chip temperature [°C * 10]
  uint16_t tmeas;
  // Operating frequency [kHz]
  uint16_t opfreq;
  // NTC Temperature [°C * 10]
  uint16_t ntc;
  // RX Int Status 0
  uint8_t status0;

} stwlc38_report_regs_t;

// STWLC38 driver state
typedef struct {
  // Set if the driver is initialized
  bool initialized;

  // EXTI handle
  EXTI_HandleTypeDef EXTI_Handle;

  // I2C bus where the STWLC38 is connected
  i2c_bus_t *i2c_bus;
  // Storage for the pending I2C packet
  i2c_packet_t pending_i2c_packet;
  // Report register (global buffer used for report readout)
  stwlc38_report_regs_t report_regs;
  // Timer used for periodic report readout
  systimer_t *timer;

  // Main LDO output current state
  bool vout_enabled;
  // Main LDO output requested state
  bool vout_enabled_requested;
  // Flags set if report readout is scheduled
  bool report_readout_requested;

  // Current report
  stwlc38_report_t report;
  // Current state of the FSM
  stwlc38_fsm_state_t state;

} stwlc38_driver_t;

extern stwlc38_driver_t g_stwlc38_driver;

#endif  // KERNEL_MODE
