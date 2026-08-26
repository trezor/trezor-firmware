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

#include <math.h>

#include <io/pmic.h>
#include <sys/i2c_bus.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systimer.h>

#ifdef USE_SUSPEND
#include <io/suspend.h>
#endif

#include "npm2100_defs.h"

#ifdef KERNEL_MODE

// Default timeout for all I2C operations
#define NPM2100_I2C_TIMEOUT 10

// Maximum number of consecutive I2C errors after we report a fatal error
#define NPM2100_I2C_ERROR_LIMIT 3

// Delay inserted between the ADC trigger and the readout [ms]
#define NPM2100_ADC_READOUT_DELAY 5

// Minimum temperature that counts as valid data
#define NPM2100_NTC_TEMP_VALID_MIN (-20.0f)

// Minimum temperature that counts as valid data
#define NPM2100_NTC_TEMP_VALID_MAX (105.0f)

// Minimum battery voltage that counts as valid data
#define NPM2100_BATT_VOLTAGE_VALID_MIN (0.5f)

// NPM2100 FSM states
typedef enum {
  NPM2100_STATE_IDLE = 0,
  NPM2100_STATE_CLEAR_EVENTS,
  NPM2100_STATE_ENTER_SHIPMODE,
  NPM2100_STATE_ADC_TRIGGER,
  NPM2100_STATE_ADC_WAIT,
  NPM2100_STATE_ADC_READOUT,
} npm2100_fsm_state_t;

typedef enum {
  NPM2100_NO_CHANNEL_SELECTED = 0,
  NPM2100_ADC_CHANNEL_VBAT,
  NPM2100_ADC_CHANNEL_VSYS,
  NPM2100_ADC_CHANNEL_DIETEMP,
} npm2100_adc_channel_id_t;

typedef struct {
  uint8_t adc_vbat_result;
  uint8_t adc_vsys_result;
  uint8_t adc_temp_result;
  uint8_t npm_status;
} npm2100_adc_regs_t;

typedef struct {
  // TODO: add more events if needed
} npm2100_event_regs_t;

// NPM2100 PMIC driver state
typedef struct {
  // Set if the PMIC driver is initialized
  bool initialized;

  // EXTI handle
  EXTI_HandleTypeDef exti_handle;

  // I2C bus where the PMIC is connected
  i2c_bus_t* i2c_bus;
  // Number of consecutive I2C errors
  int i2c_errors;
  // Storage for the pending I2C packet
  i2c_packet_t pending_i2c_packet;

  // Timer used for waiting for the ADC conversion
  systimer_t* timer;

  // Content of RESET register read during driver initialization
  uint8_t restart_cause;

  // Current state of the FSM
  npm2100_fsm_state_t state;

  // Set if the driver was requested to suspend background operations.
  // IF so, the driver waits until the last operation is finished,
  // then enters suspended mode.
  bool suspending;

  // Set if the driver's background operations are suspended.
  // In suspended mode, the driver does not start any new operations.
  bool suspended;

  // ADC register (global buffer used for ADC measurements)
  npm2100_adc_regs_t adc_regs;
  // Event registers (global buffer used for events readout)
  npm2100_event_regs_t event_regs;

  // Enter ship mode
  bool shipmode_requested;

  // Request flags for ADC measurements
  bool adc_trigger_requested;
  bool adc_readout_requested;
  npm2100_adc_channel_id_t adc_channel_id;

  // Request flag for clearing events and releasing INT line
  bool clear_events_requested;

  // Report callback used for asynchronous measurements
  pmic_report_callback_t report_callback;
  void* report_callback_context;

} npm2100_driver_t;

// PMIC driver instance
npm2100_driver_t g_npm2100_driver = {
    .initialized = false,
};

// forward declarations
static void npm2100_timer_callback(void* context);
static void npm2100_i2c_callback(void* context, i2c_packet_t* packet);
static void npm2100_fsm_continue(npm2100_driver_t* drv);

