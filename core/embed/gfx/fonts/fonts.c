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
#ifdef TRANSLATIONS
#include "librust_fonts.h"
#endif

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

static const font_info_t *get_font_info(font_id_t font_id) {
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

int font_height(font_id_t font_id) {
  const font_info_t *font_info = get_font_info(font_id);
  return font_info ? font_info->height : 0;
}

int font_max_height(font_id_t font) {
  const font_info_t *font_info = get_font_info(font);
  return font_info ? font_info->max_height : 0;
}

int font_baseline(font_id_t font) {
  const font_info_t *font_info = get_font_info(font);
  return font_info ? font_info->baseline : 0;
}

const uint8_t *font_get_glyph(font_id_t font, uint16_t c) {
#ifdef TRANSLATIONS
  // found UTF8 character
  // it is not hardcoded in firmware fonts, it must be extracted from the
  // embedded blob
  if (c >= 0x7F) {
    const uint8_t *g = get_utf8_glyph(c, font);
    if (g != NULL) {
      return g;
    }
  }
#endif

  // printable ASCII character
  if (c >= ' ' && c < 0x7F) {
    const font_info_t *font_info = get_font_info(font);
    if (font_info == NULL) {
      return NULL;
    }
    return font_info->glyph_data[c - ' '];
  }

  return font_nonprintable_glyph(font);
}

const uint8_t *font_nonprintable_glyph(font_id_t font) {
  const font_info_t *font_info = get_font_info(font);
  return font_info ? font_info->glyph_nonprintable : NULL;
}

font_glyph_iter_t font_glyph_iter_init(font_id_t font, const uint8_t *text,
                                       const int len) {
  return (font_glyph_iter_t){
      .font = font,
      .text = text,
      .remaining = len,
  };
}

#define UNICODE_BADCHAR 0xFFFD
#define IS_UTF8_CONTINUE(c) (((c) & 0b11000000) == 0b10000000)

static uint16_t next_utf8_codepoint(font_glyph_iter_t *iter) {
  uint16_t out;
  assert(iter->remaining > 0);
  // 1-byte UTF-8 character
  if (iter->text[0] < 0x7f) {
    out = iter->text[0];
    ++iter->text;
    --iter->remaining;
    return out;
  }
  // 2-byte UTF-8 character
  if (iter->remaining >= 2 && ((iter->text[0] & 0b11100000) == 0b11000000) &&
      IS_UTF8_CONTINUE(iter->text[1])) {
    out = (((uint16_t)iter->text[0] & 0b00011111) << 6) |
          (iter->text[1] & 0b00111111);
    iter->text += 2;
    iter->remaining -= 2;
    return out;
  }
  // 3-byte UTF-8 character
  if (iter->remaining >= 3 && ((iter->text[0] & 0b11110000) == 0b11100000) &&
      IS_UTF8_CONTINUE(iter->text[1]) && IS_UTF8_CONTINUE(iter->text[2])) {
    out = (((uint16_t)iter->text[0] & 0b00001111) << 12) |
          (((uint16_t)iter->text[1] & 0b00111111) << 6) |
          (iter->text[2] & 0b00111111);
    iter->text += 3;
    iter->remaining -= 3;
    return out;
  }
  // 4-byte UTF-8 character
  if (iter->remaining >= 4 && ((iter->text[0] & 0b11111000) == 0b11110000) &&
      IS_UTF8_CONTINUE(iter->text[1]) && IS_UTF8_CONTINUE(iter->text[2]) &&
      IS_UTF8_CONTINUE(iter->text[3])) {
    // we use 16-bit codepoints, so we can't represent 4-byte UTF-8 characters
    iter->text += 4;
    iter->remaining -= 4;
    return UNICODE_BADCHAR;
  }

  ++iter->text;
  --iter->remaining;
  return UNICODE_BADCHAR;
}

bool font_next_glyph(font_glyph_iter_t *iter, const uint8_t **out) {
  if (iter->remaining <= 0) {
    return false;
  }
  uint16_t c = next_utf8_codepoint(iter);
  *out = font_get_glyph(iter->font, c);
  if (*out == NULL) {
    // should not happen but ¯\_(ツ)_/¯
    return font_next_glyph(iter, out);
  } else {
    return true;
  }
}

// compute the width of the text (in pixels)
int font_text_width(font_id_t font, const char *text, int textlen) {
  int width = 0;
  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }
  font_glyph_iter_t iter = font_glyph_iter_init(font, (uint8_t *)text, textlen);
  const uint8_t *g = NULL;
  while (font_next_glyph(&iter, &g)) {
    const uint8_t adv = g[2];  // advance
    width += adv;
  }
  return width;
}
