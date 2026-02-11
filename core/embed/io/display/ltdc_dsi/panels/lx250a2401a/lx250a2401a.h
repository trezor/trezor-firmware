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

#pragma once

#include <trezor_types.h>

#define REFRESH_RATE_SCALING_SUPPORTED 1

#define PANEL_REFRESH_RATE_HI 60
#define PANEL_REFRESH_RATE_LO 30

// DSI PLL configuration (lane byte clock, TX escape clock)
// DSI_LANE_BYTE_CLOCK_HZ = (((HSE_VALUE / PLL_DSI_IDF) * 2 * PLL_DSI_NDIV) /
// PLL_DSI_ODF) / 8
#define DSI_LANE_BYTE_CLOCK_HZ 62000000UL  // PLL DSI
#define PLL_DSI_IDF 4
#define PLL_DSI_NDIV \
  ((DSI_LANE_BYTE_CLOCK_HZ * 8 * PLL_DSI_ODF * PLL_DSI_IDF) / (2 * HSE_VALUE))
#define PLL_DSI_ODF 2
#define DSI_DPHY_FRANGE DSI_DPHY_FRANGE_450MHZ_510MHZ
#define DSI_TX_ESCAPE_CLK_DIV 4  // 15.5MHz, ~7.75MHz (in LP)

// DSI PHY timing parameters configuration
#define PHY_LP_OFFSET PHY_LP_OFFSSET_0_CLKP  // LPXO - no offset
// RM0456 Table 445. HS2LP and LP2HS values vs. band frequency (MHz)
#define PHY_TIMER_CLK_HS2LP 11
#define PHY_TIMER_CLK_LP2HS 40
#define PHY_TIMER_DATA_HS2LP 12
#define PHY_TIMER_DATA_LP2HS 23

// LTDC PLL3 configuration (pixel clock and lane byte clock at the beginning of
// initialization)
// LTDC_PIXEL_CLOCK_HZ = ((HSE_VALUE / PLL3_M) * PLL3_N) / PLL3_R
#define LTDC_PIXEL_CLOCK_HZ 18518519UL  // Output of PLL3R
// 4MHz is used as PLL3 block input clock
#define PLL3_M (HSE_VALUE / 4000000UL)
#define PLL3_N 125
#define PLL3_P 8
#define PLL3_Q 8  // Not used output clock branch
#define PLL3_R 27

// DSI lane byte clock to LTDC pixel clock ratio (floating point)
#define LANE_BYTE_2_PIXEL_CLK_RATIO \
  ((float)DSI_LANE_BYTE_CLOCK_HZ / (float)LTDC_PIXEL_CLOCK_HZ)

// Display timing parameters
#define HSYNC 6   // Horizontal Sync
#define HBP 2     // Horizontal Back Porch
#define HACT 480  // Horizontal Active Time
#define HFP 56    // Horizontal Front Porch

#define VSYNC 2   // Vertical Sync
#define VBP 26    // Vertical Back Porch
#define VACT 520  // Vertical Active Time
#define VFP_CALC(f)                                             \
  ((LTDC_PIXEL_CLOCK_HZ / ((f) * (HSYNC + HBP + HACT + HFP))) - \
   (VSYNC + VBP + VACT))
#define VFP_REFRESH_RATE_HI VFP_CALC(PANEL_REFRESH_RATE_HI)
#define VFP_REFRESH_RATE_LO VFP_CALC(PANEL_REFRESH_RATE_LO)
#define VFP VFP_REFRESH_RATE_HI  // Vertical Front Porch

#define PANEL_DSI_MODE DSI_VID_MODE_BURST
#define PANEL_DSI_LANES DSI_TWO_DATA_LANES
#define PANEL_DSI_COLOR_CODING DSI_RGB888

#define PANEL_LTDC_PIXEL_FORMAT LTDC_PIXEL_FORMAT_ARGB8888

#define LCD_WIDTH 480
#define LCD_HEIGHT 520

#define LCD_X_OFFSET 50
#define LCD_Y_OFFSET 0

#define GFXMMU_LUT_FIRST 0
#define GFXMMU_LUT_LAST 519
#define GFXMMU_LUT_SIZE 520

// IMPORTANT:
//
// Changing this value affects constants in backlight.rs and bootui.h
// (for example: BACKLIGHT_NORMAL, BACKLIGHT_LOW, BACKLIGHT_DIM,
// BACKLIGHT_NONE, BACKLIGHT_MIN, and BACKLIGHT_MAX). Ensure these
// values remain consistent.
// Additionally, changing this value can affect CI tests, production-
// line tests, and backlight settings on devices in the field.
//
// See issue #6028 for details.
#define GAMMA_EXP 2.2f

// Size of the physical frame buffer in bytes
//
// It's smaller than size of the virtual frame buffer
// due to used GFXMMU settings
#define PHYSICAL_FRAME_BUFFER_SIZE (765 * 1024)

// Pitch (in pixels) of the virtual frame buffer
#define FRAME_BUFFER_PIXELS_PER_LINE 768

#define VIRTUAL_FRAME_BUFFER_SIZE \
  (FRAME_BUFFER_PIXELS_PER_LINE * LCD_HEIGHT * 4)
