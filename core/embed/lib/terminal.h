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

#ifndef LIB_TERMINAL_H
#define LIB_TERMINAL_H

#include "colors.h"

#ifndef TREZOR_PRINT_DISABLE
void term_set_color(uint16_t fgcolor, uint16_t bgcolor);
void term_print(const char *text, int textlen);
void term_printf(const char *fmt, ...)
    __attribute__((__format__(__printf__, 1, 2)));
#endif

#endif  // LIB_TERMINAL_H
