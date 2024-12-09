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

#include "nvm_data.h"
#include "stwlc38.h"
#include "stwlc38_defs.h"

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
#define STWLC37_ENB_PORT GPIOD
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

// STWLC38 driver instance
static stwlc38_driver_t g_stwlc38_driver = {
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

static i2c_status_t stwlc38_write_fw_register(i2c_bus_t *i2c_bus,
                                              uint16_t address, uint8_t value);
static i2c_status_t stwlc38_write_hw_register(i2c_bus_t *i2c_bus,
                                              uint32_t address, uint8_t vaule);
static i2c_status_t stwlc38_read_fw_register(i2c_bus_t *i2c_bus,
                                             uint16_t address, uint8_t *data);
static i2c_status_t stwlc38_write_n_bytes(i2c_bus_t *i2c_bus, uint16_t address,
                                          uint8_t *data, size_t size);
static i2c_status_t stwlc38_read_n_bytes(i2c_bus_t *i2c_bus, uint16_t address,
                                         uint8_t *data, size_t size);
static i2c_status_t stwlc38_nvm_write_sector(i2c_bus_t *i2c_bus,
                                             const uint8_t *data, size_t size,
                                             uint8_t sec_idx);
static i2c_status_t stwlc38_nvm_write_bulk(i2c_bus_t *i2c_bus,
                                           const uint8_t *data, size_t size,
                                           uint8_t sec_idx);

bool stwlc38_patch_and_config() {
  stwlc38_driver_t *drv = &g_stwlc38_driver;
  i2c_status_t status;

  if (!drv->initialized) {
    return false;
  }

  // Check op mode
  uint8_t reg;
  status =
      stwlc38_read_fw_register(drv->i2c_bus, STWLC38_FWREG_OP_MODE_REG, &reg);
  if (status != I2C_STATUS_OK) {
    return false;
  }

  if (reg != OP_MODE_SA) {
    return false;
  }

  // Reset and disable NVM loading
  status =
      stwlc38_write_fw_register(drv->i2c_bus, STWLC38_FWREG_SYS_CMD_REG, 0x40);
  if (status != I2C_STATUS_OK) {
    return false;
  }

  systick_delay_ms(STWLC38_RESET_DELAY_MS);

  // Check op mode again
  status =
      stwlc38_read_fw_register(drv->i2c_bus, STWLC38_FWREG_OP_MODE_REG, &reg);
  if (status != I2C_STATUS_OK) {
    return false;
  }

  if (reg != OP_MODE_SA) {
    return false;
  }

  // Unlock NVM
  status =
      stwlc38_write_fw_register(drv->i2c_bus, STWLC38_FWREG_NVM_PWD_REG, 0xC5);
  if (status != I2C_STATUS_OK) {
    return false;
  }

  // Write patch to NVM
  status = stwlc38_nvm_write_bulk(drv->i2c_bus, patch_data, NVM_PATCH_SIZE,
                                  STWLC38_NVM_PATCH_START_SECTOR_INDEX);
  if (status != I2C_STATUS_OK) {
    return false;
  }

  // Write config to NVM
  status = stwlc38_nvm_write_bulk(drv->i2c_bus, cfg_data, NVM_CFG_SIZE,
                                  STWLC38_NVM_CFG_START_SECTOR_INDEX);
  if (status != I2C_STATUS_OK) {
    return false;
  }

  // Reset stwlc38
  status =
      stwlc38_write_hw_register(drv->i2c_bus, STWLC38_HWREG_RESET_REG, 0x01);
  if (status != I2C_STATUS_OK) {
    return false;
  }

  systick_delay_ms(STWLC38_RESET_DELAY_MS);

  return true;
}

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

bool stwlc38_read_chip_info(stwlc38_chip_info_t *chip_info) {
  stwlc38_driver_t *drv = &g_stwlc38_driver;

  if (!drv->initialized) {
    return false;
  }

  systimer_key_t lock = systimer_suspend(drv->timer);

  uint8_t raw_data[16];

  // Read first block of chip information (Address 0x0000 - 0x000F)
  i2c_status_t ret = stwlc38_read_n_bytes(
      drv->i2c_bus, STWLC38_FWREG_CHIP_ID_REG, (uint8_t *)&raw_data, 15);
  if (ret != I2C_STATUS_OK) {
    systimer_resume(drv->timer, lock);
    return false;
  }

  // Parse raw data into chip info structure
  chip_info->chip_id = (uint16_t)((raw_data[1] << 8) + raw_data[0]);
  chip_info->chip_rev = raw_data[2];
  chip_info->cust_id = raw_data[3];
  chip_info->rom_id = (uint16_t)((raw_data[5] << 8) + raw_data[4]);
  chip_info->patch_id = (uint16_t)((raw_data[7] << 8) + raw_data[6]);
  chip_info->cfg_id = (uint16_t)((raw_data[11] << 8) + raw_data[10]);
  chip_info->pe_id = (uint16_t)((raw_data[13] << 8) + raw_data[12]);
  chip_info->op_mode = raw_data[14];

  // Read second block of chip information - device ID (Address 0x0010 - 0x001F)
  ret = stwlc38_read_n_bytes(drv->i2c_bus, STWLC38_FWREG_DEVICE_ID_REG,
                             (uint8_t *)&raw_data, 16);
  if (ret != I2C_STATUS_OK) {
    systimer_resume(drv->timer, lock);
    return false;
  }

  memcpy(&(chip_info->device_id), raw_data, 16);

  // Read third block of chip information - system error (Address 0x002C -
  // 0x002F)
  ret = stwlc38_read_n_bytes(drv->i2c_bus, STWLC38_FWREG_SYS_ERR_REG,
                             (uint8_t *)&raw_data, 4);
  if (ret != I2C_STATUS_OK) {
    systimer_resume(drv->timer, lock);
    return false;
  }

  memcpy(&(chip_info->sys_err), raw_data, 4);

  systimer_resume(drv->timer, lock);

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

static i2c_status_t stwlc38_write_fw_register(i2c_bus_t *i2c_bus,
                                              uint16_t address, uint8_t value) {
  i2c_status_t status;

  i2c_op_t op[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 3,
          .data = {(address) >> 8, (address) & 0xFF, value},
      },
  };

  i2c_packet_t i2c_pkt = {
      .address = STWLC38_I2C_ADDRESS,
      .ops = (i2c_op_t *)&op,
      .op_count = ARRAY_LENGTH(op),
  };

  status = i2c_bus_submit_and_wait(i2c_bus, &i2c_pkt);

  return status;
}

static i2c_status_t stwlc38_read_fw_register(i2c_bus_t *i2c_bus,
                                             uint16_t address, uint8_t *data) {
  i2c_op_t op[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 2,
          .data = {address >> 8, address & 0xFF},
      },
      {
          .flags = I2C_FLAG_RX,
          .size = 1,
          .ptr = data,
      },
  };

  i2c_packet_t i2c_pkt = {
      .address = STWLC38_I2C_ADDRESS,
      .ops = (i2c_op_t *)&op,
      .op_count = ARRAY_LENGTH(op),
  };

  i2c_status_t status = i2c_bus_submit_and_wait(i2c_bus, &i2c_pkt);

  return status;
}

