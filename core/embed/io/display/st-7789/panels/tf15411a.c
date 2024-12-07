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

#include "../display_io.h"
#include "tf15411a.h"

void tf15411a_init_seq(void) {
  // Inter Register Enable1
  ISSUE_CMD_BYTE(0xFE);

  // Inter Register Enable2
  ISSUE_CMD_BYTE(0xEF);

  // TEON: Tearing Effect Line On; V-blanking only
  ISSUE_CMD_BYTE(0x35);
  ISSUE_DATA_BYTE(0x00);

  // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits
  // input)
  ISSUE_CMD_BYTE(0x3A);
  ISSUE_DATA_BYTE(0x55);

  // Frame Rate
  // ISSUE_CMD_BYTE(0xE8); ISSUE_DATA_BYTE(0x12); ISSUE_DATA_BYTE(0x00);

  // Power Control 2
  ISSUE_CMD_BYTE(0xC3);
  ISSUE_DATA_BYTE(0x27);

  // Power Control 3
  ISSUE_CMD_BYTE(0xC4);
  ISSUE_DATA_BYTE(0x18);

  // Power Control 4
  ISSUE_CMD_BYTE(0xC9);
  ISSUE_DATA_BYTE(0x1F);

  ISSUE_CMD_BYTE(0xC5);
  ISSUE_DATA_BYTE(0x0F);

  ISSUE_CMD_BYTE(0xC6);
  ISSUE_DATA_BYTE(0x00);

  ISSUE_CMD_BYTE(0xC7);
  ISSUE_DATA_BYTE(0x10);

  ISSUE_CMD_BYTE(0xC8);
  ISSUE_DATA_BYTE(0x01);

  ISSUE_CMD_BYTE(0xFF);
  ISSUE_DATA_BYTE(0x62);

  ISSUE_CMD_BYTE(0x99);
  ISSUE_DATA_BYTE(0x3E);

  ISSUE_CMD_BYTE(0x9D);
  ISSUE_DATA_BYTE(0x4B);

  ISSUE_CMD_BYTE(0x8E);
  ISSUE_DATA_BYTE(0x0F);

  // SET_GAMMA1
  ISSUE_CMD_BYTE(0xF0);
  ISSUE_DATA_BYTE(0x8F);
  ISSUE_DATA_BYTE(0x1B);
  ISSUE_DATA_BYTE(0x05);
  ISSUE_DATA_BYTE(0x06);
  ISSUE_DATA_BYTE(0x07);
  ISSUE_DATA_BYTE(0x42);

  // SET_GAMMA3
  ISSUE_CMD_BYTE(0xF2);
  ISSUE_DATA_BYTE(0x5C);
  ISSUE_DATA_BYTE(0x1F);
  ISSUE_DATA_BYTE(0x12);
  ISSUE_DATA_BYTE(0x10);
  ISSUE_DATA_BYTE(0x07);
  ISSUE_DATA_BYTE(0x43);

  // SET_GAMMA2
  ISSUE_CMD_BYTE(0xF1);
  ISSUE_DATA_BYTE(0x59);
  ISSUE_DATA_BYTE(0xCF);
  ISSUE_DATA_BYTE(0xCF);
  ISSUE_DATA_BYTE(0x35);
  ISSUE_DATA_BYTE(0x37);
  ISSUE_DATA_BYTE(0x8F);

  // SET_GAMMA4
  ISSUE_CMD_BYTE(0xF3);
  ISSUE_DATA_BYTE(0x58);
  ISSUE_DATA_BYTE(0xCF);
  ISSUE_DATA_BYTE(0xCF);
  ISSUE_DATA_BYTE(0x35);
  ISSUE_DATA_BYTE(0x37);
  ISSUE_DATA_BYTE(0x8F);
}

void tf15411a_rotate(int degrees, display_padding_t* padding) {
  uint16_t shift = 0;
  char BX = 0, BY = 0;

#define RGB (1 << 3)
#define ML (1 << 4)  // vertical refresh order
#define MH (1 << 2)  // horizontal refresh order
#define MV (1 << 5)
#define MX (1 << 6)
#define MY (1 << 7)
  // MADCTL: Memory Data Access Control - reference:
  // section 9.3 in the ILI9341 manual
  // section 6.2.18 in the GC9307 manual
  // section 8.12 in the ST7789V manual
  uint8_t display_command_parameter = 0;
  switch (degrees) {
    case 0:
      display_command_parameter = 0;
      BY = 1;
      break;
    case 90:
      display_command_parameter = MV | MX | MH | ML;
      BX = 0;
      shift = 1;
      break;
    case 180:
      display_command_parameter = MX | MY | MH | ML;
      BY = 1;
      shift = 1;
      break;
    case 270:
      display_command_parameter = MV | MY;
      BX = 0;
      break;
  }

  display_command_parameter ^= RGB | MY;  // XOR RGB and MY settings

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
