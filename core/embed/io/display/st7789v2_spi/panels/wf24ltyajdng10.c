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

// Winstar/AVNet WF24LTYAJDNG10
// 2.4" TFT, 240(RGB)x320, controller ILI9341V, connected via 4-wire 8-bit
// serial (SPI) interface (IM[2:0] = 1,1,0 - same encoding and, on this
// board, the same physical RESET/D-C/SPI2/IM[2:0] pins as the
// mi0240agt5cp1f sibling panel - see devkit.h and
// wf24ltyajdng10_select_interface_mode below). Module also carries a CF1124
// I2C capacitive touch controller (see the datasheet's CTP FPC pinout); that
// is out of scope here - this file only covers the display half.
//
// Unlike mi0240agt5cp1f/mi0200aet1, this panel's controller is ILI9341V, not
// ST7789V2. It nonetheless lives in st7789v2_spi/panels/ and reuses that
// family's shared display_driver.c core: st7789v2_cmd/st7789v2_data/
// st7789v2_data1 are electrically generic 4-wire-SPI transport helpers (bit-
// banged CS/DC + HAL_SPI_Transmit) with no ST7789V2-specific behavior, and
// the basic MIPI-DCS commands both controllers share (SLPOUT, MADCTL,
// COLMOD, CASET, RASET, RAMWR, DISPON) happen to use identical opcodes on
// both - see ST7789V2_* in ../display_driver.h, reused as-is below. The
// extended/power/gamma register range (0xB0-0xE1) has different addresses
// and meanings on ILI9341V, so this file defines its own ILI9341_* command
// macros for those rather than reusing the ST7789V2_* ones.
//
// Register sequence transcribed verbatim from the manufacturer-supplied
// reference init code (datasheet "WF24LTYAJDNG0#.pdf", section 15,
// "ILI9341_WF28J") - same command order, same values, including MADCTL
// (0x48) - see NOTE below on why, unlike the mi0240agt5cp1f/mi0200aet1
// ST7789V2 siblings, this panel needs no MADCTL deviation from the
// reference, and instead needs a software pixel byte-swap in the shared
// core (display_driver.c's display_sync_with_fb()).
//
// NOTE on byte order: this panel's controller (ILI9341V) expects each
// 16bpp pixel as high-byte-first (R4-R0,G5-G3 then G2-G0,B4-B0 - datasheet
// section 7.6.2, 4-line Serial Interface), but display_sync_with_fb() sends
// drv->framebuf's bytes as-is, and our framebuffer stores native
// little-endian uint16_t pixels (low byte first in memory) - the opposite
// order. Unlike the ST7789V2 siblings, where a RAMCTRL.ENDIAN=1 write fixes
// this exact mismatch (see their file header NOTEs), ILI9341V's analogous
// control - Interface Control (0xF6), ENDIAN bit (3rd parameter, D5) - is
// documented as valid "only [for] 65K 8-bit and 9-bit MCU interface mode"
// (datasheet section 8.3.28), i.e. the *parallel* interface; this panel is
// wired for the 4-line 8-bit *serial* interface (see
// wf24ltyajdng10_select_interface_mode below), where ENDIAN has no effect.
// This was confirmed on real hardware in two stages: an IFCTL ENDIAN=1
// write (mirroring the ST7789V2 fix) plus clearing MADCTL_BGR (0x48->0x40)
// only partially fixed solid-color test fills, changing a 3-way channel
// rotation ("RGB shows as BRG") into a 2-channel swap with R merely
// coincidentally correct ("RGB shows as RBG") - i.e. the IFCTL write was
// doing nothing, and MADCTL_BGR (a simple R/B swap) cannot by itself
// correct what is actually a byte-order fault, not a channel-routing one.
// The real fix is a genuine byte-swap done in software - see
// display_sync_with_fb() in display_driver.c, gated on
// DISPLAY_PANEL_WF24LTYAJDNG10. With that in place, the reference's MADCTL
// value (0x48, MADCTL_MX | MADCTL_BGR) is correct as-is and does not need
// touching - see wf24ltyajdng10_rotate below, which carries MADCTL_BGR
// through for the same reason.
//
// CASET/RASET (0..239 / 0..319) are already part of the reference sequence
// (unlike the ST7789V2 siblings' references, which omitted them and needed
// them added) - transcribed as-is below.
//
// The reference's SLPOUT + 150ms delay (before any register write) and
// final DISPON (after the last register write) are handled by the shared
// core in display_driver.c, which calls PANEL_INIT_SEQ() (this file) between
// them - see display_init() there. Unlike the ST7789V2 siblings, the
// ILI9341V reference has no INVON - this panel is not display-inverted.
//
// The reference also writes COLMOD (0x3A) and Gamma Set (0x26) twice - once
// right after SLPOUT, once again later in the ILI9341V-specific block - both
// reproduced here exactly as given, redundant as it looks (the shared core
// in display_driver.c only issues SLPOUT itself; both COLMOD/Gamma Set
// writes are this file's responsibility).

