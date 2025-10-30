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

void touch_debug_init(void);

void touch_debug_deinit(void);

void touch_debug_start(uint32_t x, uint32_t y);

void touch_debug_end(uint32_t x, uint32_t y);

void touch_debug_click(uint32_t x, uint32_t y);

void touch_debug_next(void);

bool touch_debug_active(void);

uint32_t touch_debug_get_state(void);