// Writes a value to the NPM2100 register
//
// This function is used only during driver initialization because
// it's synchronous and blocks the execution.
static bool npm2100_set_reg(i2c_bus_t* bus, uint8_t addr, uint8_t value) {
  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 3,
          .data = {addr, value},
      },
  };

  i2c_packet_t pkt;
  memset(&pkt, 0, sizeof(i2c_packet_t));
  pkt.address = NPM2100_I2C_ADDRESS;
  pkt.timeout = NPM2100_I2C_TIMEOUT;
  pkt.op_count = ARRAY_LENGTH(ops);
  pkt.ops = ops;

  if (I2C_STATUS_OK != i2c_bus_submit_and_wait(bus, &pkt)) {
    return false;
  }

  return true;
}

// Reads a value from the NPM2100 register
//
// This function is used only during driver initialization because
// it's synchronous and blocks the execution.
static bool npm2100_get_reg(i2c_bus_t* bus, uint8_t addr, uint8_t* data) {
  i2c_op_t ops[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 2,
          .data = {addr},
      },
      {
          .flags = I2C_FLAG_RX,
          .size = sizeof(*data),
          .ptr = data,
      },
  };

  i2c_packet_t pkt;
  memset(&pkt, 0, sizeof(i2c_packet_t));
  pkt.address = NPM2100_I2C_ADDRESS;
  pkt.timeout = NPM2100_I2C_TIMEOUT;
  pkt.op_count = ARRAY_LENGTH(ops);
  pkt.ops = ops;

  if (I2C_STATUS_OK != i2c_bus_submit_and_wait(bus, &pkt)) {
    return false;
  }

  return true;
}

// Initializes the NPM2100 driver to the default state
static bool npm2100_initialize(i2c_bus_t* bus) {
  // TODO: uncomment if needed
  // int8_t die_temp_stop = 110;    // °C
  // int8_t die_temp_resume = 100;  // °C

  struct {
    uint8_t addr;
    uint8_t value;
  } table[] = {
      // TODO: define VBAT thresholds?
      // VBATMINLHSEL 0x2E Enable register control for VBATMINL and VBATMINH
      // comparator thresholds
      // VBATMINL     0x2F Battery voltage threshold setting for VBATMINL
      // VBATMINH     0x30 Battery voltage threshold setting for VBATMINH
      // VOUTMIN      0x31 Output voltage threshold setting for VOUTMIN
      // VOUTWRN      0x32 Output voltage threshold setting for VOUTWRN

      // BOOST regulator
      {NPM2100_BOOST_VOUT, NPM2100_BOOST_VOUT_3V3},
      {NPM2100_BOOST_VOUTSEL, NPM2100_BOOST_VOUTSEL_REGISTER},
      {NPM2100_BOOST_IBATLIM, NPM2100_BOOST_IBATLIM_800MA},

      // ADC settings
      {NPM2100_ADC_CONFIG, NPM2100_ADC_CONFIG_AVG_16},
      // Die tempererature thresholds
      // - TODO: define warning threshold
      // GPIO
      // - TODO: if needed
      // TIMER
      // - TODO: probably not used (WATCHDOG TIMER?)
      // Ship mode and Reset button
      // - reset button must be disabled in BUTTON register before configuring
      // this register
      {NPM2100_RESET_BUTTON, NPM2100_RESET_BUTTON_LONGPRESS_DISABLE},
      {NPM2100_RESET_PIN, NPM2100_RESET_PIN_SELECT_SHPHLD},
      {NPM2100_RESET_BUTTON, NPM2100_RESET_BUTTON_LONGPRESS_ENABLE},
      // Clear all events
      {NPM2100_EVENTS_SYSTEM_CLR, 0xFF},
      {NPM2100_EVENTS_ADC_CLR, 0x0F},
      {NPM2100_EVENTS_GPIO_CLR, 0x3F},
      {NPM2100_EVENTS_BOOST_CLR, 0xFF},
      {NPM2100_EVENTS_LDOSW_CLR, 0x03},
      // Disable all interrupts
      {NPM2100_INTEN_SYSTEM_CLR, 0xFF},
      {NPM2100_INTEN_ADC_CLR, 0x0F},
      {NPM2100_INTEN_GPIO_CLR, 0x3F},
      {NPM2100_INTEN_BOOST_CLR, 0xFF},
      {NPM2100_INTEN_LDOSW_CLR, 0x03},
      // Enable interrupts we are interested in
      // TODO: enable interrupts we are interested in
      {NPM2100_INTEN_SYSTEM_SET, NPM2100_EVENT_SYSTEM_DIETWARN},
      {NPM2100_REQUESTSET,
       NPM2100_REQUEST_DIETEMP | NPM2100_REQUEST_DIETEMPENA},
  };

  for (int i = 0; i < sizeof(table) / sizeof(table[0]); i++) {
    if (!npm2100_set_reg(bus, table[i].addr, table[i].value)) {
      return false;
    }
  }

  return true;
}

