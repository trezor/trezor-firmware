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

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "common.h"

#include "ft6x36.h"
#include "i2c.h"
#include "touch.h"

#ifdef TOUCH_PANEL_LX154A2422CPT23
#include "panels/lx154a2422cpt23.h"
#endif

// #define TOUCH_TRACE_REGS
// #define TOUCH_TRACE_EVENT

typedef struct {
  // Set if the driver is initialized
  secbool initialized;
  // Set if the driver is ready to report touches.
  // FT6X36 needs about 300ms after power-up to stabilize.
  secbool ready;
  // Captured tick counter when `touch_init()` was called
  uint32_t init_ticks;
  // Time (in ticks) when touch_get_event() was called last time
  uint32_t poll_ticks;
  // Time (in ticks) when the touch registers were read last time
  uint32_t read_ticks;
  // Set if the touch controller is currently touched
  // (respectively, the we detected a touch event)
  bool pressed;
  // Previously reported x-coordinate
  uint16_t last_x;
  // Previously reported y-coordinate
  uint16_t last_y;

} touch_driver_t;

// Touch driver instance
static touch_driver_t g_touch_driver = {
    .initialized = secfalse,
};

// Reads a subsequent registers from the FT6X36.
//
// Returns: `sectrue` if the register was read
// successfully, `secfalse` otherwise.
//
// If the I2C bus is busy, the function will cycle the
// bus and retry the operation.
static secbool ft6x36_read_regs(uint8_t reg, uint8_t* value, size_t count) {
  uint16_t i2c_bus = TOUCH_I2C_INSTANCE;
  uint8_t i2c_addr = FT6X36_I2C_ADDR;
  uint8_t txdata[] = {reg};
  uint8_t retries = 3;

  do {
    int result = i2c_transmit(i2c_bus, i2c_addr, txdata, sizeof(txdata), 10);
    if (HAL_OK == result) {
      result = i2c_receive(i2c_bus, i2c_addr, value, count, 10);
    }

    if (HAL_OK == result) {
      // success
      return sectrue;
    } else if (HAL_BUSY == result && retries > 0) {
      // I2C bus is busy, cycle it and try again
      i2c_cycle(i2c_bus);
      retries--;
    } else {
      // Aother error or retries exhausted
      return secfalse;
    }
  } while (1);
}

// Writes a register to the FT6X36.
//
// Returns: `sectrue` if the register was written
// successfully, `secfalse` otherwise.
//
// If the I2C bus is busy, the function will cycle the
// bus and retry the operation.
static secbool ft6x36_write_reg(uint8_t reg, uint8_t value) {
  uint16_t i2c_bus = TOUCH_I2C_INSTANCE;
  uint8_t i2c_addr = FT6X36_I2C_ADDR;
  uint8_t txdata[] = {reg, value};
  uint8_t retries = 3;

  do {
    int result = i2c_transmit(i2c_bus, i2c_addr, txdata, sizeof(txdata), 10);
    if (HAL_OK == result) {
      // success
      return sectrue;
    } else if (HAL_BUSY == result && retries > 0) {
      // I2C bus is busy, cycle it and try again
      i2c_cycle(i2c_bus);
      retries--;
    } else {
      // Another error or retries exhausted
      return secfalse;
    }
  } while (1);
}

