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
// Register sequence reused from the (same ST7789 family, same 240x320
// resolution) i8080 dem240320b1 panel - see
// display/i8080/panels/dem240320b1.c. Note that the other panels already
// supported on this board (lx200b4501ctp03, lx240d4508ctp05) are GC9307-based
// despite the superficial similarity, so their register values do not apply
// here.
//
// Checked against the module's own datasheet (MI0240AGT-5CP1-F Ver 1.0,
// Multi-Inno): it confirms the ST7789V2 controller, the 240x320 resolution,
// SPI as a supported interface, and (via the IM[3:0] mode-select table) that
// IM[2:0] = 1,1,0 is indeed 4-line 8-bit serial mode - but, like the
// dem240320b1 module, it does not publish a register init table, so it can't
// independently confirm the gamma/VCOM/porch/inversion values below. The
// ST7789V2 controller datasheet itself only lists generic silicon-reset
// (power-on) defaults for those registers, which are not panel-tuned and are
// not a better source than the values below (borrowed from a same-controller
// panel already tuned against real hardware). No public reference for this
// exact part number exists either. These values remain a reasonable
// starting point pending validation on real hardware.

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

// Register values below are the same as the i8080 dem240320b1 panel (same
// ST7789 controller family, same 240x320 resolution) - see comment at the
// top of this file. Gamma / VCOM / porch / inversion values may need tuning
// against real hardware.
void mi0240agt5cp1f_init_seq(display_driver_t *drv) {
  // Memory Data Access Control (MADCTL): default orientation. This panel's
  // column scan direction is reversed relative to the controller's native
  // (MX=0) reference - MY alone was a true 180-degree rotation of correct
  // (not a mirror), and MX|MY together over-corrected to a horizontal
  // mirror, so MX alone is the "upright" default. See the matching 0/180
  // swap in mi0240agt5cp1f_rotate() below.
  st7789v2_cmd(drv, ST7789V2_MADCTL);
  st7789v2_data1(drv, MADCTL_MX);

  // Interface Pixel Format: 16 bits/pixel (RGB565)
  st7789v2_cmd(drv, ST7789V2_COLMOD);
  st7789v2_data1(drv, 0x05);

  // RAM Control: set ENDIAN=1 (Little Endian, D3 of 2nd parameter). Our
  // framebuffer stores each RGB565 pixel as a native little-endian uint16_t
  // and display_sync_with_fb() sends its bytes as-is (low byte first), but
  // the controller's power-on default (ENDIAN=0) expects the high byte
  // first - that mismatch, not a subpixel wiring/color-order issue, was the
  // actual root cause of the earlier color-channel-swap and gradient-stripe
  // bugs (see git history for the abandoned MADCTL_BGR/software-swap
  // workaround this replaced). 1st parameter 0x00 selects RM=0 (RAM access
  // from MCU interface) / DM=00 (MCU interface mode) - both already the
  // reset default, spelled out here since they must accompany the 2nd
  // parameter in the same command. See ST7789V2 datasheet section 9.2.1,
  // "RAMCTRL (B0h): RAM Control".
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

void mi0240agt5cp1f_rotate(display_driver_t *drv, int angle) {
  // 0/180 are swapped relative to the "textbook" ST7789V2 bits (MX
  // alone / MY alone instead of 0 / MX|MY) to match this panel's
  // reversed column scan direction - see mi0240agt5cp1f_init_seq() above.
  // 90/270 are still the textbook values and haven't been verified
  // against real hardware yet.
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
