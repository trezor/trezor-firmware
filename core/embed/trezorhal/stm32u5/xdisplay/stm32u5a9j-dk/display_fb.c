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

#include <stdint.h>
#include <string.h>

#include TREZOR_BOARD
#include STM32_HAL_H

#include <xdisplay.h>
#include "display_internal.h"

// Physical frame buffers in internal SRAM memory
__attribute__((section(".fb1")))
ALIGN_32BYTES(uint32_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE]);

__attribute__((section(".fb2")))
ALIGN_32BYTES(uint32_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE]);

// The current frame buffer selector at fixed memory address
// It's shared between bootloaders and the firmware
__attribute__((section(".framebuffer_select"))) uint32_t current_frame_buffer =
    0;

display_fb_info_t display_get_frame_buffer(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    display_fb_info_t fb = {
        .ptr = NULL,
        .stride = 0,
    };
    return fb;
  }

  uintptr_t addr;

  if (current_frame_buffer == 0) {
    addr = GFXMMU_VIRTUAL_BUFFER1_BASE_S;
  } else {
    addr = GFXMMU_VIRTUAL_BUFFER0_BASE_S;
  }

  uint32_t fb_stride = FRAME_BUFFER_PIXELS_PER_LINE * sizeof(uint32_t);

  // We do not utilize whole area of the display
  // (discovery kit display is 480x480 and we need just 240x240)
  addr += (480 - DISPLAY_RESY) / 2 * sizeof(uint32_t);
  addr += (480 - DISPLAY_RESX) / 2 * fb_stride;

  display_fb_info_t fb = {
      .ptr = (void *)addr,
      .stride = fb_stride,
  };

  return fb;
}

void display_refresh(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  if (current_frame_buffer == 0) {
    current_frame_buffer = 1;
    BSP_LCD_SetFrameBuffer(0, GFXMMU_VIRTUAL_BUFFER1_BASE_S);
    memcpy(physical_frame_buffer_0, physical_frame_buffer_1,
           sizeof(physical_frame_buffer_0));
  } else {
    current_frame_buffer = 0;
    BSP_LCD_SetFrameBuffer(0, GFXMMU_VIRTUAL_BUFFER0_BASE_S);
    memcpy(physical_frame_buffer_1, physical_frame_buffer_0,
           sizeof(physical_frame_buffer_1));
  }
}