#pragma GCC optimize ("O0")

#include <trezor_bsp.h>
#include <trezor_model.h>

#include "wf24ltyajdng10.h"

// ILI9341V-specific command opcodes not shared with ST7789V2 (see file
// header comment above). Names/functions per the ILI9341 datasheet register
// map; comments in "quotes" are the reference code's own (sometimes
// ST7789V2-style-mislabeled, e.g. 0xB0) comments, kept for traceability.
#define ILI9341_GAMSET 0x26     // Gamma Set
#define ILI9341_IFCTL_B0 0xB0   // "Porch Setting" per reference; actually
                                // RGB Interface Signal Control per the
                                // ILI9341 register map
#define ILI9341_FRMCTR1 0xB1    // Frame Rate Control (Normal Mode/Full Colors)
#define ILI9341_DFUNCTR 0xB6    // Display Function Control
#define ILI9341_ETMOD 0xB7      // Entry Mode Set
#define ILI9341_PWCTR1 0xC0     // Power Control 1 (GVDD)
#define ILI9341_PWCTR2 0xC1     // Power Control 2 (AVDD/VGH/VGL)
#define ILI9341_VMCTR1 0xC5     // VCOM Control 1 (VCOMH/VCOML)
#define ILI9341_VMCTR2 0xC7     // VCOM Control 2
#define ILI9341_WRCABC 0x55     // Write Content Adaptive Brightness Control
                                // and Color Enhancement
#define ILI9341_TEOFF 0x34      // Tearing Effect Line OFF
#define ILI9341_TEON 0x35       // Tearing Effect Line ON
#define ILI9341_GMCTRP1 0xE0    // Positive Gamma Correction
#define ILI9341_GMCTRN1 0xE1    // Negative Gamma Correction

