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

// Register sequence adapted from the vendor GC9307 application note for a
// 240x320 IPS module (GC9307_BOE2.4_6-generation-line
// IPS(GV024QVQ-N81-3QP0)_AN_20230829); the module datasheets for
// LX240D4508CTP05A/B do not themselves provide a register init table.

#include <trezor_model.h>

#include "../display_io.h"
#include "lx240d4508ctp05.h"

void lx240d4508ctp05_init_seq(void) {
  // Inter Register Enable1 / Enable2
  ISSUE_CMD_BYTE(0xFE);
  ISSUE_CMD_BYTE(0xEF);

  // MADCTL: Memory Data Access Control; MX=1, RGB=1 (default orientation is
  // never re-applied via lx240d4508ctp05_rotate(), so this initial value is
  // the one that actually takes effect on a default-orientation boot)
  ISSUE_CMD_BYTE(0x36);
  ISSUE_DATA_BYTE(0x48);

  // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits
  // input)
  ISSUE_CMD_BYTE(0x3A);
  ISSUE_DATA_BYTE(0x05);

  ISSUE_CMD_BYTE(0x86);
  ISSUE_DATA_BYTE(0x98);

  ISSUE_CMD_BYTE(0x89);
  ISSUE_DATA_BYTE(0x03);

  ISSUE_CMD_BYTE(0x8B);
  ISSUE_DATA_BYTE(0x80);

  ISSUE_CMD_BYTE(0x8D);
  ISSUE_DATA_BYTE(0x33);

  ISSUE_CMD_BYTE(0x8E);
  ISSUE_DATA_BYTE(0x0F);

  // Frame Rate / inversion
  ISSUE_CMD_BYTE(0xE8);
  ISSUE_DATA_BYTE(0x13);
  ISSUE_DATA_BYTE(0x00);

  ISSUE_CMD_BYTE(0xFF);
  ISSUE_DATA_BYTE(0x62);

  ISSUE_CMD_BYTE(0x99);
  ISSUE_DATA_BYTE(0x3E);

  ISSUE_CMD_BYTE(0x9D);
  ISSUE_DATA_BYTE(0x4B);

  ISSUE_CMD_BYTE(0x98);
  ISSUE_DATA_BYTE(0x3E);

  ISSUE_CMD_BYTE(0x9C);
  ISSUE_DATA_BYTE(0x4B);

  // Power Control 2 (vbp for vreg1a/1b)
  ISSUE_CMD_BYTE(0xC3);
  ISSUE_DATA_BYTE(0x30);

  // Power Control 3 (vbn for vreg2a/2b)
  ISSUE_CMD_BYTE(0xC4);
  ISSUE_DATA_BYTE(0x18);

  // Power Control 4
  ISSUE_CMD_BYTE(0xC9);
  ISSUE_DATA_BYTE(0x0A);

  // Column Address Set: 0 .. 239
  ISSUE_CMD_BYTE(0x2A);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0xEF);

  // Row Address Set: 0 .. 319
  ISSUE_CMD_BYTE(0x2B);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x01);
  ISSUE_DATA_BYTE(0x3F);

  ISSUE_CMD_BYTE(0x2C);

  // SET_GAMMA1
  ISSUE_CMD_BYTE(0xF0);
  ISSUE_DATA_BYTE(0x85);
  ISSUE_DATA_BYTE(0x0C);
  ISSUE_DATA_BYTE(0x09);
  ISSUE_DATA_BYTE(0x07);
  ISSUE_DATA_BYTE(0x03);
  ISSUE_DATA_BYTE(0x33);

  // SET_GAMMA3
  ISSUE_CMD_BYTE(0xF2);
  ISSUE_DATA_BYTE(0x85);
  ISSUE_DATA_BYTE(0x0C);
  ISSUE_DATA_BYTE(0x09);
  ISSUE_DATA_BYTE(0x07);
  ISSUE_DATA_BYTE(0x03);
  ISSUE_DATA_BYTE(0x33);

  // SET_GAMMA2
  ISSUE_CMD_BYTE(0xF1);
  ISSUE_DATA_BYTE(0x4B);
  ISSUE_DATA_BYTE(0x72);
  ISSUE_DATA_BYTE(0x91);
  ISSUE_DATA_BYTE(0x34);
  ISSUE_DATA_BYTE(0x3E);
  ISSUE_DATA_BYTE(0x3F);

  // SET_GAMMA4
  ISSUE_CMD_BYTE(0xF3);
  ISSUE_DATA_BYTE(0x4B);
  ISSUE_DATA_BYTE(0x72);
  ISSUE_DATA_BYTE(0x91);
  ISSUE_DATA_BYTE(0x34);
  ISSUE_DATA_BYTE(0x3E);
  ISSUE_DATA_BYTE(0x3F);

  // TEON: Tearing Effect Line On; V-blanking only
  ISSUE_CMD_BYTE(0x35);
  ISSUE_DATA_BYTE(0x00);

  // Tearing scanline
  ISSUE_CMD_BYTE(0x44);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x0A);
}

void lx240d4508ctp05_rotate(int degrees, display_padding_t* padding) {
#define RGB (1 << 3)
#define ML (1 << 4)  // vertical refresh order
#define MH (1 << 2)  // horizontal refresh order
#define MV (1 << 5)
#define MX (1 << 6)
#define MY (1 << 7)
  // MADCTL: Memory Data Access Control - reference:
  // section 6.2.18 in the GC9307 manual
  uint8_t display_command_parameter = 0;
  switch (degrees) {
    case 0:
      display_command_parameter = 0;
      break;
    case 90:
      display_command_parameter = MV | MX | MH | ML;
      break;
    case 180:
      display_command_parameter = MX | MY | MH | ML;
      break;
    case 270:
      display_command_parameter = MV | MY;
      break;
  }

  display_command_parameter ^= RGB | MY;  // XOR RGB and MY settings

  ISSUE_CMD_BYTE(0x36);
  ISSUE_DATA_BYTE(display_command_parameter);

  // Full 240x320 panel - no window offset in any orientation.
  padding->x = 0;
  padding->y = 0;
}
