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

#ifdef KERNEL_MODE

#include <io/i2c_bus.h>
#include <io/touch.h>
#include <sys/sysevent_source.h>
#include <sys/systick.h>
#include "ft6x36.h"

#ifdef TOUCH_PANEL_LX154A2422CPT23
#include "panels/lx154a2422cpt23.h"
#elif defined TOUCH_PANEL_LHS200KB_IF21
#include "panels/lhs200kb-if21.h"
#elif defined TOUCH_PANEL_LX250A2410A
#include "panels/lx250a2410a.h"
#endif

#include "../touch_fsm.h"

// #define TOUCH_TRACE_REGS
// #define TOUCH_TRACE_EVENT

typedef struct {
  // Set if the driver is initialized
  secbool initialized;
  // I2c bus where the touch controller is connected
  i2c_bus_t* i2c_bus;
  // Set if the driver is ready to report touches.
  // FT6X36 needs about 300ms after power-up to stabilize.
  secbool ready;
  // Captured tick counter when `touch_init()` was called
  uint32_t init_ticks;
  // Time (in ticks) when the touch registers were read last time
  uint32_t read_ticks;
  // Last reported touch state
  uint32_t state;
  // Touch state machine for each task
  touch_fsm_t tls[SYSTASK_MAX_TASKS];

} touch_driver_t;

// Touch driver instance
static touch_driver_t g_touch_driver = {
    .initialized = secfalse,
};

// Forward declarations
static const syshandle_vmt_t g_touch_handle_vmt;

// Reads a subsequent registers from the FT6X36.
//
// Returns: `sectrue` if the register was read
// successfully, `secfalse` otherwise.
//
// If the I2C bus is busy, the function will cycle the
// bus and retry the operation.
static secbool ft6x36_read_regs(i2c_bus_t* bus, uint8_t reg, uint8_t* value,
                                size_t count) {
  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 1,
          .data = {reg},
      },
      {
          .flags = I2C_FLAG_RX,
          .size = count,
          .ptr = value,
      },
  };

  i2c_packet_t pkt = {
      .address = FT6X36_I2C_ADDR,
      .op_count = ARRAY_LENGTH(ops),
      .ops = ops,
  };

  if (I2C_STATUS_OK != i2c_bus_submit_and_wait(bus, &pkt)) {
    return secfalse;
  }

  return sectrue;
}

// Writes a register to the FT6X36.
//
// Returns: `sectrue` if the register was written
// successfully, `secfalse` otherwise.
//
// If the I2C bus is busy, the function will cycle the
// bus and retry the operation.
static secbool ft6x36_write_reg(i2c_bus_t* bus, uint8_t reg, uint8_t value) {
  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 2,
          .data = {reg, value},
      },
  };

  i2c_packet_t pkt = {
      .address = FT6X36_I2C_ADDR,
      .op_count = ARRAY_LENGTH(ops),
      .ops = ops,
  };

  if (I2C_STATUS_OK != i2c_bus_submit_and_wait(bus, &pkt)) {
    return secfalse;
  }

  return sectrue;
}

// Wake up the touch controller from monitor mode.
//
// The FT3168 touch controller switches from active mode to monitor mode
// after a period of inactivity (the default setting is ~12s).
// This feature cannot be disabled (at least in the current controller
// firmware). When in this mode, it fails to respond to the first I2C command —
// writes are not ACKed, and reads return 0x00 or garbage data.
// To avoid this issue, we need to wake up the controller before
// sending any commands to it.
static void ft6x36_wake_up(i2c_bus_t* bus) {
#ifdef TOUCH_WAKEUP_WORKAROUND
  uint8_t temp;
  // Wake up the touch controller by reading one of its registers
  // (the specific register does not matter)
  ft6x36_read_regs(bus, 0x00, &temp, 1);
  // Wait for the touch controller to wake up
  // (not sure if this is necessary, but it's safer to include it)
  systick_delay_ms(1);
#endif
}

