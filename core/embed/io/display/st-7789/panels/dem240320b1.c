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

// Display Elektronik DEM240320B1 VTH-PW
// 2.0" transflective TFT, 240(RGB)x320, controller ST7789 (COG).
//
// NOTE: The module datasheet does not provide a register init table, so the
// sequence below is based on the (same-controller) lx154a2482 ST7789 panel
// adapted to the full 240x320 resolution. Gamma / VCOM / porch / inversion
// values are a reasonable starting point and may need tuning against real
// hardware.

#include <trezor_model.h>

#include "../display_io.h"
#include "dem240320b1.h"

void dem240320b1_gamma(void) {
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

void dem240320b1_init_seq(void) {
  // Memory Data Access Control (MADCTL)
  ISSUE_CMD_BYTE(0x36);
  ISSUE_DATA_BYTE(0x00);

  // Interface Pixel Format: 16 bits/pixel (RGB565)
  ISSUE_CMD_BYTE(0x3A);
  ISSUE_DATA_BYTE(0x05);

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
  ISSUE_DATA_BYTE(0xEF);  // column inversion

  // INVON (21h): Display Inversion On (panel is normally black)
  ISSUE_CMD_BYTE(0x21);

  // PWCTRL1: Power Control 1
  ISSUE_CMD_BYTE(0xD0);
  ISSUE_DATA_BYTE(0xA4);
  ISSUE_DATA_BYTE(0xA1);

  dem240320b1_gamma();
}

void dem240320b1_rotate(int degrees, display_padding_t* padding) {
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
      break;
    case 90:
      display_command_parameter = MV | MX;
      break;
    case 180:
      display_command_parameter = MX | MY;
      break;
    case 270:
      display_command_parameter = MV | MY;
      break;
  }

  ISSUE_CMD_BYTE(0x36);
  ISSUE_DATA_BYTE(display_command_parameter);

  // Full 240x320 panel - no window offset in any orientation.
  padding->x = 0;
  padding->y = 0;
}
