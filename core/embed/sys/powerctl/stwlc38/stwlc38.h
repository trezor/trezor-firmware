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

#ifndef TREZORHAL_STWLC38_H
#define TREZORHAL_STWLC38_H

#include <trezor_types.h>

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
// communicate over I2C. STWLC38 is disabled by default after initialization.
//
// Returns true if the STWLC38 was successfully enabled or disabled.
bool stwlc38_enable(bool enable);

// Enables or disables the main LDO output.
//
// Main LDO output is enabled by default after initialization.
//
// Returns true if the main LDO output was successfully enabled or disabled.
bool stwlc38_enable_vout(bool enable);

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

// Gets the current report from the STWLC38
bool stwlc38_get_report(stwlc38_report_t* status);

#endif  // TREZORHAL_STWLC38_H