static i2c_status_t stwlc38_write_hw_register(i2c_bus_t *i2c_bus,
                                              uint32_t address, uint8_t value) {
  i2c_op_t op[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 4,
          .data =
              {
                  (STWLC38_HWREG_CUT_ID_REG && 0xFF000000) >> 24,
                  (STWLC38_HWREG_CUT_ID_REG && 0x00FF0000) >> 16,
                  (STWLC38_HWREG_CUT_ID_REG && 0x0000FF00) >> 8,
                  (STWLC38_HWREG_CUT_ID_REG && 0x000000FF),
              },
      },
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 1,
          .data = {value},
      },
  };

  i2c_packet_t i2c_pkt = {
      .address = STWLC38_I2C_ADDRESS,
      .ops = (i2c_op_t *)&op,
      .op_count = ARRAY_LENGTH(op),
  };

  i2c_status_t status = i2c_bus_submit_and_wait(i2c_bus, &i2c_pkt);
  return status;
}

static i2c_status_t stwlc38_write_n_bytes(i2c_bus_t *i2c_bus, uint16_t address,
                                          uint8_t *data, size_t size) {
  i2c_op_t op[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 2,
          .data = {(address) >> 8, (address) & 0xFF},
      },
      {
          .flags = I2C_FLAG_TX,
          .size = size,
          .ptr = data,
      },
  };

  i2c_packet_t i2c_pkt = {
      .address = STWLC38_I2C_ADDRESS,
      .ops = (i2c_op_t *)&op,
      .op_count = ARRAY_LENGTH(op),
  };

  i2c_status_t status = i2c_bus_submit_and_wait(i2c_bus, &i2c_pkt);
  return status;
}

