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

// AVNet (Multi-Inno) MI0200AET-1 (+ MI0240EGP-C1_OB adapter board)
// 2.0" TFT, 240(RGB)x320, controller ST7789V2, connected via 4-wire SPI.
//
// Electrically pin-compatible with MI0240AGT-5CP1-F on this board: RESET,
// D/C and the SPI2 bus pins are all wired identically (see devkit.h) and
// reused as-is via the shared st7789v2_spi display_driver.c core. The one
// hardware difference is that this module's IM[2:0] mode-select pins are
// not routed to the MCU at all ("no IM pins used" per the pinout this
// driver was written against) - presumably strapped to the correct level on
// the MI0240EGP-C1_OB adapter board itself - so unlike the sibling panel,
// this one has no _select_interface_mode() hook (see mi0200aet1.h).
//
// Register sequence carried over unmodified from mi0240agt5cp1f (same
// ST7789V2 controller, same 240x320 resolution). Checked against the
// module's own datasheet (MI0200AET-1 Ver 1.3, Multi-Inno): it confirms the
// ST7789V2 controller, the 240x320 resolution, 4-wire SPI, and the 4-LED
// (common-anode, 4 cathodes LEDK1-4) backlight already wired on this board
// via BACKLIGHT_PWM_* (see devkit.h) - but, like the sibling panel's
// datasheet, it does not publish a register init table, so it can't
// independently confirm the gamma/VCOM/porch/inversion values below, nor the
// MADCTL orientation bits (carried over from the sibling panel and NOT yet
// verified against this panel's own glass - it may scan differently). These
// values remain a reasonable starting point pending validation on real
// hardware.

#pragma GCC optimize ("O0")

#include <trezor_bsp.h>
#include <trezor_model.h>

#include "mi0200aet1.h"

// Register values below are carried over unmodified from the mi0240agt5cp1f
// sibling panel (same ST7789 controller family, same 240x320 resolution) -
// see comment at the top of this file. Gamma / VCOM / porch / inversion
// values, and the MADCTL orientation bits, may need tuning against this
// panel's own real hardware.
void mi0200aet1_init_seq(display_driver_t *drv) {
  // Memory Data Access Control (MADCTL): default orientation. Carried over
  // from the mi0240agt5cp1f sibling panel as a starting point - NOT yet
  // verified against this panel's own glass, which may scan differently.
  // See the matching 0/180 swap in mi0200aet1_rotate() below.
  st7789v2_cmd(drv, ST7789V2_MADCTL);
  st7789v2_data1(drv, MADCTL_MX);

  // Interface Pixel Format: 16 bits/pixel (RGB565)
  st7789v2_cmd(drv, ST7789V2_COLMOD);
  st7789v2_data1(drv, 0x05);

  // RAM Control: set ENDIAN=1 (Little Endian, D3 of 2nd parameter). Our
  // framebuffer stores each RGB565 pixel as a native little-endian uint16_t
  // and display_sync_with_fb() sends its bytes as-is (low byte first), but
  // the controller's power-on default (ENDIAN=0) expects the high byte
  // first - see the mi0240agt5cp1f sibling panel, where this was the root
  // cause of a color-channel-swap and gradient-stripe bug on the same
  // controller. 1st parameter 0x00 selects RM=0 (RAM access from MCU
  // interface) / DM=00 (MCU interface mode) - both already the reset
  // default, spelled out here since they must accompany the 2nd parameter in
  // the same command. See ST7789V2 datasheet section 9.2.1, "RAMCTRL (B0h):
  // RAM Control".
  st7789v2_cmd(drv, ST7789V2_RAMCTRL);
  {
    static const uint8_t d[2] = {0x00, 0xC8};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Column Address Set: 0 .. 239
  st7789v2_cmd(drv, ST7789V2_CASET);
  {
    static const uint8_t d[4] = {0x00, 0x00, 0x00, 0xEF};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Row Address Set: 0 .. 319
  st7789v2_cmd(drv, ST7789V2_RASET);
  {
    static const uint8_t d[4] = {0x00, 0x00, 0x01, 0x3F};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Porch Setting
  st7789v2_cmd(drv, ST7789V2_PORCTRL);
  {
    static const uint8_t d[5] = {0x0C, 0x0C, 0x00, 0x33, 0x33};
    st7789v2_data(drv, d, sizeof(d));
  }

  // VCOM Setting
  st7789v2_cmd(drv, ST7789V2_VCOMS);
  st7789v2_data1(drv, 0x1F);

  // LCMCTRL: LCM Control
  st7789v2_cmd(drv, ST7789V2_LCMCTRL);
  st7789v2_data1(drv, 0x20);

  // VDV and VRH Command Enable
  st7789v2_cmd(drv, ST7789V2_VDVVRHEN);
  st7789v2_data1(drv, 0x01);

  // VRH Set (4.3V)
  st7789v2_cmd(drv, ST7789V2_VRHS);
  st7789v2_data1(drv, 0x0F);

  // VDV Setting
  st7789v2_cmd(drv, ST7789V2_VDVS);
  st7789v2_data1(drv, 0x20);

  // Frame Rate Control in Normal Mode (column inversion)
  st7789v2_cmd(drv, ST7789V2_FRCTRL2);
  st7789v2_data1(drv, 0xEF);

  // Display Inversion On (panel is normally black)
  st7789v2_cmd(drv, ST7789V2_INVON);

  // PWCTRL1: Power Control 1
  st7789v2_cmd(drv, ST7789V2_PWCTRL1);
  {
    static const uint8_t d[2] = {0xA4, 0xA1};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Positive voltage gamma correction
  st7789v2_cmd(drv, ST7789V2_PVGAMCTRL);
  {
    static const uint8_t d[14] = {0xD0, 0x0A, 0x10, 0x0A, 0x0A, 0x26, 0x36,
                                  0x34, 0x4D, 0x18, 0x13, 0x14, 0x2F, 0x34};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Negative voltage gamma correction
  st7789v2_cmd(drv, ST7789V2_NVGAMCTRL);
  {
    static const uint8_t d[14] = {0xD0, 0x0A, 0x10, 0x0A, 0x09, 0x26, 0x36,
                                  0x53, 0x4C, 0x18, 0x14, 0x14, 0x2F, 0x34};
    st7789v2_data(drv, d, sizeof(d));
  }
}

void mi0200aet1_rotate(display_driver_t *drv, int angle) {
  // Carried over from the mi0240agt5cp1f sibling panel as a starting point
  // (0/180 swapped relative to the "textbook" ST7789V2 bits) - NOT yet
  // verified against this panel's own glass, which may scan differently.
  // See mi0200aet1_init_seq() above.
  uint8_t madctl = 0;
  switch (angle) {
    case 90:
      madctl = MADCTL_MV | MADCTL_MX;
      break;
    case 180:
      madctl = MADCTL_MY;
      break;
    case 270:
      madctl = MADCTL_MV | MADCTL_MY;
      break;
    default:
      madctl = MADCTL_MX;
      break;
  }

  st7789v2_cmd(drv, ST7789V2_MADCTL);
  st7789v2_data1(drv, madctl);
}
