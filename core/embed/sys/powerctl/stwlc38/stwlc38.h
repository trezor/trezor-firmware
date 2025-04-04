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

#include <trezor_types.h>

typedef enum {
  OP_MODE_SA = 1,
  OP_MODE_RX = 2,
  OP_MODE_TX = 3,
} stwlc38_op_mode_t;

typedef enum {
  STWLC38_UNKNOWN_CHIP_REV = 0,
  STWLC38_CUT_1_2 = 0x3,
  STWLC38_CUT_1_3 = 0x4,
} stwlc38_chip_rev_t;

typedef struct {
  uint16_t chip_id;           // Chip ID
  uint8_t chip_rev;           // Chip Revision
  uint8_t cust_id;            // Customer ID
  uint16_t rom_id;            // ROM ID
  uint16_t patch_id;          // Patch ID
  uint16_t cfg_id;            // Config ID
  uint16_t pe_id;             // Production ID
  stwlc38_op_mode_t op_mode;  // Operation mode
  uint8_t device_id[16];      // Device ID
  union {
    uint32_t sys_err;  // System error
    struct {
      uint32_t core_hard_fault : 1;
      uint32_t reserved_bit_1 : 1;
      uint32_t nvm_ip_err : 1;
      uint32_t reserved_bit_3 : 1;
      uint32_t nvm_boot_err : 1;
      uint32_t reserved_3 : 3;
      uint32_t nvm_pe_error : 2;
      uint32_t nvm_config_err : 2;
      uint32_t nvm_patch_err : 2;
      uint32_t nvm_prod_info_err : 2;
      uint32_t reserved_4 : 16;
    };
  };
} stwlc38_chip_info_t;

typedef struct {
  // Powered-up and initialized
  bool ready;
  // Providing power to the system
  bool vout_ready;

  // Rectified voltage [V]
  float vrect;
  // Main LDO voltage output [V]
  float vout;
  // Output current [mA]
  float icur;
  // Chip temperature [°C]
  float tmeas;
  // Operating frequency [kHz]
  uint16_t opfreq;
  // NTC Temperature [°C]
  float ntc;

} stwlc38_report_t;

// Initializes STWLC38 driver
//
// After initialization, the STWLC38 is enabled by default.
bool stwlc38_init(void);

// Deinitializes STWLC38 driver
void stwlc38_deinit(void);

// Enables or disables the STWLC38. This can be used to enable/disable
// wireless charging functionality.
//
// If the STWLC38 is disabled, it's not self-powered and is unable to
// communicate over I2C. STWLC38 is enabled by default after initialization.
//
// Returns true if the STWLC38 was successfully enabled or disabled.
bool stwlc38_enable(bool enable);

// Enables or disables the main LDO output.
//
// Main LDO output is enabled by default after initialization.
//
// Returns true if the main LDO output was successfully enabled or disabled.
bool stwlc38_enable_vout(bool enable);

// Reads the chip information from the STWLC38
//
// The chip information is read from the STWLC38 and stored in the provided
// chip_info structure.
//
// Returns true if the chip information was successfully read.
bool stwlc38_read_chip_info(stwlc38_chip_info_t* chip_info);

// Performs the firmware patch and config update on the STWLC38
//
//
// To perform the update, the STWLC38 must be in standalone mode (5V on VOUT
// pin).
//
// Returns true if the firmware and config update was successfully performed.
bool stwlc38_patch_and_config();

// Gets the current report from the STWLC38
bool stwlc38_get_report(stwlc38_report_t* status);
