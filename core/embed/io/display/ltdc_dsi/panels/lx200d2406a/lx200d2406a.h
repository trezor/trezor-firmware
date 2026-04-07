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

#define REFRESH_RATE_SCALING_SUPPORTED 0

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
#define LTDC_PIXEL_CLOCK_HZ 20833333UL  // Output of PLL3R
// 4MHz is used as PLL3 block input clock
#define PLL3_M (HSE_VALUE / 4000000UL)
#define PLL3_N 125
#define PLL3_P 8
#define PLL3_Q 8  // Not used output clock branch
#define PLL3_R 24

// DSI lane byte clock to LTDC pixel clock ratio
#define LANE_BYTE_2_PIXEL_CLK_RATIO 3

// Display timing parameters
#define HSYNC 30  // Horizontal Sync
#define HBP 60    // Horizontal Back Porch
#define HACT 240  // Horizontal Active Time
#define HFP 60    // Horizontal Front Porch

#define VSYNC 4   // Vertical Sync
#define VBP 4     // Vertical Back Porch
#define VACT 320  // Vertical Active Time
#define VFP 660   // Vertical Front Porch

#define PANEL_DSI_MODE DSI_VID_MODE_NB_PULSES
#define PANEL_DSI_LANES DSI_ONE_DATA_LANE
#define PANEL_DSI_COLOR_CODING DSI_RGB888

#define PANEL_LTDC_PIXEL_FORMAT LTDC_PIXEL_FORMAT_RGB565

#define LCD_WIDTH 240
#define LCD_HEIGHT 320

#define LCD_X_OFFSET 0
#define LCD_Y_OFFSET 0

// Size of the physical frame buffer in bytes
//
// It's smaller than size of the virtual frame buffer
// due to used GFXMMU settings
#define PHYSICAL_FRAME_BUFFER_SIZE (240 * 320 * 2)
#define VIRTUAL_FRAME_BUFFER_SIZE PHYSICAL_FRAME_BUFFER_SIZE

// Pitch (in pixels) of the virtual frame buffer
#define FRAME_BUFFER_PIXELS_PER_LINE 240