void wf24ltyajdng10_select_interface_mode(void) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = 0;

  // IM[2:0] = 1,1,0 selects the 4-line (4-wire 8-bit) serial I/F. The
  // WF24LTYAJDNG10 module datasheet's own pin table (section 10.1) only
  // names IM0/IM1/IM2 generically as "Select the MCU interface mode" and
  // gives no truth table for serial mode (it states IM[2:0]="000"/"001" for
  // 8/16-bit parallel only, and only exposes 3 IM pins - no IM3, presumably
  // tied off internally on the module). The generic ILI9341 controller
  // datasheet (section 7.1.8 "Serial Interface") gives the actual table:
  // IM[3:0] = 0110 or 1110 both select the 4-line serial interface, i.e.
  // IM3 is don't-care and IM[2:0] = "1,1,0" either way.
  //
  // The board's DISPLAY_SPI_IM0_PIN/DISPLAY_SPI_IM2_PIN were originally
  // physically swapped relative to the mi0240agt5cp1f sibling's assumption
  // (measured at the display connector: PD14 = panel IM2, PD5 = panel IM0),
  // requiring the levels below to be written swapped to compensate. The
  // board has since been rewired so DISPLAY_SPI_IM0_PIN/DISPLAY_SPI_IM2_PIN
  // reach the panel's IM0/IM2 inputs directly, same as mi0240agt5cp1f - so
  // this now writes IM2=1, IM1=1, IM0=0 straight, no compensation needed.
  // Latched at reset, so must be driven to their final level before the
  // reset pulse in display_init().
  GPIO_InitStructure.Pin = DISPLAY_SPI_IM0_PIN;
  HAL_GPIO_WritePin(DISPLAY_SPI_IM0_PORT, DISPLAY_SPI_IM0_PIN,
                    GPIO_PIN_RESET);
  HAL_GPIO_Init(DISPLAY_SPI_IM0_PORT, &GPIO_InitStructure);

  GPIO_InitStructure.Pin = DISPLAY_SPI_IM1_PIN;
  HAL_GPIO_WritePin(DISPLAY_SPI_IM1_PORT, DISPLAY_SPI_IM1_PIN, GPIO_PIN_SET);
  HAL_GPIO_Init(DISPLAY_SPI_IM1_PORT, &GPIO_InitStructure);

  GPIO_InitStructure.Pin = DISPLAY_SPI_IM2_PIN;
  HAL_GPIO_WritePin(DISPLAY_SPI_IM2_PORT, DISPLAY_SPI_IM2_PIN, GPIO_PIN_SET);
  HAL_GPIO_Init(DISPLAY_SPI_IM2_PORT, &GPIO_InitStructure);
}

