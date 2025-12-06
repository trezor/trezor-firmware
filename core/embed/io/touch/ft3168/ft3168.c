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
#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systick.h>
#include "ft3168.h"

#ifdef TOUCH_PANEL_LX250A2410A
#include "panels/lx250a2410a.h"
#endif

#include "../touch_poll.h"

#ifdef USE_SUSPEND
#include <sys/suspend.h>
#endif

// #define TOUCH_TRACE_REGS

#define FT3168_P_MONITOR_AUTO_ENTRY_DEFAULT (FT3168_P_MONITOR_AUTO_ENTRY_ON)
#define FT3168_TIMEENTERMONITOR_DEFAULT 12  // In seconds

typedef struct {
  // Set if the driver is initialized
  secbool initialized;
  // I2c bus where the touch controller is connected
  i2c_bus_t* i2c_bus;
  // Set if the driver is ready to report touches.
  // FT3168 needs about 300ms after power-up to stabilize.
  secbool ready;
  // Captured tick counter when `touch_init()` was called
  uint32_t init_ticks;
  // Time (in ticks) when the touch registers were read last time
  uint32_t read_ticks;
  // Last reported touch state
  uint32_t state;

#ifdef USE_SUSPEND
  // Set if the driver is currently suspended
  secbool suspended;
  // EXTI handle for touch interrupt line
  EXTI_HandleTypeDef exti;
#endif  // USE_SUSPEND

} touch_driver_t;

// Touch driver instance
static touch_driver_t g_touch_driver = {
    .initialized = secfalse,
};

// Reads a subsequent registers from the FT3168.
//
// Returns: `sectrue` if the register was read
// successfully, `secfalse` otherwise.
//
// If the I2C bus is busy, the function will cycle the
// bus and retry the operation.
static secbool ft3168_read_regs(i2c_bus_t* bus, uint8_t reg, uint8_t* value,
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
      .address = FT3168_I2C_ADDR,
      .op_count = ARRAY_LENGTH(ops),
      .ops = ops,
  };

  if (I2C_STATUS_OK != i2c_bus_submit_and_wait(bus, &pkt)) {
    return secfalse;
  }

  return sectrue;
}