// Powers down the touch controller and puts all
// the pins in the proper state to save power.
static void ft6x36_power_down(void) {
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
  GPIO_InitTypeDef GPIO_InitStructure = {0};

  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = TOUCH_INT_PIN;
  HAL_GPIO_Init(TOUCH_INT_PORT, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = TOUCH_RST_PIN;
  HAL_GPIO_Init(TOUCH_RST_PORT, &GPIO_InitStructure);
  GPIO_InitStructure.Pin = TOUCH_ON_PIN;
  HAL_GPIO_Init(TOUCH_ON_PORT, &GPIO_InitStructure);

  if (state == GPIO_PIN_SET) {
    // 90 ms for circuitry to stabilize (being conservative)
    hal_delay(90);
  }
}

// Powers up the touch controller and do proper reset sequence
//
// `ft6x36_power_down()` must be called before calling this first time function
// to properly initialize the GPIO pins.
static void ft6x36_power_up(void) {
  // Ensure the touch controller is in reset state
  HAL_GPIO_WritePin(TOUCH_RST_PORT, TOUCH_RST_PIN, GPIO_PIN_RESET);
  // Power up the touch controller
  HAL_GPIO_WritePin(TOUCH_ON_PORT, TOUCH_ON_PIN, GPIO_PIN_RESET);

  // Wait until the circuit fully kicks-in
  // (5ms is the minimum time required for the reset signal to be effective)
  hal_delay(10);

  // Enable intterrupt input
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_IT_RISING;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = TOUCH_INT_PIN;
  HAL_GPIO_Init(TOUCH_INT_PORT, &GPIO_InitStructure);

  // Release touch controller from reset
  HAL_GPIO_WritePin(TOUCH_RST_PORT, TOUCH_RST_PIN, GPIO_PIN_SET);

  // Wait for the touch controller to boot up
  hal_delay(5);

  // Clear the flag indicating rising edge on INT_PIN
  __HAL_GPIO_EXTI_CLEAR_FLAG(TOUCH_INT_PIN);
}

// Checks if the touch controller has an interrupt pending
// which indicates that new data is available.
//
// The function clears the interrupt flag if it was set so the
// next call returns `false` if no new impulses were detected.
static bool ft6x36_test_and_clear_interrupt(void) {
  uint32_t event = __HAL_GPIO_EXTI_GET_FLAG(TOUCH_INT_PIN);
  if (event != 0) {
    __HAL_GPIO_EXTI_CLEAR_FLAG(TOUCH_INT_PIN);
  }

  return event != 0;
}

// Configures the touch controller to the funtional state.
static secbool ft6x36_configure(void) {
  const static uint8_t config[] = {
      // Set touch controller to the interrupt trigger mode.
      // Basically, CTPM generates a pulse when new data is available.
      FT6X36_REG_G_MODE,
      0x01,
      FT6X36_REG_TH_GROUP,
      TOUCH_SENSITIVITY,
  };

  _Static_assert(sizeof(config) % 2 == 0);

  for (int i = 0; i < sizeof(config); i += 2) {
    uint8_t reg = config[i];
    uint8_t value = config[i + 1];

    if (sectrue != ft6x36_write_reg(reg, value)) {
      return secfalse;
    }
  }

  return sectrue;
}

static void ft6x36_panel_correction(uint16_t x, uint16_t y, uint16_t* x_new,
                                    uint16_t* y_new) {
#ifdef TOUCH_PANEL_LX154A2422CPT23
  lx154a2422cpt23_touch_correction(x, y, x_new, y_new);
#else
  *x_new = x;
  *y_new = y;
#endif
}

secbool touch_init(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue == driver->initialized) {
    // The driver is already initialized
    return sectrue;
  }

  // Initialize GPIO to the default configuration
  // (touch controller is powered down)
  ft6x36_power_down();

  // Power up the touch controller and perform the reset sequence
  ft6x36_power_up();

  // Configure the touch controller
  if (sectrue != ft6x36_configure()) {
    ft6x36_power_down();
    return secfalse;
  }

  driver->init_ticks = hal_ticks_ms();
  driver->poll_ticks = driver->init_ticks;
  driver->read_ticks = driver->init_ticks;
  driver->initialized = sectrue;

  return sectrue;
}

void touch_deinit(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue == driver->initialized) {
    // Do not need to deinitialized the controller
    // just power it off
    ft6x36_power_down();

    memset(driver, 0, sizeof(touch_driver_t));
  }
}

secbool touch_ready(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue == driver->initialized && sectrue != driver->ready) {
    // FT6X36 does not report events for 300ms
    // after it is released from the reset state
    if ((int)(hal_ticks_ms() - driver->init_ticks) >= 310) {
      driver->ready = sectrue;
    }
  }

  return driver->ready;
}

secbool touch_set_sensitivity(uint8_t value) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue == driver->initialized) {
    return ft6x36_write_reg(FT6X36_REG_TH_GROUP, value);
  } else {
    return secfalse;
  }
}