// Verbatim transcription of the datasheet's section 15 reference init code
// ("ILI9341_WF28J") - see the file header comment above.
void wf24ltyajdng10_init_seq(display_driver_t *drv) {
  // Interface Pixel Format: 16 bits/pixel (RGB565). Reference writes this
  // right after SLPOUT, before Gamma Set and the ILI9341V-specific register
  // block below - unlike SLPOUT itself (handled by the shared core in
  // display_driver.c), this first COLMOD write is panel-specific and must be
  // issued here.
  st7789v2_cmd(drv, ST7789V2_COLMOD);
  st7789v2_data1(drv, 0x55);

  // Gamma Set. Reference writes this right after SLPOUT/COLMOD, before the
  // ILI9341V-specific register block below - see file header comment.
  st7789v2_cmd(drv, ILI9341_GAMSET);
  st7789v2_data1(drv, 0x01);

  // "Porch Setting" (0xB0) - see ILI9341_IFCTL_B0 comment above.
  st7789v2_cmd(drv, ILI9341_IFCTL_B0);
  st7789v2_data1(drv, 0x80 | (1 << 0) | (1 << 1));

  // Frame Rate Control (Normal Mode/Full Colors)
  st7789v2_cmd(drv, ILI9341_FRMCTR1);
  {
    static const uint8_t d[2] = {0x00, 0x1B};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Display Function Control
  st7789v2_cmd(drv, ILI9341_DFUNCTR);
  {
    static const uint8_t d[4] = {0x0A, 0x02, 0x27, 0x04};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Entry Mode Set
  st7789v2_cmd(drv, ILI9341_ETMOD);
  st7789v2_data1(drv, 0x06);

  // Power Control 1 (GVDD)
  st7789v2_cmd(drv, ILI9341_PWCTR1);
  st7789v2_data1(drv, 0x35);

  // Power Control 2 (AVDD/VGH/VGL)
  st7789v2_cmd(drv, ILI9341_PWCTR2);
  st7789v2_data1(drv, 0x10);

  // VCOM Control 1 (VCOMH/VCOML)
  st7789v2_cmd(drv, ILI9341_VMCTR1);
  {
    static const uint8_t d[2] = {0x20, 0x21};
    st7789v2_data(drv, d, sizeof(d));
  }

  // VCOM Control 2
  st7789v2_cmd(drv, ILI9341_VMCTR2);
  st7789v2_data1(drv, 0x80 | 0x40);

  // Write Content Adaptive Brightness Control and Color Enhancement
  st7789v2_cmd(drv, ILI9341_WRCABC);
  st7789v2_data1(drv, 0x90);

  // Tearing Effect Line OFF, then ON with mode parameter. Reference issues
  // both back to back (0x34 with no data, then 0x35 with data 0x01).
  st7789v2_cmd(drv, ILI9341_TEOFF);
  st7789v2_cmd(drv, ILI9341_TEON);
  st7789v2_data1(drv, 0x01);

  // Memory Data Access Control (MADCTL): 0x48 (MADCTL_MX | MADCTL_BGR),
  // matching the reference verbatim - see file header NOTE above on why the
  // color-order fault is actually a byte-order problem fixed elsewhere (in
  // display_sync_with_fb(), display_driver.c), not a MADCTL/channel-routing
  // one. See wf24ltyajdng10_rotate below for the 90/180/270 derivation.
  st7789v2_cmd(drv, ST7789V2_MADCTL);
  st7789v2_data1(drv, MADCTL_MX | MADCTL_BGR);

  // Interface Pixel Format: 16 bits/pixel (RGB565). Reference writes this a
  // second time here (already set once right after SLPOUT, above) - see
  // file header comment.
  st7789v2_cmd(drv, ST7789V2_COLMOD);
  st7789v2_data1(drv, 0x55);

  // Gamma Set - reference writes this a second time here too.
  st7789v2_cmd(drv, ILI9341_GAMSET);
  st7789v2_data1(drv, 0x01);

  // Positive Gamma Correction
  st7789v2_cmd(drv, ILI9341_GMCTRP1);
  {
    static const uint8_t d[15] = {0x0F, 0x35, 0x31, 0x0B, 0x0E, 0x06, 0x49,
                                  0xA7, 0x33, 0x07, 0x0F, 0x03, 0x0C, 0x0A,
                                  0x00};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Negative Gamma Correction
  st7789v2_cmd(drv, ILI9341_GMCTRN1);
  {
    static const uint8_t d[15] = {0x00, 0x0A, 0x0F, 0x04, 0x11, 0x08, 0x36,
                                  0x58, 0x4D, 0x07, 0x10, 0x0C, 0x32, 0x34,
                                  0x0F};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Column Address Set: 0 .. 239 / Row Address Set: 0 .. 319. Already part
  // of the reference sequence (unlike the ST7789V2 siblings) - see file
  // header comment.
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

  // No INVON here, unlike the ST7789V2 siblings - the ILI9341V reference
  // does not invert this panel. display_driver.c issues DISPON right after
  // this function returns.
}

void wf24ltyajdng10_rotate(display_driver_t *drv, int angle) {
  // The reference init code only demonstrates the 0-degree (default)
  // orientation above; it gives no data for 90/180/270. These follow the
  // same "textbook" rotation table used by the ST7789V2 siblings (0=none,
  // 90=MV|MX, 180=MX|MY, 270=MV|MY - see e.g. Adafruit_ILI9341/
  // Adafruit_ST7789), which happens to use identical MADCTL bit positions on
  // both controllers. MADCTL_BGR is carried through at every angle, matching
  // the reference's MADCTL value in wf24ltyajdng10_init_seq above - see the
  // NOTE in the file header comment.
  uint8_t madctl = MADCTL_BGR;
  switch (angle) {
    case 90:
      madctl |= MADCTL_MV | MADCTL_MX;
      break;
    case 180:
      madctl |= MADCTL_MX | MADCTL_MY;
      break;
    case 270:
      madctl |= MADCTL_MV | MADCTL_MY;
      break;
    default:
      break;
  }

  st7789v2_cmd(drv, ST7789V2_MADCTL);
  st7789v2_data1(drv, madctl);
}