bool pmic_init(void) {
  npm2100_driver_t* drv = &g_npm2100_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(npm2100_driver_t));

  drv->i2c_bus = i2c_bus_open(NPM2100_I2C_INSTANCE);
  if (drv->i2c_bus == NULL) {
    goto cleanup;
  }

  drv->timer = systimer_create(npm2100_timer_callback, drv);
  if (drv->timer == NULL) {
    goto cleanup;
  }

  // TODO: uncomment if connected to STM
  /*
  GPIO_InitTypeDef GPIO_InitStructure = {0};

  // INT pin, active low, external pull-up
    NPM2100_INT_PIN_CLK_ENA();
    GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStructure.Pin = NPM2100_INT_PIN;
    HAL_GPIO_Init(NPM2100_INT_PORT, &GPIO_InitStructure);

    // Setup interrupt line for the NPM2100
    EXTI_ConfigTypeDef EXTI_Config = {0};
    EXTI_Config.GPIOSel = NPM2100_EXTI_INTERRUPT_GPIOSEL;
    EXTI_Config.Line = NPM2100_EXTI_INTERRUPT_LINE;
    EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
    EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
    HAL_EXTI_SetConfigLine(&drv->exti_handle, &EXTI_Config);
  */

  if (!npm2100_get_reg(drv->i2c_bus, NPM2100_RESET_RESET,
                       &drv->restart_cause)) {
    goto cleanup;
  }

  if (!npm2100_initialize(drv->i2c_bus)) {
    goto cleanup;
  }

  // TODO: uncomment if connected to STM
  /*
  // Enable interrupt line
  NVIC_SetPriority(NPM2100_EXTI_INTERRUPT_NUM, IRQ_PRI_NORMAL);
  __HAL_GPIO_EXTI_CLEAR_FLAG(NPM2100_INT_PIN);
  NVIC_EnableIRQ(NPM2100_EXTI_INTERRUPT_NUM);
  */

  drv->initialized = true;

  return true;

cleanup:
  pmic_deinit();
  return false;
}

void pmic_deinit(void) {
  npm2100_driver_t* drv = &g_npm2100_driver;

  // TODO: uncomment if connected to STM
  /*
  NVIC_DisableIRQ(NPM2100_EXTI_INTERRUPT_NUM);
  HAL_EXTI_ClearConfigLine(&drv->exti_handle);
  */

  i2c_bus_close(drv->i2c_bus);
  systimer_delete(drv->timer);

  memset(drv, 0, sizeof(npm2100_driver_t));
}

bool pmic_suspend(void) {
  npm2100_driver_t* drv = &g_npm2100_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  drv->suspending = true;
  npm2100_fsm_continue(drv);
  irq_unlock(irq_key);

  return true;
}