static i2c_status_t stwlc38_read_n_bytes(i2c_bus_t *i2c_bus, uint16_t address,
                                         uint8_t *data, size_t size) {
  i2c_op_t op[] = {
      {
          .flags = I2C_FLAG_TX | I2C_FLAG_EMBED,
          .size = 2,
          .data = {(address) >> 8, (address) & 0xFF},
      },
      {
          .flags = I2C_FLAG_RX,
          .size = (uint16_t) size,
          .ptr = data,
      },
  };

  i2c_packet_t i2c_pkt = {
      .address = STWLC38_I2C_ADDRESS,
      .ops = (i2c_op_t *)&op,
      .op_count = ARRAY_LENGTH(op),
  };

  i2c_status_t status = i2c_bus_submit_and_wait(i2c_bus, &i2c_pkt);
  return status;
}

static i2c_status_t stwlc38_nvm_write_sector(i2c_bus_t *i2c_bus,
                                             const uint8_t *data, size_t size,
                                             uint8_t sec_idx) {
  int32_t ret;
  int32_t i;
  int32_t timeout = 1;
  uint8_t reg;

  ret = stwlc38_write_fw_register(i2c_bus, STWLC38_FWREG_NVM_SEC_IDX_REG,
                                  sec_idx);
  if (ret != I2C_STATUS_OK) {
    return ret;
  }

  ret = stwlc38_write_fw_register(i2c_bus, STWLC38_FWREG_SYS_CMD_REG, 0x10);
  if (ret != I2C_STATUS_OK) {
    return ret;
  }

  size_t remaining = size;
  int8_t chunk = 0;
  while (remaining > 0) {
    if (remaining > STWLC38_MAX_WRITE_CHUNK) {
      ret = stwlc38_write_n_bytes(
          i2c_bus,
          STWLC38_FWREG_AUX_DATA_00_REG + chunk * STWLC38_MAX_WRITE_CHUNK,
          ((uint8_t *)(data)) + chunk * STWLC38_MAX_WRITE_CHUNK,
          STWLC38_MAX_WRITE_CHUNK);
      if (ret != I2C_STATUS_OK) {
        return ret;
      }

      remaining -= STWLC38_MAX_WRITE_CHUNK;

    } else {
      ret = stwlc38_write_n_bytes(
          i2c_bus,
          STWLC38_FWREG_AUX_DATA_00_REG + chunk * STWLC38_MAX_WRITE_CHUNK,
          ((uint8_t *)data) + chunk * STWLC38_MAX_WRITE_CHUNK, remaining);
      if (ret != I2C_STATUS_OK) {
        return ret;
      }

      break;
    }

    chunk++;
  }

  ret = stwlc38_write_fw_register(i2c_bus, STWLC38_FWREG_SYS_CMD_REG, 0x04);
  if (ret != I2C_STATUS_OK) {
    return ret;
  }

  for (i = 0; i < STWLC38_NVM_WRITE_TIMEOUT; i++) {
    systick_delay_ms(STWLC38_NVM_WRITE_INTERVAL_MS);

    ret = stwlc38_read_fw_register(i2c_bus, STWLC38_FWREG_SYS_CMD_REG, &reg);
    if (ret != I2C_STATUS_OK) {
      return ret;
    }

    if ((reg & 0x04) == 0) {
      timeout = 0;
      break;
    }
  }

  ret = stwlc38_write_fw_register(i2c_bus, STWLC38_FWREG_SYS_CMD_REG, 0x20);
  if (ret != I2C_STATUS_OK) {
    return ret;
  }

  return timeout ? I2C_STATUS_TIMEOUT : I2C_STATUS_OK;
}

static i2c_status_t stwlc38_nvm_write_bulk(i2c_bus_t *i2c_bus,
                                           const uint8_t *data, size_t size,
                                           uint8_t sec_idx) {
  int32_t ret;
  size_t remaining = size;
  int32_t to_write_now = 0;
  int32_t written_already = 0;

  while (remaining > 0) {
    to_write_now = remaining > STWLC38_NVM_SECTOR_BYTE_SIZE
                       ? STWLC38_NVM_SECTOR_BYTE_SIZE
                       : remaining;

    ret = stwlc38_nvm_write_sector(i2c_bus, data + written_already,
                                   to_write_now, sec_idx);
    if (ret != I2C_STATUS_OK) {
      return ret;
    }

    remaining -= to_write_now;
    written_already += to_write_now;
    sec_idx++;
  }

  return I2C_STATUS_OK;
}

#endif  // KERNEL_MODE