// Powers down the touch controller and puts all
// the pins in the proper state to save power.
static void ft6x36_power_down(void) {
#ifdef TOUCH_ON_PIN
  GPIO_PinState state = HAL_GPIO_ReadPin(TOUCH_ON_PORT, TOUCH_ON_PIN);

  // set power off and other pins as per section 3.5 of FT6236 datasheet
  HAL_GPIO_WritePin(TOUCH_ON_PORT, TOUCH_ON_PIN,
                    GPIO_PIN_SET);  // CTP_ON (active low) i.e.- CTPM power
                                    // off when set/high/log 1

#endif
  HAL_GPIO_WritePin(TOUCH_INT_PORT, TOUCH_INT_PIN,
                    GPIO_PIN_RESET);  // CTP_INT normally an input, but drive
                                      // low as an output while powered off

#ifdef TOUCH_RST_PIN
  HAL_GPIO_WritePin(TOUCH_RST_PORT, TOUCH_RST_PIN,
                    GPIO_PIN_RESET);  // CTP_REST (active low) i.e.- CTPM
                                      // held in reset until released
#endif

  HAL_GPIO_DeInit(TOUCH_INT_PORT, TOUCH_INT_PIN);

#if defined(TOUCH_RST_PIN) || defined(TOUCH_ON_PIN)
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;

#ifdef TOUCH_RST_PIN
  GPIO_InitStructure.Pin = TOUCH_RST_PIN;
  HAL_GPIO_Init(TOUCH_RST_PORT, &GPIO_InitStructure);
#endif

#ifdef TOUCH_ON_PIN
  GPIO_InitStructure.Pin = TOUCH_ON_PIN;
  HAL_GPIO_Init(TOUCH_ON_PORT, &GPIO_InitStructure);

  if (state == GPIO_PIN_SET) {
    // 90 ms for circuitry to stabilize (being conservative)
    systick_delay_ms(90);
  }
#endif
#endif
}

// Powers up the touch controller and do proper reset sequence
//
// `ft6x36_power_down()` must be called before calling this first time function
// to properly initialize the GPIO pins.
static void ft6x36_power_up(void) {
#ifdef TOUCH_RST_PIN
  // Ensure the touch controller is in reset state
  HAL_GPIO_WritePin(TOUCH_RST_PORT, TOUCH_RST_PIN, GPIO_PIN_RESET);
#endif

#ifdef TOUCH_ON_PIN
  // Power up the touch controller
  HAL_GPIO_WritePin(TOUCH_ON_PORT, TOUCH_ON_PIN, GPIO_PIN_RESET);
#endif

  // Wait until the circuit fully kicks-in
  // (5ms is the minimum time required for the reset signal to be effective)
  systick_delay_ms(10);

  // Enable intterrupt input
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_IT_RISING;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = TOUCH_INT_PIN;
  HAL_GPIO_Init(TOUCH_INT_PORT, &GPIO_InitStructure);

#ifdef TOUCH_RST_PIN
  // Release touch controller from reset
  HAL_GPIO_WritePin(TOUCH_RST_PORT, TOUCH_RST_PIN, GPIO_PIN_SET);
#endif

  // Wait for the touch controller to boot up
  systick_delay_ms(5);

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

// Configures the touch controller to the functional state.
static secbool ft6x36_configure(i2c_bus_t* i2c_bus) {
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

    if (sectrue != ft6x36_write_reg(i2c_bus, reg, value)) {
      return secfalse;
    }
  }

  return sectrue;
}

static void ft6x36_panel_correction(uint16_t x, uint16_t y, uint16_t* x_new,
                                    uint16_t* y_new) {
#ifdef TOUCH_PANEL_LX154A2422CPT23
  lx154a2422cpt23_touch_correction(x, y, x_new, y_new);
#elif defined TOUCH_PANEL_LHS200KB_IF21
  lhs200kb_if21_touch_correction(x, y, x_new, y_new);
#elif defined TOUCH_PANEL_LX250A2410A
  lx250a2410a_touch_correction(x, y, x_new, y_new);
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

  memset(driver, 0, sizeof(touch_driver_t));

  // Initialize GPIO to the default configuration
  // (touch controller is powered down)
  ft6x36_power_down();

  // Power up the touch controller and perform the reset sequence
  ft6x36_power_up();

  driver->i2c_bus = i2c_bus_open(TOUCH_I2C_INSTANCE);
  if (driver->i2c_bus == NULL) {
    goto cleanup;
  }

  ft6x36_wake_up(driver->i2c_bus);

  // Configure the touch controller
  if (sectrue != ft6x36_configure(driver->i2c_bus)) {
    goto cleanup;
  }

  if (!syshandle_register(SYSHANDLE_TOUCH, &g_touch_handle_vmt, driver)) {
    goto cleanup;
  }

  driver->init_ticks = systick_ms();
  driver->read_ticks = driver->init_ticks;
  driver->initialized = sectrue;

  return sectrue;

cleanup:
  touch_deinit();
  return secfalse;
}

void touch_deinit(void) {
  touch_driver_t* driver = &g_touch_driver;
  syshandle_unregister(SYSHANDLE_TOUCH);
  i2c_bus_close(driver->i2c_bus);
  if (sectrue == driver->initialized) {
    ft6x36_power_down();
  }
  memset(driver, 0, sizeof(touch_driver_t));
}

