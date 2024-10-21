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

#ifndef TREZOR_HAL_DISPLAY_INTERNAL_H
#define TREZOR_HAL_DISPLAY_INTERNAL_H

#include <stdbool.h>
#include <stdint.h>

// Display driver context.
typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Current display orientation (0, 90, 180, 270)
  int orientation_angle;
  // Current backlight level ranging from 0 to 255
  int backlight_level;
} display_driver_t;

// Display driver instance
extern display_driver_t g_display_driver;

// Size of the physical frame buffer in bytes
//
// It's smaller than size of the virtual frame buffer
// due to used GFXMMU settings
#define PHYSICAL_FRAME_BUFFER_SIZE 184320

// Pitch (in pixels) of the virtual frame buffer
#define FRAME_BUFFER_PIXELS_PER_LINE 768

// Size of the virtual frame buffer in bytes
#define VIRTUAL_FRAME_BUFFER_SIZE \
  (FRAME_BUFFER_PIXELS_PER_LINE * DISPLAY_RESY * 4)

// Physical frame buffers in internal SRAM memory
//
// Both frame buffers layes in the fixed addresses that
// are shared between bootloaders and the firmware.
extern uint32_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE];
extern uint32_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE];

// The current frame buffer selector at fixed memory address
//
// The variable address is shared between bootloaders and the firmware
extern uint32_t current_frame_buffer;

// LCD orientations
#define LCD_ORIENTATION_PORTRAIT 0U
#define LCD_ORIENTATION_LANDSCAPE 1U
#define LCD_ORIENTATION_PORTRAIT_ROT180 2U
#define LCD_ORIENTATION_LANDSCAPE_ROT180 3U

int32_t BSP_LCD_Init(uint32_t Instance, uint32_t Orientation);
int32_t BSP_LCD_DeInit(uint32_t Instance);
int32_t BSP_LCD_Reinit(uint32_t Instance);
int32_t BSP_LCD_SetBrightness(uint32_t Instance, uint32_t Brightness);
int32_t BSP_LCD_DisplayOn(uint32_t Instance);
int32_t BSP_LCD_DisplayOff(uint32_t Instance);
int32_t BSP_LCD_SetFrameBuffer(uint32_t Instance, uint32_t fb_addr);

#endif  // TREZOR_HAL_DISPLAY_INTERNAL_H
