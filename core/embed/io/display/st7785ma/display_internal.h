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

#include <trezor_types.h>

typedef struct {
  bool initialized;
  bool blanking;
  uint32_t current_frame_buffer;
  DSI_HandleTypeDef hlcd_dsi;
  LTDC_HandleTypeDef hlcd_ltdc;
  DSI_VidCfgTypeDef DSIVidCfg;
} display_driver_t;

extern display_driver_t g_display_driver;

// Size of the physical frame buffer in bytes
//
// It's smaller than size of the virtual frame buffer
// due to used GFXMMU settings
#define PHYSICAL_FRAME_BUFFER_SIZE (240 * 320 * 2)

// Pitch (in pixels) of the virtual frame buffer
#define FRAME_BUFFER_PIXELS_PER_LINE 240

void display_set_fb(uint32_t fb_addr);

void display_fb_clear(void);

uint32_t display_fb_get_initial_addr(void);

#endif  // TREZOR_HAL_DISPLAY_INTERNAL_H