void touch_power_set(bool on) {
  if (on) {
    ft6x36_power_up();
  } else {
    touch_deinit();
    ft6x36_power_down();
  }
}

secbool touch_ready(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue == driver->initialized && sectrue != driver->ready) {
    // FT6X36 does not report events for 300ms
    // after it is released from the reset state
    if ((int)(systick_ms() - driver->init_ticks) >= 310) {
      driver->ready = sectrue;
    }
  }

  return driver->ready;
}

secbool touch_set_sensitivity(uint8_t value) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue == driver->initialized) {
    ft6x36_wake_up(driver->i2c_bus);
    return ft6x36_write_reg(driver->i2c_bus, FT6X36_REG_TH_GROUP, value);
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
    systick_delay_ms(1);
  }

  ft6x36_wake_up(driver->i2c_bus);

  uint8_t fw_version = 0;

  if (sectrue !=
      ft6x36_read_regs(driver->i2c_bus, FT6X36_REG_FIRMID, &fw_version, 1)) {
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

  uint32_t time = systicks_ms() % 10000;

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

  systask_id_t task_id = systask_id(systask_active());

  printf("%04ld [task=%d, event=%c, x=%3d, y=%3d]\r\n", time, task_id,
         event_type, x, y);
}
#endif

// Reads touch registers and returns the last touch event
// (state of touch registers) the controller is reporting.
static uint32_t touch_get_state(touch_driver_t* driver) {
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

  // Test if the touch controller is polled too frequently
  // (less than 20ms since the last read)
  bool toofast = (int32_t)(ticks - driver->read_ticks) < 20 /* ms */;

  // Fast track: if there is no new event and the touch controller
  // is not touched, we do not need to read the registers
  bool pressed = (driver->state & TOUCH_START) || (driver->state & TOUCH_MOVE);

  if (!ft6x36_test_and_clear_interrupt() && (!pressed || toofast)) {
    return driver->state;
  }

  driver->read_ticks = ticks;

  // Read the set of registers containing touch event and coordinates
  if (sectrue != ft6x36_read_regs(driver->i2c_bus, 0x00, regs, sizeof(regs))) {
    // Failed to read the touch registers
    return driver->state;
  }

#ifdef TOUCH_TRACE_REGS
  trace_regs(regs);
#endif

  // Extract gesture ID (FT6X63_GESTURE_xxx)
  uint8_t gesture = regs[FT6X63_REG_GEST_ID];

  if (gesture != FT6X36_GESTURE_NONE) {
    // This is here for unknown historical reasons
    // It seems we can't get here with FT6X36
    return driver->state;
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

  uint32_t xy = touch_pack_xy(x, y);

  if ((nb_touches == 1) && (flags == FT6X63_EVENT_PRESS_DOWN)) {
    driver->state = TOUCH_START | xy;
  } else if ((nb_touches == 1) && (flags == FT6X63_EVENT_CONTACT)) {
    driver->state = TOUCH_MOVE | xy;
  } else if ((nb_touches == 0) && (flags == FT6X63_EVENT_LIFT_UP)) {
    driver->state = TOUCH_END | xy;
  }

  return driver->state;
}

uint32_t touch_get_event(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue != driver->initialized) {
    return 0;
  }

  touch_fsm_t* fsm = &driver->tls[systask_id(systask_active())];

  uint32_t touch_state = touch_get_state(driver);

  uint32_t event = touch_fsm_get_event(fsm, touch_state);

#ifdef TOUCH_TRACE_EVENT
  trace_event(event);
#endif

  return event;
}

static void on_task_created(void* context, systask_id_t task_id) {
  touch_driver_t* driver = (touch_driver_t*)context;
  touch_fsm_t* fsm = &driver->tls[task_id];
  touch_fsm_init(fsm);
}

static void on_event_poll(void* context, bool read_awaited,
                          bool write_awaited) {
  touch_driver_t* driver = (touch_driver_t*)context;
  UNUSED(write_awaited);

  if (read_awaited) {
    uint32_t touch_state = touch_get_state(driver);
    syshandle_signal_read_ready(SYSHANDLE_TOUCH, &touch_state);
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  touch_driver_t* driver = (touch_driver_t*)context;
  touch_fsm_t* fsm = &driver->tls[task_id];

  uint32_t touch_state = *(uint32_t*)param;

  return touch_fsm_event_ready(fsm, touch_state);
}

static const syshandle_vmt_t g_touch_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL_MODE