uint8_t touch_get_version(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue != driver->initialized) {
    return 0;
  }

  // After powering up the touch controller, we need to wait
  // for an unspecified amount of time (~100ms) before attempting
  // to read the firmware version. If we try to read too soon, we get 0x00
  // and the chip behaves unpredictably.
  while (sectrue != touch_ready()) {
    hal_delay(1);
  }

  uint8_t fw_version = 0;

  if (sectrue != ft6x36_read_regs(FT6X36_REG_FIRMID, &fw_version, 1)) {
    ft6x36_power_down();
    return secfalse;
  }

  return fw_version;
}

secbool touch_activity(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue == driver->initialized) {
    if (ft6x36_test_and_clear_interrupt()) {
      return sectrue;
    }
  }

  return secfalse;
}

#ifdef TOUCH_TRACE_REGS
void trace_regs(uint8_t* regs) {
  // Extract gesture ID (FT6X63_GESTURE_xxx)
  uint8_t gesture = regs[FT6X63_REG_GEST_ID];

  // Extract number of touches (0, 1, 2) or 0x0F before
  // the first touch (tested with FT6206)
  uint8_t nb_touches = regs[FT6X63_REG_TD_STATUS] & 0x0F;

  // Extract event flags (one of press down, contact, lift up)
  uint8_t flags = regs[FT6X63_REG_P1_XH] & FT6X63_EVENT_MASK;

  // Extract touch coordinates
  uint16_t x = ((regs[FT6X63_REG_P1_XH] & 0x0F) << 8) | regs[FT6X63_REG_P1_XL];
  uint16_t y = ((regs[FT6X63_REG_P1_YH] & 0x0F) << 8) | regs[FT6X63_REG_P1_YL];

  char event;

  if (flags == FT6X63_EVENT_PRESS_DOWN) {
    event = 'D';
  } else if (flags == FT6X63_EVENT_CONTACT) {
    event = 'C';
  } else if (flags == FT6X63_EVENT_LIFT_UP) {
    event = 'U';
  } else {
    event = '-';
  }

  uint32_t time = hal_ticks_ms() % 10000;

  printf("%04ld [gesture=%02X, nb_touches=%d, flags=%c, x=%3d, y=%3d]\r\n",
         time, gesture, nb_touches, event, x, y);
}
#endif

#ifdef TOUCH_TRACE_EVENT
void trace_event(uint32_t event) {
  char event_type = (event & TOUCH_START)  ? 'D'
                    : (event & TOUCH_MOVE) ? 'M'
                    : (event & TOUCH_END)  ? 'U'
                                           : '-';

  uint16_t x = touch_unpack_x(event);
  uint16_t y = touch_unpack_y(event);

  uint32_t time = hal_ticks_ms() % 10000;

  printf("%04ld [event=%c, x=%3d, y=%3d]\r\n", time, event_type, x, y);
}
#endif

uint32_t touch_get_event(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue != driver->initialized) {
    return 0;
  }

  // Content of registers 0x00 - 0x06 read from the touch controller
  uint8_t regs[7];

  // Ensure the registers are within the bounds
  _Static_assert(sizeof(regs) > FT6X63_REG_GEST_ID);
  _Static_assert(sizeof(regs) > FT6X63_REG_TD_STATUS);
  _Static_assert(sizeof(regs) > FT6X63_REG_P1_XH);
  _Static_assert(sizeof(regs) > FT6X63_REG_P1_XL);
  _Static_assert(sizeof(regs) > FT6X63_REG_P1_YH);
  _Static_assert(sizeof(regs) > FT6X63_REG_P1_YL);

  uint32_t ticks = hal_ticks_ms();

  // Test if the touch_get_event() is starving (not called frequently enough)
  bool starving = (int32_t)(ticks - driver->poll_ticks) > 300 /* ms */;
  driver->poll_ticks = ticks;

  // Test if the touch controller is polled too frequently
  // (less than 20ms since the last read)
  bool toofast = (int32_t)(ticks - driver->read_ticks) < 20 /* ms */;

  // Fast track: if there is no new event and the touch controller
  // is not touched, we do not need to read the registers
  if (!ft6x36_test_and_clear_interrupt() && (!driver->pressed || toofast)) {
    return 0;
  }

  driver->read_ticks = ticks;

  // Read the set of registers containing touch event and coordinates
  if (sectrue != ft6x36_read_regs(0x00, regs, sizeof(regs))) {
    // Failed to read the touch registers
    return 0;
  }

