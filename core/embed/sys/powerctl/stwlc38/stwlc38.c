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

#include <io/i2c_bus.h>
#include <sys/irq.h>
#include <sys/systick.h>
#include <sys/systimer.h>

#include "stwlc38.h"
#include "stwlc38_defs.h"
#include "stwlc38_internal.h"

#ifdef KERNEL_MODE

// STWLC38 driver instance
stwlc38_driver_t g_stwlc38_driver = {
    .initialized = false,
};

// I2C operation for writing 8-bit constant value to the STWLC38 register
#define STWLC_WRITE_CONST8(reg, value)                                 \
  {                                                                    \
    .flags = I2C_FLAG_TX | I2C_FLAG_EMBED | I2C_FLAG_START, .size = 3, \
    .data = {(reg) >> 8, (reg) & 0xFF, (value)},                       \
  }

// I2C operations for reading 16-bit STWLC38 register into the
// specified field in `g_stwlc38_driver` structure
#define STWLC_READ_FIELD16(reg, field)                               \
  {                                                                  \
      .flags = I2C_FLAG_TX | I2C_FLAG_EMBED | I2C_FLAG_START,        \
      .size = 2,                                                     \
      .data = {(reg) >> 8, (reg) & 0xFF},                            \
  },                                                                 \
  {                                                                  \
    .flags = I2C_FLAG_RX, .size = 2, .ptr = &g_stwlc38_driver.field, \
  }

// I2C operations for reading 8-bit STWLC38 register into the
// specified field in `g_stwlc38_driver` structure
#define STWLC_READ_FIELD8(reg, field)                                \
  {                                                                  \
      .flags = I2C_FLAG_TX | I2C_FLAG_EMBED | I2C_FLAG_START,        \
      .size = 2,                                                     \
      .data = {(reg) >> 8, (reg) & 0xFF},                            \
  },                                                                 \
  {                                                                  \
    .flags = I2C_FLAG_RX, .size = 1, .ptr = &g_stwlc38_driver.field, \
  }

// forward declarations
static void stwlc38_timer_callback(void *context);
static void stwlc38_i2c_callback(void *context, i2c_packet_t *packet);
static void stwlc38_fsm_continue(stwlc38_driver_t *drv);

void stwlc38_deinit(void) {
  stwlc38_driver_t *drv = &g_stwlc38_driver;

  i2c_bus_close(drv->i2c_bus);
  systimer_delete(drv->timer);
  memset(drv, 0, sizeof(stwlc38_driver_t));
}

bool stwlc38_init(void) {
  stwlc38_driver_t *drv = &g_stwlc38_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(stwlc38_driver_t));

  drv->state = STWLC38_STATE_POWER_DOWN;

  // Main LDO output is enabled by default
  drv->vout_enabled = true;
  drv->vout_enabled_requested = true;

  drv->i2c_bus = i2c_bus_open(STWLC38_I2C_INSTANCE);
  if (drv->i2c_bus == NULL) {
    goto cleanup;
  }

  drv->timer = systimer_create(stwlc38_timer_callback, drv);
  if (drv->timer == NULL) {
    goto cleanup;
  }

  STWLC38_INT_PIN_CLK_ENA();
  STWLC38_ENB_PIN_CLK_ENA();

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  // INT pin, active low, external pull-up
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLUP;  // NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = STWLC38_INT_PIN;
  HAL_GPIO_Init(STWLC38_INT_PORT, &GPIO_InitStructure);

  // ENB pin, active low, external pull-down
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = STWLC38_ENB_PIN;
  HAL_GPIO_WritePin(STWLC37_ENB_PORT, STWLC38_ENB_PIN, GPIO_PIN_RESET);
  HAL_GPIO_Init(STWLC37_ENB_PORT, &GPIO_InitStructure);

  // Setup interrupt line for the STWLC38
  EXTI_HandleTypeDef EXTI_Handle = {0};
  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = STWLC38_EXTI_INTERRUPT_GPIOSEL;
  EXTI_Config.Line = STWLC38_EXTI_INTERRUPT_LINE;
  EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
  EXTI_Config.Trigger = EXTI_TRIGGER_FALLING;
  HAL_EXTI_SetConfigLine(&EXTI_Handle, &EXTI_Config);
  NVIC_SetPriority(STWLC38_EXTI_INTERRUPT_NUM, IRQ_PRI_NORMAL);
  __HAL_GPIO_EXTI_CLEAR_FLAG(STWLC38_INT_PIN);
  NVIC_EnableIRQ(STWLC38_EXTI_INTERRUPT_NUM);

  drv->initialized = true;

  // Try to readout stwlc38 report, it may be already powered up
  irq_key_t irq_key = irq_lock();
  drv->report_readout_requested = true;
  stwlc38_fsm_continue(drv);
  irq_unlock(irq_key);

  return true;

