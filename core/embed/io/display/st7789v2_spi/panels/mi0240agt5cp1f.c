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

// AVNet (Multi-Inno) MI0240AGT-5CP1-F
// 2.4" TFT, 240(RGB)x320, controller ST7789V2, connected via 4-line 8-bit
// serial (SPI) interface (IM[2:0] = 1,1,0).
//
// Register sequence transcribed verbatim from the manufacturer-supplied
// reference init code ("MI0240AGT-5 Initialization Code.txt", AVNet/
// Multi-Inno) - same command order, same values, with two deliberate
// deviations on RAMCTRL and MADCTL - see NOTEs below. CASET/RASET (setting
// the full 0..239 / 0..319 addressing window) are the one other addition
// beyond the reference: the reference never sets an address window at init
// at all, but display_sync_with_fb() in display_driver.c relies on the
// window already covering the full frame buffer before every RAMWR, so it
// must be set exactly once, and here is the natural place.
//
// The reference's SLPOUT + 120ms delay (before any register write) and
// final INVON+DISPON (after the last register write) are handled by the
// shared core in display_driver.c, which calls PANEL_INIT_SEQ() (this file)
// between them - see display_init() there. INVON below is kept as the last
// command in this sequence, immediately before display_driver.c issues
// DISPON, to preserve the reference's exact command order.
//
// NOTE: RAMCTRL is {0x00, 0xC8} here, NOT the reference's verbatim
// {0x11, 0xF0} - two deliberate deviations, both confirmed on real hardware:
//
// 1st parameter 0x00 (reference: 0x11): 0x11 sets RM=1/DM=01 (RAM access
// from the RGB interface - ST7789V2 datasheet section 9.2.1), which
// silently breaks pixel writes on this board: it's wired purely as 4-wire
// SPI (IM[2:0]=1,1,0, no RGB/DE/HSYNC/VSYNC/PCLK lines connected at all),
// so with RM=1 the controller's GRAM is only ever fed from that
// (nonexistent) RGB interface and every RAMWR byte sent over SPI in
// display_sync_with_fb() is a no-op - confirmed as a fully blank screen.
// 0x00 selects RM=0/DM=00 (MCU interface), required for RAMWR-over-SPI to
// reach GRAM at all.
//
// 2nd parameter 0xC8 (reference: 0xF0): sets ENDIAN (D3) = 1, Little
// Endian, to match our framebuf's native little-endian uint16_t pixel
// storage - see display_sync_with_fb() (display_driver.c). The reference's
// 0xF0 (ENDIAN=0, Big Endian) would otherwise expect the MSB of each pixel
// first while getting the LSB, causing a color-channel-swap/gradient-stripe
// pattern (the same failure mode previously seen and fixed on this same
// controller - see git history).
//
// NOTE: MADCTL is 0x00 here, NOT the reference's verbatim MADCTL_BGR
// (0x08) - confirmed on real hardware: with MADCTL_BGR set, the controller
// interprets our RGB565 framebuffer data (standard RGB component order, as
// produced by the rest of the graphics stack) as BGR, swapping red and
// blue on screen. 0x00 (RGB order) matches what this driver's framebuffer
// actually produces - see mi0240agt5cp1f_rotate below, which no longer
// carries MADCTL_BGR through either.

#pragma GCC optimize ("O0")

#include <trezor_bsp.h>
#include <trezor_model.h>

#include "mi0240agt5cp1f.h"

