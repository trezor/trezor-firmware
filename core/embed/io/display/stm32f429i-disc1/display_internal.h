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

#ifndef TREZORHAL_DISPLAY_INTERNAL_H
#define TREZORHAL_DISPLAY_INTERNAL_H

#include <trezor_bsp.h>
#include <trezor_types.h>

#include <sys/sdram.h>

// Frame buffer address in external SDRAM
#define FRAME_BUFFER_ADDR ((uint32_t)SDRAM_DEVICE_ADDR)
// Frame buffer size (16-bit per pixel RGB565)
#define FRAME_BUFFER_SIZE (DISPLAY_RESX * DISPLAY_RESY * 2)

// Initializes LTDC controller and I/O pins
void BSP_LCD_Init(void);

#endif  // TREZORHAL_DISPLAY_INTERNAL_H