bool pmic_resume(void) {
  npm2100_driver_t* drv = &g_npm2100_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  drv->suspending = false;
  drv->suspended = false;
  npm2100_fsm_continue(drv);
  irq_unlock(irq_key);

  return true;
}

bool pmic_is_suspended(void) {
  npm2100_driver_t* drv = &g_npm2100_driver;

  if (!drv->initialized) {
    return false;
  }

  bool is_suspended;

  irq_key_t irq_key = irq_lock();
  is_suspended = drv->suspended;
  irq_unlock(irq_key);

  return is_suspended;
}

bool pmic_enter_shipmode(void) {
  npm2100_driver_t* drv = &g_npm2100_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  drv->shipmode_requested = true;
  npm2100_fsm_continue(drv);
  irq_unlock(irq_key);

  return true;
}

uint8_t pmic_restart_cause(void) {
  npm2100_driver_t* drv = &g_npm2100_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->restart_cause;
}

bool pmic_measure(pmic_report_callback_t callback, void* context) {
  npm2100_driver_t* drv = &g_npm2100_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();

  if (drv->report_callback != NULL && callback != NULL) {
    // Cannot start another measurement while the previous one is in progress
    irq_unlock(irq_key);
    return false;
  }

  drv->report_callback = callback;
  drv->report_callback_context = context;

  if (drv->report_callback != NULL) {
    drv->adc_trigger_requested = true;
    npm2100_fsm_continue(drv);
  }

  irq_unlock(irq_key);

  return true;
}

// Synchronous measurement context structure
// (used internally within the `npm2100_measure_sync` function)
typedef struct {
  // Set when the measurement is done
  volatile bool done;
  // Report structure where the measurement is stored
  pmic_report_t* report;
} npm2100_sync_measure_t;

// Callback for the synchronous measurement
static void npm2100_sync_measure_callback(void* context,
                                          pmic_report_t* report) {
  npm2100_sync_measure_t* ctx = (npm2100_sync_measure_t*)context;
  *ctx->report = *report;
  ctx->done = true;
}

bool pmic_measure_sync(pmic_report_t* report) {
  npm2100_sync_measure_t measure = {
      .done = false,
      .report = report,
  };

  // Start asynchronous measurement
  if (!pmic_measure(npm2100_sync_measure_callback, &measure)) {
    return false;
  }

  // Wait for the measurement to finish
  while (!measure.done) {
    __WFI();
  }

  return true;
}

// Prepares PMIC report from the last readout of the ADC values
// stored in `drv->adc_regs`
//
// This function is called in the irq context.
static void npm2100_calculate_report(npm2100_driver_t* drv,
                                     pmic_report_t* report) {
  memset(report, 0, sizeof(pmic_report_t));

  npm2100_adc_regs_t* r = &drv->adc_regs;

  // Calculate the battery voltage (VBAT)
  report->vbat = NPM2100_ADC_VBAT_V(r->adc_vbat_result);
  report->battery_disconnected = false;

  // NTC is diconnected.
  report->ntc_disconnected = true;

  // Calculate the die temperature from the die ADC reading.
  report->die_temp = NPM2100_ADC_DIETEMP_C(r->adc_temp_result);

  // Calculate the system voltage (VSYS) from the ADC value.
  report->vsys = NPM2100_ADC_VOUT_V(r->adc_vsys_result);
}

// I2C operation for writing constant value to the npm2100 register
#define NPM_WRITE_CONST(reg, value)                           \
  {                                                           \
      .flags = I2C_FLAG_TX | I2C_FLAG_EMBED | I2C_FLAG_START, \
      .size = 2,                                              \
      .data = {(reg), (value)},                               \
  }

