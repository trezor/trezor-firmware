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

void* display_get_frame_addr(void) {
  if (current_frame_buffer == 0) {
    return (void*)GFXMMU_VIRTUAL_BUFFER0_BASE_S;
  } else {
    return (void*)GFXMMU_VIRTUAL_BUFFER1_BASE_S;
  }
}

void display_refresh(void) {
  current_frame_buffer = current_frame_buffer ? 0 : 1;

  if (current_frame_buffer == 0) {
    BSP_LCD_SetFrameBuffer(0, GFXMMU_VIRTUAL_BUFFER0_BASE_S);
    memcpy(physical_frame_buffer_1, physical_frame_buffer_0,
           PHYSICAL_FRAME_BUFFER_SIZE);
  } else {
    BSP_LCD_SetFrameBuffer(0, GFXMMU_VIRTUAL_BUFFER1_BASE_S);
    memcpy(physical_frame_buffer_0, physical_frame_buffer_1,
           PHYSICAL_FRAME_BUFFER_SIZE);
  }
}