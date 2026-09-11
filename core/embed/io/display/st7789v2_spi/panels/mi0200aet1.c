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
// Register sequence transcribed verbatim from the manufacturer-supplied
// reference init code ("MI0200AET-1 Initialization Code.txt", AVNet/
// Multi-Inno) - same command order, same values, including MADCTL, with one
// deliberate deviation on RAMCTRL - see NOTE below. It also writes an
// undocumented register, 0xD6 - not listed anywhere in the ST7789V2
// datasheet (confirmed by full-text search), so presumably a manufacturer/
// factory-test register - reproduced here as-is since the reference does so
// unconditionally.
//
// NOTE: unlike the reference (which never writes RAMCTRL (0xB0) at all,
// leaving it at the ST7789V2 silicon reset default), this file now writes
// RAMCTRL = {0x00, 0xC8} explicitly - confirmed on real hardware: this panel
// showed the same color-channel-swap/gradient-stripe pattern as the
// mi0240agt5cp1f sibling before its own RAMCTRL fix (see that panel's file
// header NOTE), because ENDIAN was left at its reset default of 0 (Big
// Endian), which mismatches our framebuf's native little-endian uint16_t
// pixel storage - see display_sync_with_fb() (display_driver.c). 0x00 for
// the 1st parameter (RM=0/DM=00, MCU interface) matches the silicon reset
// default already in effect - this panel's pixel writes were reaching GRAM
// fine, only the byte order was wrong - so only ENDIAN (2nd parameter,
// 0x00->0xC8) is an actual behavior change here.
//
// CASET/RASET (setting the full 0..239 / 0..319 addressing window) are the
// one addition beyond the reference: the reference never sets an address
// window at init at all, but display_sync_with_fb() in display_driver.c
// relies on the window already covering the full frame buffer before every
// RAMWR, so it must be set exactly once, and here is the natural place.
//
// The reference's SLPOUT + 120ms delay (before any register write) and
// final INVON+DISPON (after the last register write) are handled by the
// shared core in display_driver.c, which calls PANEL_INIT_SEQ() (this file)
// between them - see display_init() there. INVON below is kept as the last
// command in this sequence, immediately before display_driver.c issues
// DISPON, to preserve the reference's exact command order.

#pragma GCC optimize ("O0")

#include <trezor_bsp.h>
#include <trezor_model.h>

#include "mi0200aet1.h"

// Undocumented ST7789V2 register written unconditionally by the reference
// init code - not in the ST7789V2 datasheet's register map (confirmed via
// full-text search), likely a manufacturer/factory-test register. Named
// after its raw command byte since no datasheet name exists.
#define ST7789V2_UNDOCUMENTED_0xD6 0xD6