cleanup:
  stwlc38_deinit();
  return false;
}

bool stwlc38_enable(bool enable) {
  stwlc38_driver_t *drv = &g_stwlc38_driver;

  if (!drv->initialized) {
    return false;
  }

  if (enable) {
    HAL_GPIO_WritePin(STWLC37_ENB_PORT, STWLC38_ENB_PIN, GPIO_PIN_RESET);
  } else {
    HAL_GPIO_WritePin(STWLC37_ENB_PORT, STWLC38_ENB_PIN, GPIO_PIN_SET);
  }

  return true;
}

bool stwlc38_enable_vout(bool enable) {
  stwlc38_driver_t *drv = &g_stwlc38_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();

  if (drv->vout_enabled_requested != enable) {
    drv->vout_enabled_requested = enable;
    stwlc38_fsm_continue(drv);
  }

  irq_unlock(irq_key);

  return true;
}

// I2C operations for readout of the current state into the
// `g_stwlc38.state` structure
static const i2c_op_t stwlc38_ops_report_readout[] = {
    STWLC_READ_FIELD16(STWLC38_REG_VRECT, report_regs.vrect),
    STWLC_READ_FIELD16(STWLC38_REG_VOUT, report_regs.vout),
    STWLC_READ_FIELD16(STWLC38_REG_ICUR, report_regs.icur),
    STWLC_READ_FIELD16(STWLC38_REG_TMEAS, report_regs.tmeas),
    STWLC_READ_FIELD16(STWLC38_REG_OPFREQ, report_regs.opfreq),
    STWLC_READ_FIELD16(STWLC38_REG_NTC, report_regs.ntc),
    STWLC_READ_FIELD8(STWLC38_REG_RXINT_STATUS0, report_regs.status0),
};

// I2C operations for enabling of the main LDO
static const i2c_op_t stwlc38_ops_vout_enable[] = {
    STWLC_WRITE_CONST8(STWLC38_RX_COMMAND, 0x01),  // RX VOUT ON
};

// I2C operations for disabling of the main LDO
static const i2c_op_t stwlc38_ops_vout_disable[] = {
    STWLC_WRITE_CONST8(STWLC38_RX_COMMAND, 0x02),  // RX VOUT OFF
};

#define stwlc38_i2c_submit(drv, ops) \
  _stwlc38_i2c_submit(drv, ops, ARRAY_LENGTH(ops))

// helper function for submitting I2C operations
static void _stwlc38_i2c_submit(stwlc38_driver_t *drv, const i2c_op_t *ops,
                                size_t op_count) {
  i2c_packet_t *pkt = &drv->pending_i2c_packet;

  memset(pkt, 0, sizeof(i2c_packet_t));
  pkt->address = STWLC38_I2C_ADDRESS;
  pkt->context = drv;
  pkt->callback = stwlc38_i2c_callback;
  pkt->timeout = 0;
  pkt->ops = (i2c_op_t *)ops;
  pkt->op_count = op_count;

  i2c_status_t status = i2c_bus_submit(drv->i2c_bus, pkt);
  if (status != I2C_STATUS_OK) {
    // This should never happen
    error_shutdown("STWLC32 I2C submit error");
  }
}

bool stwlc38_get_report(stwlc38_report_t *report) {
  stwlc38_driver_t *drv = &g_stwlc38_driver;

  if (!drv->initialized) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  *report = drv->report;
  irq_unlock(irq_key);

  return true;
}