// Writes a register to the FT3168.
//
// Returns: `sectrue` if the register was written
// successfully, `secfalse` otherwise.
//
// If the I2C bus is busy, the function will cycle the
// bus and retry the operation.
static secbool ft3168_write_reg(i2c_bus_t* bus, uint8_t reg, uint8_t value) {
  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 2,
          .data = {reg, value},
      },
  };

  i2c_packet_t pkt = {
      .address = FT3168_I2C_ADDR,
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
// after a period of inactivity. When in this mode, it fails to respond to
// the first I2C command — writes are not ACKed, and reads return 0x00
// or garbage data. To avoid this issue, we need to wake up the controller
// before sending any commands to it.
static void ft3168_wake_up(i2c_bus_t* bus) {
  uint8_t temp;
  // Wake up the touch controller by reading one of its registers
  // (the specific register does not matter)
  ft3168_read_regs(bus, 0x00, &temp, 1);
  // Wait for the touch controller to wake up
  // (not sure if this is necessary, but it's safer to include it)
  systick_delay_ms(1);
}

// Sets the power mode of the touch controller.
//
// `mode` can be one of the following values:
//   0x00 - P_ACTIVE_MODE
//   0x01 - P_MONITOR_MODE
//   0x03 - P_HIBERNATE_MODE
// Returns `sectrue` if the config sequence succeeds or `secfalse` if it fails.
static secbool ft3168_power_mode_set(i2c_bus_t* bus, power_mode_t mode) {
  secbool ret = sectrue;

  // Ensure the touch controller is awake (just a precaution).
  // DEBUGGING WARNING: after switching the controller to MONITOR mode,
  // the first I2C command may fail - BE CAREFUL WHEN SETTING BP's.
  ft3168_wake_up(bus);

  if (P_ACTIVE_MODE == mode) {
    // Configure the defaults of automatic transition to monitor mode
    ret &= ft3168_write_reg(bus, FT3168_REG_G_TIMEENTERMONITOR,
                            FT3168_TIMEENTERMONITOR_DEFAULT);
    ret &= ft3168_write_reg(bus, FT3168_REG_G_CTRL,
                            FT3168_P_MONITOR_AUTO_ENTRY_DEFAULT);
  } else if (P_MONITOR_MODE == mode) {
    // Enable the automatic transition to monitor mode after 1s (in case
    // the touch controller wakes up when it shouldn't)
    ret &= ft3168_write_reg(bus, FT3168_REG_G_TIMEENTERMONITOR, 1);
    ret &= ft3168_write_reg(bus, FT3168_REG_G_CTRL,
                            FT3168_P_MONITOR_AUTO_ENTRY_ON);
  }

  // Set the touch controller to the specified power mode
  ret &= ft3168_write_reg(bus, FT3168_REG_G_PMODE, (uint8_t)mode);

  return ret;
}

// Powers down the touch controller and puts all
// the pins in the proper state to save power.
static void ft3168_power_down(void) {
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
// `ft3168_power_down()` must be called before calling this first time function
// to properly initialize the GPIO pins.
static void ft3168_power_up(void) {
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
static bool ft3168_test_and_clear_interrupt(void) {
  uint32_t event = __HAL_GPIO_EXTI_GET_FLAG(TOUCH_INT_PIN);
  if (event != 0) {
    __HAL_GPIO_EXTI_CLEAR_FLAG(TOUCH_INT_PIN);
  }

  return event != 0;
}

// Configures the touch controller to the functional state.
static secbool ft3168_configure(i2c_bus_t* i2c_bus) {
  const static uint8_t config[] = {
      // Set touch controller to the interrupt trigger mode.
      // Basically, CTPM generates a pulse when new data is available.
      FT3168_REG_G_MODE,
      FT3168_INT_TRIG_MODE,
      FT3168_REG_TH_GROUP,
      TOUCH_SENSITIVITY,
      FT3168_REG_G_CTRL,
      FT3168_P_MONITOR_AUTO_ENTRY_DEFAULT,
      FT3168_REG_G_TIMEENTERMONITOR,
      FT3168_TIMEENTERMONITOR_DEFAULT};

  _Static_assert(sizeof(config) % 2 == 0);

  for (int i = 0; i < sizeof(config); i += 2) {
    uint8_t reg = config[i];
    uint8_t value = config[i + 1];

    if (sectrue != ft3168_write_reg(i2c_bus, reg, value)) {
      return secfalse;
    }
  }

  return sectrue;
}

static void ft3168_panel_correction(uint16_t x, uint16_t y, uint16_t* x_new,
                                    uint16_t* y_new) {
#ifdef TOUCH_PANEL_LX250A2410A
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
  ft3168_power_down();

  // Power up the touch controller and perform the reset sequence
  ft3168_power_up();

  driver->i2c_bus = i2c_bus_open(TOUCH_I2C_INSTANCE);
  if (driver->i2c_bus == NULL) {
    goto cleanup;
  }

  // Ensure the touch controller is awake (just a precaution).
  ft3168_wake_up(driver->i2c_bus);

  // Configure the touch controller
  if (sectrue != ft3168_configure(driver->i2c_bus)) {
    goto cleanup;
  }

  if (!touch_poll_init()) {
    goto cleanup;
  }

#ifdef USE_SUSPEND
  // Setup interrupt handler (enabled in touch_suspend())
  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = TOUCH_EXTI_INTERRUPT_GPIOSEL;
  EXTI_Config.Line = TOUCH_EXTI_INTERRUPT_LINE;
  EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
  EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
  HAL_EXTI_SetConfigLine(&driver->exti, &EXTI_Config);
  NVIC_SetPriority(TOUCH_EXTI_INTERRUPT_NUM, IRQ_PRI_NORMAL);
#endif  // USE_SUSPEND

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

#ifdef USE_SUSPEND
  // Disable the interrupt
  NVIC_DisableIRQ(TOUCH_EXTI_INTERRUPT_NUM);
  HAL_EXTI_ClearConfigLine(&driver->exti);
#endif  // USE_SUSPEND

  touch_poll_deinit();
  i2c_bus_close(driver->i2c_bus);
  if (sectrue == driver->initialized) {
    ft3168_power_down();
  }
  memset(driver, 0, sizeof(touch_driver_t));
}

#ifdef USE_SUSPEND
secbool touch_suspend(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (secfalse == driver->initialized) {
    // The driver isn't initialized, wrong control flow applied, return error
    return secfalse;
  }

  if (secfalse != driver->suspended) {
    // The driver is already suspended
    return sectrue;
  }

  touch_poll_deinit();

  // Enable the interrupt to wake up on touch
  __HAL_GPIO_EXTI_CLEAR_FLAG(TOUCH_EXTI_INTERRUPT_PIN);
  NVIC_ClearPendingIRQ(TOUCH_EXTI_INTERRUPT_NUM);
  NVIC_EnableIRQ(TOUCH_EXTI_INTERRUPT_NUM);

  // Set the touch driver to monitor mode
  if (secfalse == ft3168_power_mode_set(driver->i2c_bus, P_MONITOR_MODE)) {
    goto cleanup;
  }

  driver->suspended = sectrue;

  return sectrue;

cleanup:
  touch_deinit();
  return secfalse;
}

secbool touch_resume(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (secfalse == driver->initialized) {
    // The driver isn't initialized, wrong control flow applied, return error
    return secfalse;
  }

  if (secfalse == driver->suspended) {
    // The driver isn't suspended, nothing to resume
    return sectrue;
  }

  // Disable the interrupt for normal operation
  NVIC_DisableIRQ(TOUCH_EXTI_INTERRUPT_NUM);

  // Set the touch driver to active mode
  if (secfalse == ft3168_power_mode_set(driver->i2c_bus, P_ACTIVE_MODE)) {
    goto cleanup;
  }

  if (!touch_poll_init()) {
    goto cleanup;
  }

  driver->suspended = secfalse;

  return sectrue;

cleanup:
  touch_deinit();
  return secfalse;
}
#endif  // USE_SUSPEND

void touch_power_set(bool on) {
  if (on) {
    ft3168_power_up();
  } else {
    touch_deinit();
    ft3168_power_down();
  }
}

secbool touch_ready(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue == driver->initialized && sectrue != driver->ready) {
    // FT3168 does not report events for 300ms
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
    // Ensure the touch controller is awake (just a precaution).
    ft3168_wake_up(driver->i2c_bus);
    return ft3168_write_reg(driver->i2c_bus, FT3168_REG_TH_GROUP, value);
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

  // Ensure the touch controller is awake (just a precaution).
  ft3168_wake_up(driver->i2c_bus);

  uint8_t fw_version = 0;

  if (sectrue !=
      ft3168_read_regs(driver->i2c_bus, FT3168_REG_FIRMID, &fw_version, 1)) {
    ft3168_power_down();
    return secfalse;
  }

  return fw_version;
}

secbool touch_activity(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue == driver->initialized) {
    if (ft3168_test_and_clear_interrupt()) {
      return sectrue;
    }
  }

  return secfalse;
}

#ifdef TOUCH_TRACE_REGS
void trace_regs(uint8_t* regs) {
  // Extract gesture ID (FT3168_GESTURE_xxx)
  uint8_t gesture = regs[FT3168_REG_GEST_ID];

  // Extract number of touches (0, 1, 2) or 0x0F before
  // the first touch (tested with FT6206)
  uint8_t nb_touches = regs[FT3168_REG_TD_STATUS] & 0x0F;

  // Extract event flags (one of press down, contact, lift up)
  uint8_t flags = regs[FT3168_REG_P1_XH] & FT3168_EVENT_MASK;

  // Extract touch coordinates
  uint16_t x = ((regs[FT3168_REG_P1_XH] & 0x0F) << 8) | regs[FT3168_REG_P1_XL];
  uint16_t y = ((regs[FT3168_REG_P1_YH] & 0x0F) << 8) | regs[FT3168_REG_P1_YL];

  char event;

  if (flags == FT3168_EVENT_PRESS_DOWN) {
    event = 'D';
  } else if (flags == FT3168_EVENT_CONTACT) {
    event = 'C';
  } else if (flags == FT3168_EVENT_LIFT_UP) {
    event = 'U';
  } else {
    event = '-';
  }

  uint32_t time = systicks_ms() % 10000;

  printf("%04ld [gesture=%02X, nb_touches=%d, flags=%c, x=%3d, y=%3d]\r\n",
         time, gesture, nb_touches, event, x, y);
}
#endif

// Reads touch registers and returns the last touch event
// (state of touch registers) the controller is reporting.
uint32_t touch_get_state(void) {
  touch_driver_t* driver = &g_touch_driver;

  if (sectrue != driver->initialized) {
    return 0;
  }

  // Content of registers 0x00 - 0x06 read from the touch controller
  uint8_t regs[7];

  // Ensure the registers are within the bounds
  _Static_assert(sizeof(regs) > FT3168_REG_GEST_ID);
  _Static_assert(sizeof(regs) > FT3168_REG_TD_STATUS);
  _Static_assert(sizeof(regs) > FT3168_REG_P1_XH);
  _Static_assert(sizeof(regs) > FT3168_REG_P1_XL);
  _Static_assert(sizeof(regs) > FT3168_REG_P1_YH);
  _Static_assert(sizeof(regs) > FT3168_REG_P1_YL);

  uint32_t ticks = hal_ticks_ms();

  // Test if the touch controller is polled too frequently
  // (less than 20ms since the last read)
  bool toofast = (int32_t)(ticks - driver->read_ticks) < 20 /* ms */;

  // Fast track: if there is no new event and the touch controller
  // is not touched, we do not need to read the registers
  bool pressed = (driver->state & TOUCH_START) || (driver->state & TOUCH_MOVE);

  if (!ft3168_test_and_clear_interrupt() && (!pressed || toofast)) {
    return driver->state;
  }

  driver->read_ticks = ticks;

  // Read the set of registers containing touch event and coordinates
  if (sectrue != ft3168_read_regs(driver->i2c_bus, 0x00, regs, sizeof(regs))) {
    // Failed to read the touch registers
    return driver->state;
  }

#ifdef TOUCH_TRACE_REGS
  trace_regs(regs);
#endif

  // Extract gesture ID (FT3168_GESTURE_xxx)
  uint8_t gesture = regs[FT3168_REG_GEST_ID];

  if (gesture != FT3168_GESTURE_NONE) {
    // This is here for unknown historical reasons
    // It seems we can't get here with FT3168
    return driver->state;
  }

  // Extract number of touches (0, 1, 2) or 0x0F before
  // the first touch (tested with FT6206)
  uint8_t nb_touches = regs[FT3168_REG_TD_STATUS] & 0x0F;

  // Extract event flags (one of press down, contact, lift up)
  uint8_t flags = regs[FT3168_REG_P1_XH] & FT3168_EVENT_MASK;

  // Extract touch coordinates
  uint16_t x_raw =
      ((regs[FT3168_REG_P1_XH] & 0x0F) << 8) | regs[FT3168_REG_P1_XL];
  uint16_t y_raw =
      ((regs[FT3168_REG_P1_YH] & 0x0F) << 8) | regs[FT3168_REG_P1_YL];

  uint16_t x, y;

  ft3168_panel_correction(x_raw, y_raw, &x, &y);

  uint32_t xy = touch_pack_xy(x, y);

  if ((nb_touches == 1) && (flags == FT3168_EVENT_PRESS_DOWN)) {
    driver->state = TOUCH_START | xy;
  } else if ((nb_touches == 1) && (flags == FT3168_EVENT_CONTACT)) {
    driver->state = TOUCH_MOVE | xy;
  } else if ((nb_touches == 0) && (flags == FT3168_EVENT_LIFT_UP)) {
    driver->state = TOUCH_END | xy;
  }

  return driver->state;
}

#ifdef USE_SUSPEND
void TOUCH_EXTI_INTERRUPT_HANDLER(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  touch_driver_t* driver = &g_touch_driver;

  // Clear the EXTI line pending bit
  __HAL_GPIO_EXTI_CLEAR_FLAG(TOUCH_EXTI_INTERRUPT_PIN);

  if (secfalse != driver->initialized && secfalse != driver->suspended) {
    // Inform the powerctl module about touch press
    wakeup_flags_set(WAKEUP_FLAG_TOUCH);
  }

  mpu_restore(mpu_mode);
  IRQ_LOG_EXIT();
}
#endif  // USE_SUSPEND

#endif  // KERNEL_MODE
