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

#include TREZOR_BOARD

#include <stdint.h>

#ifdef XFRAMEBUFFER

// Size of the physical frame buffer in bytes
#define PHYSICAL_FRAME_BUFFER_SIZE (DISPLAY_RESX * DISPLAY_RESY * 2)

// Physical frame buffers in internal SRAM memory
//
// Both frame buffers layes in the fixed addresses that
// are shared between bootloaders and the firmware.
extern uint8_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE];
extern uint8_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE];

// The current frame buffer selector at fixed memory address
//
// The variable address is shared between bootloaders and the firmware
extern uint32_t current_frame_buffer;

#endif  // XFRAMEBUFFER

#endif  // TREZOR_HAL_DISPLAY_INTERNAL_H
