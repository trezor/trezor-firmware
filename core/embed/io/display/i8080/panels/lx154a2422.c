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

#include <trezor_model.h>

#include "lx154a2422.h"

#include "../display_io.h"

void lx154a2422_gamma(void) {
  // positive voltage correction
  ISSUE_CMD_BYTE(0xE0);
  ISSUE_DATA_BYTE(0xD0);
  ISSUE_DATA_BYTE(0x0A);
  ISSUE_DATA_BYTE(0x10);
  ISSUE_DATA_BYTE(0x0A);
  ISSUE_DATA_BYTE(0x0A);
  ISSUE_DATA_BYTE(0x26);
  ISSUE_DATA_BYTE(0x36);
  ISSUE_DATA_BYTE(0x34);
  ISSUE_DATA_BYTE(0x4D);
  ISSUE_DATA_BYTE(0x18);
  ISSUE_DATA_BYTE(0x13);
  ISSUE_DATA_BYTE(0x14);
  ISSUE_DATA_BYTE(0x2F);
  ISSUE_DATA_BYTE(0x34);

  // negative voltage correction
  ISSUE_CMD_BYTE(0xE1);
  ISSUE_DATA_BYTE(0xD0);
  ISSUE_DATA_BYTE(0x0A);
  ISSUE_DATA_BYTE(0x10);
  ISSUE_DATA_BYTE(0x0A);
  ISSUE_DATA_BYTE(0x09);
  ISSUE_DATA_BYTE(0x26);
  ISSUE_DATA_BYTE(0x36);
  ISSUE_DATA_BYTE(0x53);
  ISSUE_DATA_BYTE(0x4C);
  ISSUE_DATA_BYTE(0x18);
  ISSUE_DATA_BYTE(0x14);
  ISSUE_DATA_BYTE(0x14);
  ISSUE_DATA_BYTE(0x2F);
  ISSUE_DATA_BYTE(0x34);
}

void lx154a2422_init_seq(void) {
  // most recent manual:
  // https://www.newhavendisplay.com/appnotes/datasheets/LCDs/ST7789V.pdf
  // TEON: Tearing Effect Line On; V-blanking only
  ISSUE_CMD_BYTE(0x35);
  ISSUE_DATA_BYTE(0x00);

  // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits
  // input)
  ISSUE_CMD_BYTE(0x3A);
  ISSUE_DATA_BYTE(0x55);

  // CMD2EN: Commands in command table 2 can be executed when EXTC level is Low
  ISSUE_CMD_BYTE(0xDF);
  ISSUE_DATA_BYTE(0x5A);
  ISSUE_DATA_BYTE(0x69);
  ISSUE_DATA_BYTE(0x02);
  ISSUE_DATA_BYTE(0x01);

  // LCMCTRL: LCM Control: XOR RGB setting
  ISSUE_CMD_BYTE(0xC0);
  ISSUE_DATA_BYTE(0x20);

  // GATECTRL: Gate Control; NL = 240 gate lines, first scan line is gate 80.;
  // gate scan direction 319 -> 0
  ISSUE_CMD_BYTE(0xE4);
  ISSUE_DATA_BYTE(0x1D);
  ISSUE_DATA_BYTE(0x0A);
  ISSUE_DATA_BYTE(0x11);

  // INVOFF (20h): Display Inversion Off
  // INVON  (21h): Display Inversion On
  ISSUE_CMD_BYTE(0x21);

  // the above config is the most important and definitely necessary

  // PWCTRL1: Power Control 1
  ISSUE_CMD_BYTE(0xD0);
  ISSUE_DATA_BYTE(0xA4);
  ISSUE_DATA_BYTE(0xA1);

  lx154a2422_gamma();
}

void lx154a2422_rotate(int degrees, display_padding_t* padding) {
  uint16_t shift = 0;
  char BX = 0, BY = 0;

#define RGB (1 << 3)
#define ML (1 << 4)  // vertical refresh order
#define MH (1 << 2)  // horizontal refresh order
#define MV (1 << 5)
#define MX (1 << 6)
#define MY (1 << 7)
  // MADCTL: Memory Data Access Control - reference:
  // section 8.12 in the ST7789V manual
  uint8_t display_command_parameter = 0;
  switch (degrees) {
    case 0:
      display_command_parameter = 0;
      BY = 0;
      break;
    case 90:
      display_command_parameter = MV | MX | MH | ML;
      BX = 1;
      shift = 1;
      break;
    case 180:
      display_command_parameter = MX | MY | MH | ML;
      BY = 0;
      shift = 1;
      break;
    case 270:
      display_command_parameter = MV | MY;
      BX = 1;
      break;
  }

  ISSUE_CMD_BYTE(0x36);
  ISSUE_DATA_BYTE(display_command_parameter);

  if (shift) {
    // GATECTRL: Gate Control; NL = 240 gate lines, first scan line is
    // gate 80.; gate scan direction 319 -> 0
    ISSUE_CMD_BYTE(0xE4);
    ISSUE_DATA_BYTE(0x1D);
    ISSUE_DATA_BYTE(0x00);
    ISSUE_DATA_BYTE(0x11);
  } else {
    // GATECTRL: Gate Control; NL = 240 gate lines, first scan line is
    // gate 80.; gate scan direction 319 -> 0
    ISSUE_CMD_BYTE(0xE4);
    ISSUE_DATA_BYTE(0x1D);
    ISSUE_DATA_BYTE(0x0A);
    ISSUE_DATA_BYTE(0x11);
  }

  padding->x = BX ? (320 - DISPLAY_RESY) : 0;
  padding->y = BY ? (320 - DISPLAY_RESY) : 0;
}