void mi0240agt5cp1f_select_interface_mode(void) {
  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
  GPIO_InitStructure.Alternate = 0;

  // IM[2:0] = 1,1,0 selects 4-line 8-bit serial I/F (ST7789V2 manual,
  // section 6.2). These are latched at reset, so must be driven to their
  // final level before the reset pulse in display_init().
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

// Verbatim transcription of "MI0240AGT-5 Initialization Code.txt" - see the
// file header comment above.
void mi0240agt5cp1f_init_seq(display_driver_t *drv) {
  // Memory Data Access Control (MADCTL): 0x00 (RGB order, no mirror/
  // rotation), NOT the reference's verbatim MADCTL_BGR - see file header
  // NOTE above. See mi0240agt5cp1f_rotate below for the 90/180/270
  // derivation.
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

  // Porch Setting
  st7789v2_cmd(drv, ST7789V2_PORCTRL);
  {
    static const uint8_t d[5] = {0x0C, 0x0C, 0x00, 0x33, 0x33};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Gate Control
  st7789v2_cmd(drv, ST7789V2_GCTRL);
  st7789v2_data1(drv, 0x35);

  // VCOM Setting
  st7789v2_cmd(drv, ST7789V2_VCOMS);
  st7789v2_data1(drv, 0x35);

  // LCMCTRL: LCM Control
  st7789v2_cmd(drv, ST7789V2_LCMCTRL);
  st7789v2_data1(drv, 0x2C);

  // VDV and VRH Command Enable
  st7789v2_cmd(drv, ST7789V2_VDVVRHEN);
  st7789v2_data1(drv, 0x01);

  // VRH Set
  st7789v2_cmd(drv, ST7789V2_VRHS);
  st7789v2_data1(drv, 0x10);

  // VDV Setting
  st7789v2_cmd(drv, ST7789V2_VDVS);
  st7789v2_data1(drv, 0x20);

  // Frame Rate Control in Normal Mode (column inversion)
  st7789v2_cmd(drv, ST7789V2_FRCTRL2);
  st7789v2_data1(drv, 0x0F);

  // RAM Control. {0x00, 0xC8}, NOT the reference's verbatim {0x11, 0xF0} -
  // see file header NOTE above: 0x00 selects RM=0/DM=00 (MCU interface,
  // required for RAMWR-over-SPI to reach GRAM at all on this SPI-only-wired
  // board), and 0xC8 sets ENDIAN=1 (Little Endian) to match our framebuf's
  // native little-endian pixel storage - see display_sync_with_fb() in
  // display_driver.c.
  st7789v2_cmd(drv, ST7789V2_RAMCTRL);
  {
    static const uint8_t d[2] = {0x00, 0xC8};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Frame Rate Control in Idle/Partial Mode ("40 DEmode 60 HV mode" per
  // reference comment)
  st7789v2_cmd(drv, ST7789V2_FRCTRL1);
  {
    static const uint8_t d[3] = {0x40, 0x10, 0x12};
    st7789v2_data(drv, d, sizeof(d));
  }

  // PWCTRL1: Power Control 1
  st7789v2_cmd(drv, ST7789V2_PWCTRL1);
  {
    static const uint8_t d[2] = {0xA4, 0xA1};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Positive voltage gamma correction
  st7789v2_cmd(drv, ST7789V2_PVGAMCTRL);
  {
    static const uint8_t d[14] = {0xD0, 0x00, 0x02, 0x07, 0x0B, 0x1A, 0x31,
                                  0x54, 0x40, 0x29, 0x12, 0x12, 0x12, 0x17};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Negative voltage gamma correction
  st7789v2_cmd(drv, ST7789V2_NVGAMCTRL);
  {
    static const uint8_t d[14] = {0xD0, 0x00, 0x02, 0x07, 0x05, 0x25, 0x2D,
                                  0x44, 0x45, 0x1C, 0x18, 0x16, 0x1C, 0x1D};
    st7789v2_data(drv, d, sizeof(d));
  }

  // Display Inversion On (panel is normally black). Last command in the
  // reference sequence, immediately before DISPON - which display_driver.c
  // issues right after this function returns.
  st7789v2_cmd(drv, ST7789V2_INVON);
}

void mi0240agt5cp1f_rotate(display_driver_t *drv, int angle) {
  // The reference init code only demonstrates the 0-degree (default)
  // orientation above; it gives no data for 90/180/270. These follow the
  // "textbook" ST7789V2 rotation table (0=none, 90=MV|MX, 180=MX|MY,
  // 270=MV|MY - see e.g. Adafruit_ST7789). No MADCTL_BGR here - see the
  // MADCTL NOTE in the file header comment and in mi0240agt5cp1f_init_seq
  // above: this panel's framebuffer data is RGB order, not BGR.
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
