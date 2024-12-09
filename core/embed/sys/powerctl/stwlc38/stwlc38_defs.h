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

#ifndef TREZORHAL_STWLC38_DEFS_H
#define TREZORHAL_STWLC38_DEFS_H

// I2C address of the STWLC38 on the I2C bus.
#define STWLC38_I2C_ADDRESS 0x61

// RX Command register
#define STWLC38_RX_COMMAND 0x90

// Rectified voltage [mV/16-bit]
#define STWLC38_REG_VRECT 0x92
// Main LDO voltage output [mV/16-bit]
#define STWLC38_REG_VOUT 0x94
// Output current [mA]
#define STWLC38_REG_ICUR 0x96
// Chip temperature [°C * 10]
#define STWLC38_REG_TMEAS 0x98
// Operating frequency [kHz]
#define STWLC38_REG_OPFREQ 0x9A
// NTC Temperature [°C * 10]
#define STWLC38_REG_NTC 0x9C

// 3-byte status register
#define STWLC38_REG_RXINT_STATUS0 0x8C
#define STWLC38_REG_RXINT_STATUS1 0x8D
#define STWLC38_REG_RXINT_STATUS2 0x8E

// Common_Definitions
#define STWLC38_MAX_READ_CHUNK 500U
#define STWLC38_MAX_WRITE_CHUNK 250U
#define STWLC38_LOG_SIZE 1024U
#define STWLC38_GENERAL_POLLING_MS 50U
#define STWLC38_GENERAL_TIMEOUT 100U
#define STWLC38_RESET_DELAY_MS 50U

// NVM Definitions
#define STWLC38_NVM_WRITE_INTERVAL_MS 1U
#define STWLC38_NVM_WRITE_TIMEOUT 20U
#define STWLC38_NVM_UPDATE_MAX_RETRY 3U

#define STWLC38_NVM_SECTOR_BYTE_SIZE 256U
#define STWLC38_NVM_PATCH_START_SECTOR_INDEX 0U
#define STWLC38_NVM_CFG_START_SECTOR_INDEX 126U
#define STWLC38_NVM_PATCH_TOTAL_SECTOR 126U
#define STWLC38_NVM_CFG_TOTAL_SECTOR 2U
#define STWLC38_NVM_PATCH_SIZE \
  (STWLC38_NVM_PATCH_TOTAL_SECTOR * STWLC38_NVM_SECTOR_BYTE_SIZE)
#define STWLC38_NVM_CFG_SIZE \
  (STWLC38_NVM_CFG_TOTAL_SECTOR * STWLC38_NVM_SECTOR_BYTE_SIZE)

// HW Registers
#define STWLC38_OPCODE_WRITE 0xFA
#define STWLC38_OPCODE_SIZE 1U

#define STWLC38_HWREG_CUT_ID_REG 0x2001C002U
#define STWLC38_HWREG_RESET_REG 0x2001F200U

// FW Registers
#define STWLC38_FWREG_CHIP_ID_REG 0x0000U
#define STWLC38_FWREG_OP_MODE_REG 0x000EU
#define STWLC38_FWREG_DEVICE_ID_REG 0x0010U
#define STWLC38_FWREG_SYS_CMD_REG 0x0020U
#define STWLC38_FWREG_NVM_PWD_REG 0x0022U
#define STWLC38_FWREG_NVM_SEC_IDX_REG 0x0024U
#define STWLC38_FWREG_SYS_ERR_REG 0x002CU
#define STWLC38_FWREG_AUX_DATA_00_REG 0x0180U

// STWLC38 driver error codes
#define STWLC38_OK 0x0U
#define STWLC38_ERR_BUS_W 0x80000000U
#define STWLC38_ERR_BUS_WR 0x80000001U
#define STWLC38_ERR_ALLOC_MEM 0x80000002U
#define STWLC38_ERR_INVALID_PARAM 0x80000003U
#define STWLC38_ERR_TIMEOUT 0x80000004U
#define STWLC38_ERR_INVALID_OP_MODE 0x80000005U
#define STWLC38_ERR_INVALID_CHIP_ID 0x80000006U
#define STWLC38_ERR_NVM_ID_MISMATCH 0x80000007U
#define STWLC38_ERR_NVM_DATA_CORRUPTED 0x80000008U

#endif  // TREZORHAL_STWLC38_DEFS_H
