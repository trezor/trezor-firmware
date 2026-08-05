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

#ifndef LX240D4508CTP05_H_
#define LX240D4508CTP05_H_

#include "../display_panel.h"

// LX240D4508CTP05A / LX240D4508CTP05B, 2.4" TFT-LCD, 240(RGB)x320,
// controller GC9307C. Pinout, resolution and register-level init sequence
// are identical to LX200B4501CTP03A/B (see lx200b4501ctp03.c) - only the
// panel size (2.4" vs 2.0") and touch-panel OCA bonding level differ (A:
// 100% transparent OCA, B: 70% semi-transparent OCA), so both part numbers
// are served by this single panel definition.

void lx240d4508ctp05_init_seq(void);
void lx240d4508ctp05_rotate(int degrees, display_padding_t* padding);

#endif
