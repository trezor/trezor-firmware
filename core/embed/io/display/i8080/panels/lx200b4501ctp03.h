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

#ifndef LX200B4501CTP03_H_
#define LX200B4501CTP03_H_

#include "../display_panel.h"

// LX200B4501CTP03A / LX200B4501CTP03B, 2.0" TFT-LCD, 240(RGB)x320,
// controller GC9307C. The two part numbers differ only in backlight
// luminance (700 vs 530 nit typ.) - electrically and register-wise
// identical, so both are served by this single panel definition.

void lx200b4501ctp03_init_seq(void);
void lx200b4501ctp03_rotate(int degrees, display_padding_t* padding);

#endif
