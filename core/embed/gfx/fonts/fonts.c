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

#include <trezor_rtl.h>

#include "fonts.h"

// include selectively based on the SCons variables
#ifdef TREZOR_FONT_NORMAL_ENABLE
#include TREZOR_FONT_NORMAL_INCLUDE
#endif
#ifdef TREZOR_FONT_DEMIBOLD_ENABLE
#include TREZOR_FONT_DEMIBOLD_INCLUDE
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
#include TREZOR_FONT_BOLD_INCLUDE
#endif
#ifdef TREZOR_FONT_NORMAL_UPPER_ENABLE
#include TREZOR_FONT_NORMAL_UPPER_INCLUDE
#endif
#ifdef TREZOR_FONT_BOLD_UPPER_ENABLE
#include TREZOR_FONT_BOLD_UPPER_INCLUDE
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
#include TREZOR_FONT_MONO_INCLUDE
#endif
#ifdef TREZOR_FONT_BIG_ENABLE
#include TREZOR_FONT_BIG_INCLUDE
#endif
#ifdef TREZOR_FONT_SUB_ENABLE
#include TREZOR_FONT_SUB_INCLUDE
#endif

#define PASTER(font_name) font_name##_info
#define FONT_INFO(font_name) PASTER(font_name)

const font_info_t *get_font_info(font_id_t font_id) {
  switch (font_id) {
#ifdef TREZOR_FONT_NORMAL_ENABLE
    case FONT_NORMAL:
      return &FONT_INFO(TREZOR_FONT_NORMAL_NAME);
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
    case FONT_BOLD:
      return &FONT_INFO(TREZOR_FONT_BOLD_NAME);
#endif
#ifdef TREZOR_FONT_DEMIBOLD_ENABLE
    case FONT_DEMIBOLD:
      return &FONT_INFO(TREZOR_FONT_DEMIBOLD_NAME);
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
    case FONT_MONO:
      return &FONT_INFO(TREZOR_FONT_MONO_NAME);
#endif
#ifdef TREZOR_FONT_BIG_ENABLE
    case FONT_BIG:
      return &FONT_INFO(TREZOR_FONT_BIG_NAME);
#endif
#ifdef TREZOR_FONT_NORMAL_UPPER_ENABLE
    case FONT_NORMAL_UPPER:
      return &FONT_INFO(TREZOR_FONT_NORMAL_UPPER_NAME);
#endif
#ifdef TREZOR_FONT_BOLD_UPPER_ENABLE
    case FONT_BOLD_UPPER:
      return &FONT_INFO(TREZOR_FONT_BOLD_UPPER_NAME);
#endif
#ifdef TREZOR_FONT_SUB_ENABLE
    case FONT_SUB:
      return &FONT_INFO(TREZOR_FONT_SUB_NAME);
#endif
    default:
      return NULL;
  }
}

const uint8_t *font_nonprintable_glyph(font_id_t font) {
  const font_info_t *font_info = get_font_info(font);
  return font_info ? font_info->glyph_nonprintable : NULL;
}

const uint8_t *font_get_glyph(font_id_t font, char c) {
  // support only printable ASCII character
  if (c >= ' ' && c < 0x7F) {
    const font_info_t *font_info = get_font_info(font);
    if (font_info == NULL) {
      return NULL;
    }
    return font_info->glyph_data[c - ' '];
  }

  return font_nonprintable_glyph(font);
}

int font_baseline(font_id_t font) {
  const font_info_t *font_info = get_font_info(font);
  return font_info ? font_info->baseline : 0;
}

int font_max_height(font_id_t font) {
  const font_info_t *font_info = get_font_info(font);
  return font_info ? font_info->max_height : 0;
}

// compute the width of the ASCII text (in pixels)
int font_text_width(font_id_t font, const char *text, int textlen) {
  int width = 0;
  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }

  const font_info_t *font_info = get_font_info(font);
  if (font_info == NULL) {
    return 0;
  }

  for (int i = 0; i < textlen; ++i) {
    const uint8_t *glyph;
    char c = text[i];

    if (c >= ' ' && c < 0x7F) {
      glyph = font_info->glyph_data[c - ' '];
    } else {
      glyph = font_info->glyph_nonprintable;
    }
    const uint8_t adv = glyph[2];  // advance
    width += adv;
  }

  return width;
}
