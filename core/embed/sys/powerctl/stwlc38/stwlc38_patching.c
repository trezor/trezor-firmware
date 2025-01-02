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

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/i2c_bus.h>
#include <sys/irq.h>
#include <sys/systick.h>
#include <sys/systimer.h>

#include "nvm_data.h"
#include "stwlc38.h"
#include "stwlc38_defs.h"
#include "stwlc38_internal.h"

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
          .size = (uint16_t)size,
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
