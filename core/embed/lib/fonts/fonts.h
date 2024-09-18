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

#ifndef _FONTS_H
#define _FONTS_H

#include <stdbool.h>

#include "fonts/font_bitmap.h"
#include "fonts_types.h"
#include TREZOR_BOARD

#ifdef USE_RGB_COLORS
#define TREZOR_FONT_BPP 4
#else
#define TREZOR_FONT_BPP 1
#endif

// Calculate the maximum height across all enabled fonts at compile time
#define MAX_FONT_H(A, B) ((A) > (B) ? (A) : (B))
// clang-format off
#define FONT_MAX_HEIGHT \
    MAX_FONT_H( \
    MAX_FONT_H( \
    MAX_FONT_H( \
    MAX_FONT_H( \
    MAX_FONT_H( \
    MAX_FONT_H( \
    MAX_FONT_H( \
    MAX_FONT_H(0, \
        TREZOR_FONT_NORMAL_ENABLE ? FONT_NORMAL_MAX_HEIGHT : 0), \
        TREZOR_FONT_BOLD_ENABLE ? FONT_BOLD_MAX_HEIGHT : 0), \
        TREZOR_FONT_BIG_ENABLE ? FONT_BIG_MAX_HEIGHT : 0), \
        TREZOR_FONT_DEMIBOLD_ENABLE ? FONT_DEMIBOLD_MAX_HEIGHT : 0), \
        TREZOR_FONT_NORMAL_UPPER_ENABLE ? FONT_NORMAL_UPPER_MAX_HEIGHT : 0), \
        TREZOR_FONT_BOLD_UPPER_ENABLE ? FONT_BOLD_UPPER_MAX_HEIGHT : 0), \
        TREZOR_FONT_SUB_ENABLE ? FONT_SUB_MAX_HEIGHT : 0), \
        TREZOR_FONT_MONO_ENABLE ? FONT_MONO_MAX_HEIGHT : 0)
// clang-format on

int font_height(int font);
int font_max_height(int font);
int font_baseline(int font);
const uint8_t *font_get_glyph(int font, uint16_t c);
const uint8_t *font_nonprintable_glyph(int font);

font_glyph_iter_t font_glyph_iter_init(const int font, const uint8_t *text,
                                       const int len);
bool font_next_glyph(font_glyph_iter_t *iter, const uint8_t **out);
int font_text_width(int font, const char *text, int textlen);

#endif  //_FONTS_H