#ifdef TOUCH_TRACE_REGS
  trace_regs(regs);
#endif

  // Extract gesture ID (FT6X63_GESTURE_xxx)
  uint8_t gesture = regs[FT6X63_REG_GEST_ID];

  if (gesture != FT6X36_GESTURE_NONE) {
    // This is here for unknown historical reasons
    // It seems we can't get here with FT6X36
    return 0;
  }

  // Extract number of touches (0, 1, 2) or 0x0F before
  // the first touch (tested with FT6206)
  uint8_t nb_touches = regs[FT6X63_REG_TD_STATUS] & 0x0F;

  // Extract event flags (one of press down, contact, lift up)
  uint8_t flags = regs[FT6X63_REG_P1_XH] & FT6X63_EVENT_MASK;

  // Extract touch coordinates
  uint16_t x_raw =
      ((regs[FT6X63_REG_P1_XH] & 0x0F) << 8) | regs[FT6X63_REG_P1_XL];
  uint16_t y_raw =
      ((regs[FT6X63_REG_P1_YH] & 0x0F) << 8) | regs[FT6X63_REG_P1_YL];

  uint16_t x, y;

  ft6x36_panel_correction(x_raw, y_raw, &x, &y);

  uint32_t event = 0;

  uint32_t xy = touch_pack_xy(x, y);

  if ((nb_touches == 1) && (flags == FT6X63_EVENT_PRESS_DOWN)) {
    if (!driver->pressed) {
      // Finger was just pressed down
      event = TOUCH_START | xy;
    } else {
      if ((x != driver->last_x) || (y != driver->last_y)) {
        // It looks like we have missed the lift up event
        // We should send the TOUCH_END event here with old coordinates
        event = TOUCH_END | touch_pack_xy(driver->last_x, driver->last_y);
      } else {
        // We have received the same coordinates as before,
        // probably this is the same start event, or a quick bounce,
        // we should ignore it.
      }
    }
  } else if ((nb_touches == 1) && (flags == FT6X63_EVENT_CONTACT)) {
    if (driver->pressed) {
      if ((x != driver->last_x) || (y != driver->last_y)) {
        // Report the move event only if the coordinates
        // have changed
        event = TOUCH_MOVE | xy;
      }
    } else {
      // We have missed the press down event, we have to simulate it.
      // But ensure we don't simulate TOUCH_START if touch_get_event() is not
      // called frequently enough to not produce false events.
      if (!starving) {
        event = TOUCH_START | xy;
      }
    }
  } else if ((nb_touches == 0) && (flags == FT6X63_EVENT_LIFT_UP)) {
    if (driver->pressed) {
      // Finger was just lifted up
      event = TOUCH_END | xy;
    } else {
      if (!starving && ((x != driver->last_x) || (y != driver->last_y))) {
        // We have missed the PRESS_DOWN event.
        // Report the start event only if the coordinates
        // have changed and driver is not starving.
        // This suggest that the previous touch was very short,
        // or/and the driver is not called very frequently.
        event = TOUCH_START | xy;
      } else {
        // Either the driver is starving or the coordinates
        // have not changed, which would suggest that the TOUCH_END
        // is repeated, so no event is needed -this should not happen
        // since two consecutive LIFT_UPs are not possible due to
        // testing the interrupt line before reading the registers.
      }
    }
  }

  // remember the last state
  if ((event & TOUCH_START) || (event & TOUCH_MOVE)) {
    driver->pressed = true;
  } else if (event & TOUCH_END) {
    driver->pressed = false;
  }

  driver->last_x = x;
  driver->last_y = y;

#ifdef TOUCH_TRACE_EVENT
  trace_event(event);
#endif

  return event;
}
