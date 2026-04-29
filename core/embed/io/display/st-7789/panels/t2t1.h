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

#ifndef T2T1_H_
#define T2T1_H_

#include "../display_panel.h"

// Composed panel for Trezor Model T (T2T1).
// Dispatches at runtime between GC9307, ST7789V, and ILI9341V controllers
// based on display IC identification.

void t2t1_init_seq(void);
void t2t1_reinit(void);
void t2t1_rotate(int degrees, display_padding_t* padding);

#ifndef BOARDLOADER
void t2t1_preserve_inversion(void);
#endif

#endif  // T2T1_H_
