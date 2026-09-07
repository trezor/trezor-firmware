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

#include "../display_io.h"

void _154a_init_seq(void) {
  // most recent manual: https://www.newhavendisplay.com/app_notes/ILI9341.pdf
  // TEON: Tearing Effect Line On; V-blanking only
  ISSUE_CMD_BYTE(0x35);
  ISSUE_DATA_BYTE(0x00);

  // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits
  // input)
  ISSUE_CMD_BYTE(0x3A);
  ISSUE_DATA_BYTE(0x55);

  // Display Function Control: gate scan direction 319 -> 0
  ISSUE_CMD_BYTE(0xB6);
  ISSUE_DATA_BYTE(0x0A);
  ISSUE_DATA_BYTE(0xC2);
  ISSUE_DATA_BYTE(0x27);
  ISSUE_DATA_BYTE(0x00);

  // Interface Control: XOR BGR as ST7789V does
  ISSUE_CMD_BYTE(0xF6);
  ISSUE_DATA_BYTE(0x09);
  ISSUE_DATA_BYTE(0x30);
  ISSUE_DATA_BYTE(0x00);

  // the above config is the most important and definitely necessary

  ISSUE_CMD_BYTE(0xCF);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0xC1);
  ISSUE_DATA_BYTE(0x30);

  ISSUE_CMD_BYTE(0xED);
  ISSUE_DATA_BYTE(0x64);
  ISSUE_DATA_BYTE(0x03);
  ISSUE_DATA_BYTE(0x12);
  ISSUE_DATA_BYTE(0x81);

  ISSUE_CMD_BYTE(0xE8);
  ISSUE_DATA_BYTE(0x85);
  ISSUE_DATA_BYTE(0x10);
  ISSUE_DATA_BYTE(0x7A);

  ISSUE_CMD_BYTE(0xF7);
  ISSUE_DATA_BYTE(0x20);

  ISSUE_CMD_BYTE(0xEA);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x00);

  // power control VRH[5:0]
  ISSUE_CMD_BYTE(0xC0);
  ISSUE_DATA_BYTE(0x23);

  // power control SAP[2:0] BT[3:0]
  ISSUE_CMD_BYTE(0xC1);
  ISSUE_DATA_BYTE(0x12);

  // vcm control 1
  ISSUE_CMD_BYTE(0xC5);
  ISSUE_DATA_BYTE(0x60);
  ISSUE_DATA_BYTE(0x44);

  // vcm control 2
  ISSUE_CMD_BYTE(0xC7);
  ISSUE_DATA_BYTE(0x8A);

  // framerate
  ISSUE_CMD_BYTE(0xB1);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x18);

  // 3 gamma func disable
  ISSUE_CMD_BYTE(0xF2);
  ISSUE_DATA_BYTE(0x00);

  // gamma curve 1
  ISSUE_CMD_BYTE(0xE0);
  ISSUE_DATA_BYTE(0x0F);
  ISSUE_DATA_BYTE(0x2F);
  ISSUE_DATA_BYTE(0x2C);
  ISSUE_DATA_BYTE(0x0B);
  ISSUE_DATA_BYTE(0x0F);
  ISSUE_DATA_BYTE(0x09);
  ISSUE_DATA_BYTE(0x56);
  ISSUE_DATA_BYTE(0xD9);
  ISSUE_DATA_BYTE(0x4A);
  ISSUE_DATA_BYTE(0x0B);
  ISSUE_DATA_BYTE(0x14);
  ISSUE_DATA_BYTE(0x05);
  ISSUE_DATA_BYTE(0x0C);
  ISSUE_DATA_BYTE(0x06);
  ISSUE_DATA_BYTE(0x00);

  // gamma curve 2
  ISSUE_CMD_BYTE(0xE1);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x10);
  ISSUE_DATA_BYTE(0x13);
  ISSUE_DATA_BYTE(0x04);
  ISSUE_DATA_BYTE(0x10);
  ISSUE_DATA_BYTE(0x06);
  ISSUE_DATA_BYTE(0x25);
  ISSUE_DATA_BYTE(0x26);
  ISSUE_DATA_BYTE(0x3B);
  ISSUE_DATA_BYTE(0x04);
  ISSUE_DATA_BYTE(0x0B);
  ISSUE_DATA_BYTE(0x0A);
  ISSUE_DATA_BYTE(0x33);
  ISSUE_DATA_BYTE(0x39);
  ISSUE_DATA_BYTE(0x0F);
}
