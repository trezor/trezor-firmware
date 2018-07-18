/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#ifndef TREZORHAL_TOUCH_H
#define TREZORHAL_TOUCH_H

#include <stdint.h>

#define TOUCH_START (1U << 24)
#define TOUCH_MOVE  (2U << 24)
#define TOUCH_END   (4U << 24)

void touch_init(void);
void touch_power_on(void);
void touch_power_off(void);
uint32_t touch_read(void);
uint32_t touch_click(void);
inline uint16_t touch_get_x(uint32_t evt) { return (evt >> 12) & 0xFFF; }
inline uint16_t touch_get_y(uint32_t evt) { return (evt >> 0) & 0xFFF; }
inline uint32_t touch_pack_xy(uint16_t x, uint16_t y) { return ((x & 0xFFF) << 12) | (y & 0xFFF); }

#endif