// I2C operations for the value of specified uint8_t field
// in `g_npm2100_driver` structure into npm2100 register
#define NPM_WRITE_FIELD(reg, field)                                  \
  {                                                                  \
      .flags = I2C_FLAG_TX | I2C_FLAG_EMBED | I2C_FLAG_START,        \
      .size = 1,                                                     \
      .data = {(reg)},                                               \
  },                                                                 \
  {                                                                  \
    .flags = I2C_FLAG_TX, .size = 1, .ptr = &g_npm2100_driver.field, \
  }

// I2C operations for reading npm2100 register into the specified
// field in `g_npm2100_driver` structure
#define NPM_READ_FIELD(reg, field)                                   \
  {                                                                  \
      .flags = I2C_FLAG_TX | I2C_FLAG_EMBED | I2C_FLAG_START,        \
      .size = 1,                                                     \
      .data = {(reg)},                                               \
  },                                                                 \
  {                                                                  \
    .flags = I2C_FLAG_RX, .size = 1, .ptr = &g_npm2100_driver.field, \
  }

static const i2c_op_t npm2100_ops_enter_shipmode[] = {
    NPM_WRITE_CONST(NPM2100_SHIP_TASKS_SHIP, NPM2100_SHIP_TASKS_SHIP_ENTER),
};

// I2C operations for triggering of the ADC measurements

// TODO: check if we can send request to measure multiple ADC channels at once
// how does this I2C driver works?
// does it send all the operations in one I2C transaction or does it send them
// one by one with wait for an IRQ?
static const i2c_op_t npm2100_ops_vbat_adc_trigger[] = {
    NPM_WRITE_CONST(NPM2100_ADC_CONFIG, NPM2100_ADC_CONFIG_MODE_INSVBAT |
                                            NPM2100_ADC_CONFIG_AVG_16),
    NPM_WRITE_CONST(NPM2100_ADC_TASKS_ADC, NPM2100_ADC_TASKS_ADC_CONV),
};

static const i2c_op_t npm2100_ops_vsys_adc_trigger[] = {
    NPM_WRITE_CONST(NPM2100_ADC_CONFIG,
                    NPM2100_ADC_CONFIG_MODE_VOUT | NPM2100_ADC_CONFIG_AVG_16),
    NPM_WRITE_CONST(NPM2100_ADC_TASKS_ADC, NPM2100_ADC_TASKS_ADC_CONV),
};

static const i2c_op_t npm2100_ops_temp_adc_trigger[] = {
    NPM_WRITE_CONST(NPM2100_ADC_CONFIG, NPM2100_ADC_CONFIG_MODE_DIETEMP |
                                            NPM2100_ADC_CONFIG_AVG_16),
    NPM_WRITE_CONST(NPM2100_ADC_TASKS_ADC, NPM2100_ADC_TASKS_ADC_CONV),
};

// I2C operations for readout of the ADC values into the
// `g_npm2100_driver.adc_regs` structure
static const i2c_op_t npm2100_ops_vbat_adc_readout[] = {
    NPM_READ_FIELD(NPM2100_ADC_AVERAGE, adc_regs.adc_vbat_result),
};

static const i2c_op_t npm2100_ops_vsys_adc_readout[] = {
    NPM_READ_FIELD(NPM2100_ADC_AVERAGE, adc_regs.adc_vsys_result),
};

static const i2c_op_t npm2100_ops_temp_adc_readout[] = {
    NPM_READ_FIELD(NPM2100_ADC_AVERAGE, adc_regs.adc_temp_result),
};

// I2C operation that clears event flags and releases INT line
static const i2c_op_t npm2100_ops_clear_events[] = {
    NPM_WRITE_CONST(NPM2100_EVENTS_SYSTEM_CLR, 0xFF),
    NPM_WRITE_CONST(NPM2100_EVENTS_ADC_CLR, 0x0F),
    NPM_WRITE_CONST(NPM2100_EVENTS_GPIO_CLR, 0x3F),
    NPM_WRITE_CONST(NPM2100_EVENTS_BOOST_CLR, 0xFF),
    NPM_WRITE_CONST(NPM2100_EVENTS_LDOSW_CLR, 0x03),
};

