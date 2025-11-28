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

// I2C address of the FT3168 on the I2C bus.
#define FT3168_I2C_ADDR 0x38

// ------------------------------------------------------------
// FT3168 registers
// ------------------------------------------------------------

// Gesture ID (see `FT3168_GESTURE_xxx`)
#define FT3168_REG_GEST_ID 0x01

// TD_STATUS (number of touch points in lower 4 bits)
#define FT3168_REG_TD_STATUS 0x02

// Event flags in higher 2 bits (see `FT3168_EVENT_xxx`)
// MSB of touch x-coordinate in lower 4 bits
#define FT3168_REG_P1_XH 0x03

// LSB of touch x-coordinate
#define FT3168_REG_P1_XL 0x04

// MSB of touch y-coordinate in lower 4 bits
#define FT3168_REG_P1_YH 0x05

// LSB of touch y-coordinate
#define FT3168_REG_P1_YL 0x06

// Threshold for touch detection
#define FT3168_REG_TH_GROUP 0x80

// Monitor mode switch. Allow entry into monitor mode?
// 0x01: Allow
// 0x00: Disable
#define FT3168_REG_G_CTRL 0x86

// No touch to enter monitor delay. If no touch occurs within a specified time,
// it enters MONITOR mode. This mode needs to be used in conjunction with the
// "monitor mode switch" parameter. The unit is seconds.
#define FT3168_REG_G_TIMEENTERMONITOR 0x87

// Mode register
// 0x00 - interrupt polling mode
// 0x01 - interrupt trigger mode
#define FT3168_REG_G_MODE 0xA4

// Chip operating modes. Power consumption mode
// 0x00: P_ACTIVE
// 0x01: P_MONITOR
// 0x03: P_HIBERNATE
#define FT3168_REG_G_PMODE 0xA5

// Firmware version
#define FT3168_REG_FIRMID 0xA6

// ------------------------------------------------------------
// Event bits (see FT3168_REG_P1_XH)
// ------------------------------------------------------------

#define FT3168_EVENT_PRESS_DOWN 0x00
#define FT3168_EVENT_CONTACT 0x80
#define FT3168_EVENT_LIFT_UP 0x40
#define FT3168_EVENT_MASK 0xC0

// ------------------------------------------------------------
// Gesture types (see FT3168_REG_GEST_ID)
// ------------------------------------------------------------

#define FT3168_GESTURE_NONE 0x00

// ------------------------------------------------------------
// Monitor mode switch (see FT3168_REG_G_CTRL)
// ------------------------------------------------------------

#define FT3168_P_MONITOR_AUTO_ENTRY_ON 0x01
#define FT3168_P_MONITOR_AUTO_ENTRY_OFF 0x00

// ------------------------------------------------------------
// Interrupt modes(see FT3168_REG_G_MODE)
// ------------------------------------------------------------

#define FT3168_INT_POL_MODE 0x00
#define FT3168_INT_TRIG_MODE 0x01

// ------------------------------------------------------------
// Power modes (see FT3168_REG_G_PMODE)
// ------------------------------------------------------------

typedef enum {
  P_ACTIVE_MODE = 0x00,
  P_MONITOR_MODE = 0x01,
  P_HIBERNATE_MODE = 0x03
} power_mode_t;
