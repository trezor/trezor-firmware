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

#ifndef TREZORHAL_DMA2D_H
#define TREZORHAL_DMA2D_H

#include "common.h"

void dma2d_init(void);

void dma2d_setup_const(void);
void dma2d_setup_4bpp(uint16_t fg_color, uint16_t bg_color);
void dma2d_setup_16bpp(void);
void dma2d_setup_4bpp_over_4bpp(uint16_t fg_color, uint16_t bg_color,
                                uint16_t overlay_color);
void dma2d_setup_4bpp_over_16bpp(uint16_t overlay_color);

void dma2d_start(uint8_t* in_addr, uint8_t* out_addr, int32_t pixels);
void dma2d_start_const(uint16_t color, uint8_t* out_addr, int32_t pixels);
void dma2d_start_const_multiline(uint16_t color, uint8_t* out_addr,
                                 int32_t width, int32_t height);
void dma2d_start_blend(uint8_t* overlay_addr, uint8_t* bg_addr,
                       uint8_t* out_addr, int32_t pixels);

void dma2d_wait_for_transfer(void);

#endif  // TREZORHAL_DMA2D_H
