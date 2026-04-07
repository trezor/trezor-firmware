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

#include <io/gfx_color.h>

/**
 * Sets foreground and background colors for terminal text.
 *
 * Note: The current implementation does not support per-character colors.
 * It only supports setting global foreground and background colors, which
 * may be used before printing any text to the terminal.
 *
 * @param fgcolor Foreground color.
 * @param bgcolor Background color.
 */
void term_set_color(gfx_color_t fgcolor, gfx_color_t bgcolor);

/**
 * Prints a text of given length to the terminal.
 *
 * @param text Text to print.
 * @param textlen Number of characters to print from the text.
 */
void term_nprint(const char *text, int textlen);

/**
 * Prints null-terminated text to the terminal.
 *
 * @param text Text to print.
 */
void term_print(const char *text);

/**
 * Prints a 32-bit integer in decimal format to the terminal.
 *
 * @param value Integer value to print.
 */
void term_print_int32(int32_t value);

/**
 * Prints printf-style formatted text to the terminal.
 *
 * The function internally uses `vsnprintf_` to format the text.
 *
 * @param fmt Format string (printf-style).
 * @param ... Additional arguments for formatting.
 */
void term_printf(const char *fmt, ...)
    __attribute__((__format__(__printf__, 1, 2)));
