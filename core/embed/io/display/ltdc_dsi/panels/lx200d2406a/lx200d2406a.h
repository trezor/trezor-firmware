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

#define VSYNC 4
#define VBP 4
#define VFP 660
#define VACT 320
#define HSYNC 30
#define HBP 60
#define HFP 60
#define HACT 240
#define LCD_WIDTH 240
#define LCD_HEIGHT 320

#define LCD_X_OFFSET 0
#define LCD_Y_OFFSET 0

#define PANEL_DSI_MODE DSI_VID_MODE_NB_PULSES
#define PANEL_DSI_LANES DSI_ONE_DATA_LANE
#define PANEL_LTDC_PIXEL_FORMAT LTDC_PIXEL_FORMAT_RGB565

// Size of the physical frame buffer in bytes
//
// It's smaller than size of the virtual frame buffer
// due to used GFXMMU settings
#define PHYSICAL_FRAME_BUFFER_SIZE (240 * 320 * 2)
#define VIRTUAL_FRAME_BUFFER_SIZE PHYSICAL_FRAME_BUFFER_SIZE

// Pitch (in pixels) of the virtual frame buffer
#define FRAME_BUFFER_PIXELS_PER_LINE 240