// Verbatim transcription of "MI0200AET-1 Initialization Code.txt" - see the
// file header comment above.
void mi0200aet1_init_seq(display_driver_t *drv) {
  // Porch Setting
  st7789v2_cmd(drv, ST7789V2_PORCTRL);
  {
    static const uint8_t d[5] = {0x0C, 0x0C, 0x00, 0x33, 0x33};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Memory Data Access Control (MADCTL): reference default - RGB panel
  // (BGR bit clear), no mirror/rotation. NOT yet verified against real
  // hardware (the reference is a single fixed-orientation demo); see
  // mi0200aet1_rotate below for the 90/180/270 derivation.
  st7789v2_cmd(drv, ST7789V2_MADCTL);
  st7789v2_data1(drv, 0x00);

  // Interface Pixel Format: 16 bits/pixel (RGB565)
  st7789v2_cmd(drv, ST7789V2_COLMOD);
  st7789v2_data1(drv, 0x55);

  // Column Address Set: 0 .. 239 / Row Address Set: 0 .. 319. Not part of
  // the reference sequence - see file header comment above.
  st7789v2_cmd(drv, ST7789V2_CASET);
  {
    static const uint8_t d[4] = {0x00, 0x00, 0x00, 0xEF};
    st7789v2_data(drv, d, sizeof(d));
  }
  st7789v2_cmd(drv, ST7789V2_RASET);
  {
    static const uint8_t d[4] = {0x00, 0x00, 0x01, 0x3F};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Gate Control
  st7789v2_cmd(drv, ST7789V2_GCTRL);
  st7789v2_data1(drv, 0x62);

  // VCOM Setting
  st7789v2_cmd(drv, ST7789V2_VCOMS);
  st7789v2_data1(drv, 0x31);

  // LCMCTRL: LCM Control
  st7789v2_cmd(drv, ST7789V2_LCMCTRL);
  st7789v2_data1(drv, 0x2C);

  // VDV and VRH Command Enable
  st7789v2_cmd(drv, ST7789V2_VDVVRHEN);
  st7789v2_data1(drv, 0x01);

  // VRH Set
  st7789v2_cmd(drv, ST7789V2_VRHS);
  st7789v2_data1(drv, 0x00);

  // VDV Setting
  st7789v2_cmd(drv, ST7789V2_VDVS);
  st7789v2_data1(drv, 0x20);

  // Frame Rate Control in Normal Mode (column inversion)
  st7789v2_cmd(drv, ST7789V2_FRCTRL2);
  st7789v2_data1(drv, 0x0F);

  // RAM Control. {0x00, 0xC8}, NOT part of the reference sequence at all -
  // see file header NOTE above: 0x00 keeps RM=0/DM=00 (MCU interface, the
  // silicon reset default already in effect), and 0xC8 sets ENDIAN=1 (Little
  // Endian) to match our framebuf's native little-endian pixel storage - see
  // display_sync_with_fb() in display_driver.c.
  st7789v2_cmd(drv, ST7789V2_RAMCTRL);
  {
    static const uint8_t d[2] = {0x00, 0xC8};
    st7789v2_data(drv, d, sizeof(d));
  }

  // PWCTRL1: Power Control 1
  st7789v2_cmd(drv, ST7789V2_PWCTRL1);
  {
    static const uint8_t d[2] = {0xA4, 0xA1};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Undocumented register - see #define comment above.
  st7789v2_cmd(drv, ST7789V2_UNDOCUMENTED_0xD6);
  st7789v2_data1(drv, 0xA1);

  // Positive voltage gamma correction
  st7789v2_cmd(drv, ST7789V2_PVGAMCTRL);
  {
    static const uint8_t d[14] = {0xF0, 0x00, 0x06, 0x0F, 0x10, 0x3D, 0x2D,
                                  0x44, 0x40, 0x3F, 0x1C, 0x19, 0x13, 0x15};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Negative voltage gamma correction
  st7789v2_cmd(drv, ST7789V2_NVGAMCTRL);
  {
    static const uint8_t d[14] = {0xF0, 0x00, 0x00, 0x03, 0x04, 0x02, 0x2D,
                                  0x44, 0x40, 0x08, 0x14, 0x15, 0x11, 0x17};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Display Inversion On (panel is normally black). Last command in the
  // reference sequence, immediately before DISPON - which display_driver.c
  // issues right after this function returns.
  st7789v2_cmd(drv, ST7789V2_INVON);
}

void mi0200aet1_rotate(display_driver_t *drv, int angle) {
  // The reference init code only demonstrates the 0-degree (default)
  // orientation above; it gives no data for 90/180/270. These follow the
  // "textbook" ST7789V2 rotation table (0=none, 90=MV|MX, 180=MX|MY,
  // 270=MV|MY - see e.g. Adafruit_ST7789). NOT yet verified against real
  // hardware - the previous "0/180 swapped" hack this replaces was tuned
  // against an MX-based default borrowed from the mi0240agt5cp1f sibling,
  // which no longer applies now that the default matches this panel's own
  // reference (0x00, no MX).
  uint8_t madctl = 0x00;
  switch (angle) {
    case 90:
      madctl = MADCTL_MV | MADCTL_MX;
      break;
    case 180:
      madctl = MADCTL_MX | MADCTL_MY;
      break;
    case 270:
      madctl = MADCTL_MV | MADCTL_MY;
      break;
    default:
      break;
  }

  st7789v2_cmd(drv, ST7789V2_MADCTL);
  st7789v2_data1(drv, madctl);
}
