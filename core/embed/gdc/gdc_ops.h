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

#include "gdc_dma2d.h"

bool rgb565_fill(const dma2d_params_t* dp);
bool rgb565_copy_mono4(const dma2d_params_t* dp);
bool rgb565_copy_rgb565(const dma2d_params_t* dp);
bool rgb565_blend_mono4(const dma2d_params_t* dp);

bool rgba8888_fill(const dma2d_params_t* dp);
bool rgba8888_copy_mono4(const dma2d_params_t* dp);
bool rgba8888_copy_rgb565(const dma2d_params_t* dp);
bool rgba8888_copy_rgba8888(const dma2d_params_t* dp);
bool rgba8888_blend_mono4(const dma2d_params_t* dp);

bool mono8_fill(const dma2d_params_t* dp);
bool mono8_copy_mono1p(const dma2d_params_t* dp);
bool mono8_copy_mono4(const dma2d_params_t* dp);
bool mono8_blend_mono1p(const dma2d_params_t* dp);
bool mono8_blend_mono4(const dma2d_params_t* dp);

bool wnd565_fill(const dma2d_params_t* dp);
bool wnd565_copy_rgb565(const dma2d_params_t* dp);
