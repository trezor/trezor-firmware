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

#include <trezor_types.h>
#include "font_bitmap.h"

#ifdef USE_RGB_COLORS
#define TREZOR_FONT_BPP 4
#else
#define TREZOR_FONT_BPP 1
#endif

/// Font information structure containing metadata and pointers to font data
typedef struct {
  int height;
  int max_height;
  int baseline;
  const uint8_t *const *glyph_data;
  const uint8_t *glyph_nonprintable;
} font_info_t;

/// Font identifiers. Keep in sync with `enum font` definition in
/// `core/embed/rust/src/ui/display/font.rs`.
typedef enum {
  FONT_NORMAL = -1,
  FONT_BOLD = -2,
  FONT_MONO = -3,
  FONT_BIG = -4,
  FONT_DEMIBOLD = -5,
  FONT_NORMAL_UPPER = -6,
  FONT_BOLD_UPPER = -7,
  FONT_SUB = -8,
} font_id_t;

const font_info_t *get_font_info(font_id_t font_id);
const uint8_t *font_get_glyph(font_id_t font, const char c);

int font_baseline(font_id_t font);
int font_max_height(font_id_t font);
int font_text_width(font_id_t font, const char *text, int textlen);

#endif  //_FONTS_H