#define npm2100_i2c_submit(drv, ops) \
  _npm2100_i2c_submit(drv, ops, ARRAY_LENGTH(ops))

// helper function for submitting I2C operations
static void _npm2100_i2c_submit(npm2100_driver_t* drv, const i2c_op_t* ops,
                                size_t op_count) {
  i2c_packet_t* pkt = &drv->pending_i2c_packet;

  memset(pkt, 0, sizeof(i2c_packet_t));
  pkt->address = NPM2100_I2C_ADDRESS;
  pkt->context = drv;
  pkt->callback = npm2100_i2c_callback;
  pkt->timeout = NPM2100_I2C_TIMEOUT;
  pkt->ops = (i2c_op_t*)ops;
  pkt->op_count = op_count;

  i2c_status_t status = i2c_bus_submit(drv->i2c_bus, pkt);

  if (status != I2C_STATUS_OK) {
    // This should never happen
    error_shutdown("npm2100 I2C submit error");
  }
}

// npm2100 driver timer callback invoked when `drv->timer` expires.
//
// This function is called in the irq context.
static void npm2100_timer_callback(void* context) {
  npm2100_driver_t* drv = (npm2100_driver_t*)context;

  switch (drv->state) {
    case NPM2100_STATE_ADC_WAIT:
      // The ADC conversion is done, read the values
      drv->adc_readout_requested = true;
      drv->state = NPM2100_STATE_IDLE;
      break;

    default:
      // we should never get here
      drv->state = NPM2100_STATE_IDLE;
      break;
  }

  npm2100_fsm_continue(drv);
}

// npm2100 driver I2C completion callback invoked when
// `drv->pending_i2c_packet` is completed
//
// This function is called in the irq context.
static void npm2100_i2c_callback(void* context, i2c_packet_t* packet) {
  npm2100_driver_t* drv = (npm2100_driver_t*)context;

  if (packet->status != I2C_STATUS_OK) {
    drv->i2c_errors++;

    if (drv->i2c_errors > NPM2100_I2C_ERROR_LIMIT) {
      error_shutdown("npm2100 I2C error");
    }

    drv->state = NPM2100_STATE_IDLE;

    // I2C operation will be retried until it succeeds or
    // the error limit is reached
    npm2100_fsm_continue(drv);
    return;
  }

  // If the I2C operation was successful, reset the error counter
  drv->i2c_errors = 0;

  switch (drv->state) {
    case NPM2100_STATE_CLEAR_EVENTS:
      drv->clear_events_requested = false;
      drv->state = NPM2100_STATE_IDLE;
#ifdef USE_SUSPEND
      wakeup_flags_set(WAKEUP_FLAG_POWER);
#endif
      break;

    case NPM2100_STATE_ENTER_SHIPMODE:
      drv->state = NPM2100_STATE_IDLE;
      break;

    case NPM2100_STATE_ADC_TRIGGER:
      drv->adc_trigger_requested = false;

      systimer_set(drv->timer, NPM2100_ADC_READOUT_DELAY);
      drv->state = NPM2100_STATE_ADC_WAIT;
      break;

    case NPM2100_STATE_ADC_READOUT:
      drv->adc_readout_requested = false;

      if (drv->adc_channel_id == NPM2100_NO_CHANNEL_SELECTED) {
        // All ADC channels have been read out, prepare the report
        pmic_report_t report;
        npm2100_calculate_report(drv, &report);

        // Invoke report callback
        pmic_report_callback_t report_callback = drv->report_callback;
        void* report_callback_context = drv->report_callback_context;

        // Clear the report callback before invoking it
        // to allow the new measurement to be scheduled in the callback
        drv->report_callback = NULL;
        drv->report_callback_context = NULL;

        if (report_callback != NULL) {
          report_callback(report_callback_context, &report);
        }
      } else {
        // Trigger the next ADC channel conversion
        drv->adc_trigger_requested = true;
      }

      drv->state = NPM2100_STATE_IDLE;
      break;

    default:
      // we should never get here
      drv->state = NPM2100_STATE_IDLE;
      break;
  }

  npm2100_fsm_continue(drv);
}