static void stwlc38_timer_callback(void *context) {
  stwlc38_driver_t *drv = (stwlc38_driver_t *)context;

  // Schedule the report readout
  drv->report_readout_requested = true;
  stwlc38_fsm_continue(drv);
}

static void stwlc38_i2c_callback(void *context, i2c_packet_t *packet) {
  stwlc38_driver_t *drv = (stwlc38_driver_t *)context;

  if (packet->status != I2C_STATUS_OK) {
    memset(&drv->report, 0, sizeof(stwlc38_report_t));
    // Kill periodic timer
    systimer_unset(drv->timer);
    // !@# retry on error?????
    drv->state = STWLC38_STATE_POWER_DOWN;
    drv->report_readout_requested = false;

    return;
  }

  switch (drv->state) {
    case STWLC38_STATE_REPORT_READOUT:
      drv->report_readout_requested = false;

      bool was_ready = drv->report.ready;

      // Status registers readout completed
      memset(&drv->report, 0, sizeof(stwlc38_report_t));
      drv->report.ready = true;
      drv->report.vout_ready = drv->report_regs.status0 & 0x40;
      drv->report.vrect = drv->report_regs.vrect / 1000.0;
      drv->report.vout = drv->report_regs.vout / 1000.0;
      drv->report.icur = drv->report_regs.icur;
      drv->report.tmeas = drv->report_regs.tmeas / 10.0;
      drv->report.opfreq = drv->report_regs.opfreq;
      drv->report.ntc = drv->report_regs.ntc / 10.0;

      // Just powered-up ?
      if (!was_ready) {
        // After power-up, ensure that the main LDO is in the requested state
        drv->vout_enabled = !drv->vout_enabled_requested;
        // Start the periodic timer
        systimer_set_periodic(drv->timer, STWLC38_REPORT_READOUT_INTERVAL_MS);
      }

      break;

    case STWLC38_STATE_VOUT_ENABLE:
      // Main LDO output enabled
      drv->vout_enabled = true;
      break;

    case STWLC38_STATE_VOUT_DISABLE:
      // Main LDO output disabled
      drv->vout_enabled = false;
      break;

    default:
      // This should never happen
      break;
  }

  drv->state = STWLC38_STATE_IDLE;
  stwlc38_fsm_continue(drv);
}

void STWLC38_EXTI_INTERRUPT_HANDLER(void) {
  stwlc38_driver_t *drv = &g_stwlc38_driver;

  // Clear the EXTI line pending bit
  __HAL_GPIO_EXTI_CLEAR_FLAG(STWLC38_INT_PIN);

  if (drv->state == STWLC38_STATE_POWER_DOWN) {
    // Inform the powerctl module about the WPC
    // wakeup_flags_set(WAKEUP_FLAGS_WPC);
    drv->report_readout_requested = true;
    stwlc38_fsm_continue(drv);
  }
}

static void stwlc38_fsm_continue(stwlc38_driver_t *drv) {
  // The order of the following conditions defines the priority

  if (drv->state == STWLC38_STATE_POWER_DOWN && drv->report_readout_requested) {
    // Check if the i2c interface is ready
    stwlc38_i2c_submit(drv, stwlc38_ops_report_readout);
    drv->state = STWLC38_STATE_REPORT_READOUT;
    return;
  }

  if (drv->state != STWLC38_STATE_IDLE) {
    return;
  }

  if (drv->vout_enabled != drv->vout_enabled_requested) {
    // Enable/Disable the main LDO output
    if (drv->vout_enabled_requested) {
      stwlc38_i2c_submit(drv, stwlc38_ops_vout_enable);
      drv->state = STWLC38_STATE_VOUT_ENABLE;
    } else {
      stwlc38_i2c_submit(drv, stwlc38_ops_vout_disable);
      drv->state = STWLC38_STATE_VOUT_DISABLE;
    }
  } else if (drv->report_readout_requested) {
    // Read status registers
    stwlc38_i2c_submit(drv, stwlc38_ops_report_readout);
    drv->state = STWLC38_STATE_REPORT_READOUT;
  }
}

#endif  // KERNEL_MODE
