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

#endif  // TREZORHAL_STWLC38_DEFS_H