// void NPM2100_EXTI_INTERRUPT_HANDLER(void) {
//   IRQ_LOG_ENTER();
//   mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
//   npm2100_driver_t* drv = &g_npm2100_driver;

//   // Clear the EXTI line pending bit
//   __HAL_GPIO_EXTI_CLEAR_FLAG(NPM2100_INT_PIN);

//   if (!drv->initialized) {
//     mpu_restore(mpu_mode);
//     IRQ_LOG_EXIT();
//     return;
//   }

//   drv->clear_events_requested = true;
//   npm2100_fsm_continue(drv);
//   mpu_restore(mpu_mode);
//   IRQ_LOG_EXIT();
// }

// npm2100 driver FSM continuation function that decides what to do next
//
// This function is called in the irq context or when interrupts are disabled.
static void npm2100_fsm_continue(npm2100_driver_t* drv) {
  if (drv->state != NPM2100_STATE_IDLE || drv->suspended) {
    return;
  }

  // The order of the following conditions defines the priority

  if (drv->clear_events_requested) {
    npm2100_i2c_submit(drv, npm2100_ops_clear_events);

    drv->state = NPM2100_STATE_CLEAR_EVENTS;
  } else if (drv->adc_readout_requested) {
    // Read ADC values of active channel
    switch (drv->adc_channel_id) {
      case NPM2100_ADC_CHANNEL_VBAT:
        npm2100_i2c_submit(drv, npm2100_ops_vbat_adc_readout);
        break;
      case NPM2100_ADC_CHANNEL_VSYS:
        npm2100_i2c_submit(drv, npm2100_ops_vsys_adc_readout);
        break;
      case NPM2100_ADC_CHANNEL_DIETEMP:
        npm2100_i2c_submit(drv, npm2100_ops_temp_adc_readout);
        drv->adc_channel_id = NPM2100_NO_CHANNEL_SELECTED;
        break;
      default:
        break;
    }

    drv->state = NPM2100_STATE_ADC_READOUT;
  } else if (drv->adc_trigger_requested) {
    // Trigger ADC VBAT conversion
    switch (drv->adc_channel_id) {
      case NPM2100_NO_CHANNEL_SELECTED:
      case NPM2100_ADC_CHANNEL_DIETEMP:
      default:
        drv->adc_channel_id = NPM2100_ADC_CHANNEL_VBAT;
        npm2100_i2c_submit(drv, npm2100_ops_vbat_adc_trigger);
        break;
      case NPM2100_ADC_CHANNEL_VBAT:
        drv->adc_channel_id = NPM2100_ADC_CHANNEL_VSYS;
        npm2100_i2c_submit(drv, npm2100_ops_vsys_adc_trigger);
        break;
      case NPM2100_ADC_CHANNEL_VSYS:
        drv->adc_channel_id = NPM2100_ADC_CHANNEL_DIETEMP;
        npm2100_i2c_submit(drv, npm2100_ops_temp_adc_trigger);
        break;
    }

    drv->state = NPM2100_STATE_ADC_TRIGGER;
  } else if (drv->shipmode_requested) {
    npm2100_i2c_submit(drv, npm2100_ops_enter_shipmode);
    drv->shipmode_requested = false;
    drv->state = NPM2100_STATE_ENTER_SHIPMODE;
  }

  // After processing all requests, check if we need to
  // suspend the driver
  if (drv->state == NPM2100_STATE_IDLE) {
    // No more requests to process
    if (drv->suspending) {
      drv->suspending = false;
      drv->suspended = true;
    }
  }
}

#endif  // KERNEL_MODE
