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

#include "lx154a2482.h"

#include "../display_io.h"

void lx154a2482_gamma(void) {
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

void lx154a2482_init_seq(void) {
  // TEON: Tearing Effect Line On; V-blanking only
  ISSUE_CMD_BYTE(0x35);
  ISSUE_DATA_BYTE(0x00);

  // Memory Data Access Control (MADCTL)
  ISSUE_CMD_BYTE(0x36);
  ISSUE_DATA_BYTE(0x00);

  // Interface Pixel Format
  ISSUE_CMD_BYTE(0x3A);
  ISSUE_DATA_BYTE(0x05);

  // Column Address Set
  ISSUE_CMD_BYTE(0x2A);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0xEF);

  // Row Address Set
  ISSUE_CMD_BYTE(0x2B);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0xEF);

  //  Porch Setting
  ISSUE_CMD_BYTE(0xB2);
  ISSUE_DATA_BYTE(0x0C);
  ISSUE_DATA_BYTE(0x0C);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x33);
  ISSUE_DATA_BYTE(0x33);

  // VCOM Setting
  ISSUE_CMD_BYTE(0xBB);
  ISSUE_DATA_BYTE(0x1F);

  // LCMCTRL: LCM Control: XOR RGB setting
  ISSUE_CMD_BYTE(0xC0);
  ISSUE_DATA_BYTE(0x20);

  // VDV and VRH Command Enable
  ISSUE_CMD_BYTE(0xC2);
  ISSUE_DATA_BYTE(0x01);

  // VRH Set
  ISSUE_CMD_BYTE(0xC3);
  ISSUE_DATA_BYTE(0x0F);  // 4.3V

  // VDV Setting
  ISSUE_CMD_BYTE(0xC4);
  ISSUE_DATA_BYTE(0x20);

  // Frame Rate Control in Normal Mode
  ISSUE_CMD_BYTE(0xC6);
  ISSUE_DATA_BYTE(0xEF);  // column inversion     //0X0F  Dot INV, 60Hz

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

  lx154a2482_gamma();
}

void lx154a2482_rotate(int degrees, display_padding_t* padding) {
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
