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

// I2C address of the FT6X36 on the I2C bus.
#define FT6X36_I2C_ADDR 0x38

// ------------------------------------------------------------
// FT6X36 registers
// ------------------------------------------------------------

// Gesture ID (see `FT6X36_GESTURE_xxx`)
#define FT6X63_REG_GEST_ID 0x01

// TD_STATUS (number of touch points in lower 4 bits)
#define FT6X63_REG_TD_STATUS 0x02

// Event flags in higher 2 bits (see `FT6X63_EVENT_xxx`)
// MSB of touch x-coordinate in lower 4 bits
#define FT6X63_REG_P1_XH 0x03

// LSB of touch x-coordinate
#define FT6X63_REG_P1_XL 0x04

// MSB of touch y-coordinate in lower 4 bits
#define FT6X63_REG_P1_YH 0x05

// LSB of touch y-coordinate
#define FT6X63_REG_P1_YL 0x06

// Threshold for touch detection
#define FT6X36_REG_TH_GROUP 0x80

// Mode register
// 0x00 - interrupt polling mode
// 0x01 - interrupt trigger mode
#define FT6X36_REG_G_MODE 0xA4

// Firmware version
#define FT6X36_REG_FIRMID 0xA6

// ------------------------------------------------------------
// Event bits (see FT6X63_REG_P1_XH)
// ------------------------------------------------------------

#define FT6X63_EVENT_PRESS_DOWN 0x00
#define FT6X63_EVENT_CONTACT 0x80
#define FT6X63_EVENT_LIFT_UP 0x40
#define FT6X63_EVENT_MASK 0xC0

// ------------------------------------------------------------
// Gesture types (see FT6X63_REG_GEST_ID)
// ------------------------------------------------------------

#define FT6X36_GESTURE_NONE 0x00
