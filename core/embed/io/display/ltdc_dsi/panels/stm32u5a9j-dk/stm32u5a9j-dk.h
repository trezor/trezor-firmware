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

#define VSYNC 1
#define VBP 12
#define VFP 50
#define VACT 481
#define HSYNC 2
#define HBP 1
#define HFP 1
#define HACT 480
#define LCD_WIDTH 480
#define LCD_HEIGHT 480

#define LCD_Y_OFFSET 1

#define GFXMMU_FB_SIZE 733936
#define GFXMMU_LUT_FIRST 0
#define GFXMMU_LUT_LAST 479
#define GFXMMU_LUT_SIZE 480

#define PANEL_DSI_MODE DSI_VID_MODE_BURST
#define PANEL_DSI_LANES DSI_TWO_DATA_LANES
#define PANEL_LTDC_PIXEL_FORMAT LTDC_PIXEL_FORMAT_ARGB8888

// Size of the physical frame buffer in bytes
//
// It's smaller than size of the virtual frame buffer
// due to used GFXMMU settings
#define PHYSICAL_FRAME_BUFFER_SIZE (184320 * 4)

// Pitch (in pixels) of the virtual frame buffer
#define FRAME_BUFFER_PIXELS_PER_LINE 768

// Size of the virtual frame buffer in bytes
#define VIRTUAL_FRAME_BUFFER_SIZE \
  (FRAME_BUFFER_PIXELS_PER_LINE * LCD_HEIGHT * 4)
