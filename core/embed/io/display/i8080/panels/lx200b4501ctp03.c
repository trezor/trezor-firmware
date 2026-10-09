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
#include "lx200b4501ctp03.h"

#define MADCTL_MY (1U << 7U)   // Row Address Order
#define MADCTL_MX (1U << 6U)   // Column Address Order
#define MADCTL_MV (1U << 5U)   // Row / Column Exchange
#define MADCTL_ML (1U << 4U)   // Vertical Refresh Order
#define MADCTL_BGR (1U << 3U)  // RGB-BGR Order
#define MADCTL_MH (1U << 2U)   // Horizontal Refresh Order

#define MADCTL_DEFAULT (MADCTL_MX | MADCTL_BGR | MADCTL_MH)

void lx200b4501ctp03_init_seq(void) {
  // Inter Register Enable1 / Enable2
  ISSUE_CMD_BYTE(0xFE);
  ISSUE_CMD_BYTE(0xEF);

  ISSUE_CMD_BYTE(0x36);
  ISSUE_DATA_BYTE(MADCTL_DEFAULT);

  // COLMOD: Interface Pixel format; 65K color: 16-bit/pixel (RGB 5-6-5 bits
  // input)
  ISSUE_CMD_BYTE(0x3A);
  ISSUE_DATA_BYTE(0x05);

  ISSUE_CMD_BYTE(0x86);
  ISSUE_DATA_BYTE(0x98);

  ISSUE_CMD_BYTE(0x89);
  ISSUE_DATA_BYTE(0x13);

  ISSUE_CMD_BYTE(0x8B);
  ISSUE_DATA_BYTE(0x80);

  ISSUE_CMD_BYTE(0x8D);
  ISSUE_DATA_BYTE(0x33);

  ISSUE_CMD_BYTE(0x8E);
  ISSUE_DATA_BYTE(0x0F);

  // Frame Rate
  ISSUE_CMD_BYTE(0xE8);
  ISSUE_DATA_BYTE(0x13);
  ISSUE_DATA_BYTE(0x00);

  ISSUE_CMD_BYTE(0xEC);
  ISSUE_DATA_BYTE(0x33);
  ISSUE_DATA_BYTE(0x07);
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

  // Power Control 2
  ISSUE_CMD_BYTE(0xC3);
  ISSUE_DATA_BYTE(0x1A);

  // Power Control 3
  ISSUE_CMD_BYTE(0xC4);
  ISSUE_DATA_BYTE(0x30);

  // Power Control 4
  ISSUE_CMD_BYTE(0xC9);
  ISSUE_DATA_BYTE(0x2F);

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
  ISSUE_DATA_BYTE(0x15);
  ISSUE_DATA_BYTE(0x17);
  ISSUE_DATA_BYTE(0x07);
  ISSUE_DATA_BYTE(0x09);
  ISSUE_DATA_BYTE(0x07);
  ISSUE_DATA_BYTE(0x32);

  // SET_GAMMA3
  ISSUE_CMD_BYTE(0xF2);
  ISSUE_DATA_BYTE(0x15);
  ISSUE_DATA_BYTE(0x17);
  ISSUE_DATA_BYTE(0x07);
  ISSUE_DATA_BYTE(0x09);
  ISSUE_DATA_BYTE(0x07);
  ISSUE_DATA_BYTE(0x3B);

  // SET_GAMMA2
  ISSUE_CMD_BYTE(0xF1);
  ISSUE_DATA_BYTE(0x45);
  ISSUE_DATA_BYTE(0x8E);
  ISSUE_DATA_BYTE(0x95);
  ISSUE_DATA_BYTE(0x28);
  ISSUE_DATA_BYTE(0x2A);
  ISSUE_DATA_BYTE(0x7F);

  // SET_GAMMA4
  ISSUE_CMD_BYTE(0xF3);
  ISSUE_DATA_BYTE(0x4E);
  ISSUE_DATA_BYTE(0x8E);
  ISSUE_DATA_BYTE(0x95);
  ISSUE_DATA_BYTE(0x28);
  ISSUE_DATA_BYTE(0x2A);
  ISSUE_DATA_BYTE(0x7F);

  // TEON: Tearing Effect Line On; V-blanking only
  ISSUE_CMD_BYTE(0x35);
  ISSUE_DATA_BYTE(0x00);

  // Tearing scanline
  ISSUE_CMD_BYTE(0x44);
  ISSUE_DATA_BYTE(0x00);
  ISSUE_DATA_BYTE(0x0A);
}

void lx200b4501ctp03_rotate(int degrees, display_padding_t* padding) {
  uint8_t madctl_val = MADCTL_DEFAULT;

  switch (degrees) {
    case 0:
      // Nothing to change.
      break;
    case 90:
      madctl_val ^= (MADCTL_MV | (MADCTL_MX | MADCTL_MH));
      break;
    case 180:
      madctl_val ^= ((MADCTL_MY | MADCTL_ML) | (MADCTL_MX | MADCTL_MH));
      break;
    case 270:
      madctl_val ^= (MADCTL_MV | (MADCTL_MY | MADCTL_ML));
      break;
  }

  ISSUE_CMD_BYTE(0x36);
  ISSUE_DATA_BYTE(madctl_val);

  // Full 240x320 panel - no window offset in any orientation.
  padding->x = 0;
  padding->y = 0;
}
