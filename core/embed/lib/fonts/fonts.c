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

#include "fonts.h"
#include <stdbool.h>
#include <stdio.h>
#ifdef TRANSLATIONS
#include "librust_fonts.h"
#endif

// TODO: make it return uint32_t (needs logic to assemble at most 4 bytes
// together)
static uint16_t convert_char_utf8(const uint8_t c) {
  // Considering only two-byte UTF-8 characters currently
  static uint8_t first_utf8_byte = 0;

  // non-printable ASCII character
  if (c < ' ') {
    first_utf8_byte = 0;
    return 0x7F;
  }

  // regular ASCII character
  if (c < 0x80) {
    first_utf8_byte = 0;
    return c;
  }

  // UTF-8 handling: https://en.wikipedia.org/wiki/UTF-8#Encoding

  // bytes 11xxxxxx are first bytes of UTF-8 characters
  if (c >= 0xC0) {
    first_utf8_byte = c;
    return 0;  // not print this
  }

  if (first_utf8_byte) {
    // encountered a successive UTF-8 character ...
    return ((uint16_t)first_utf8_byte << 8) | c;
  } else {
    // ... or they are just non-printable ASCII characters
    return 0x7F;
  }
}

int font_height(int font) {
  switch (font) {
#ifdef TREZOR_FONT_NORMAL_ENABLE
    case FONT_NORMAL:
      return FONT_NORMAL_HEIGHT;
#endif
#ifdef TREZOR_FONT_DEMIBOLD_ENABLE
    case FONT_DEMIBOLD:
      return FONT_DEMIBOLD_HEIGHT;
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
    case FONT_BOLD:
      return FONT_BOLD_HEIGHT;
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
    case FONT_MONO:
      return FONT_MONO_HEIGHT;
#endif
#ifdef TREZOR_FONT_BIG_ENABLE
    case FONT_BIG:
      return FONT_BIG_HEIGHT;
#endif
  }
  return 0;
}

int font_max_height(int font) {
  switch (font) {
#ifdef TREZOR_FONT_NORMAL_ENABLE
    case FONT_NORMAL:
      return FONT_NORMAL_MAX_HEIGHT;
#endif
#ifdef TREZOR_FONT_DEMIBOLD_ENABLE
    case FONT_DEMIBOLD:
      return FONT_DEMIBOLD_MAX_HEIGHT;
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
    case FONT_BOLD:
      return FONT_BOLD_MAX_HEIGHT;
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
    case FONT_MONO:
      return FONT_MONO_MAX_HEIGHT;
#endif
#ifdef TREZOR_FONT_BIG_ENABLE
    case FONT_BIG:
      return FONT_BIG_MAX_HEIGHT;
#endif
  }
  return 0;
}

int font_baseline(int font) {
  switch (font) {
#ifdef TREZOR_FONT_NORMAL_ENABLE
    case FONT_NORMAL:
      return FONT_NORMAL_BASELINE;
#endif
#ifdef TREZOR_FONT_DEMIBOLD_ENABLE
    case FONT_DEMIBOLD:
      return FONT_DEMIBOLD_BASELINE;
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
    case FONT_BOLD:
      return FONT_BOLD_BASELINE;
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
    case FONT_MONO:
      return FONT_MONO_BASELINE;
#endif
#ifdef TREZOR_FONT_BIG_ENABLE
    case FONT_BIG:
      return FONT_BIG_BASELINE;
#endif
  }
  return 0;
}

const uint8_t *font_get_glyph(int font, uint8_t c) {
  uint16_t c_2bytes = convert_char_utf8(c);
  bool is_printable = c_2bytes != 0x7F;
  if (!c_2bytes) return 0;

#ifdef TRANSLATIONS
  // found UTF8 character
  // it is not hardcoded in firmware fonts, it must be extracted from the
  // embedded blob
  if (c_2bytes > 0xFF) {
    PointerData glyph_data = get_utf8_glyph(c_2bytes, font);
    if (glyph_data.ptr != NULL) {
      return glyph_data.ptr;
    } else {
      is_printable = false;
    }
  }
#endif

  // printable ASCII character
  if (is_printable && c_2bytes >= ' ' && c_2bytes <= 126) {
    switch (font) {
#ifdef TREZOR_FONT_NORMAL_ENABLE
      case FONT_NORMAL:
        return FONT_NORMAL_DATA[c_2bytes - ' '];
#endif
#ifdef TREZOR_FONT_DEMIBOLD_ENABLE
      case FONT_DEMIBOLD:
        return FONT_DEMIBOLD_DATA[c_2bytes - ' '];
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
      case FONT_BOLD:
        return FONT_BOLD_DATA[c_2bytes - ' '];
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
      case FONT_MONO:
        return FONT_MONO_DATA[c_2bytes - ' '];
#endif
#ifdef TREZOR_FONT_BIG_ENABLE
      case FONT_BIG:
        return FONT_BIG_DATA[c_2bytes - ' '];
#endif
    }
    return 0;
  }

// non-printable character
#define PASTER(s) s##_glyph_nonprintable
#define NONPRINTABLE_GLYPH(s) PASTER(s)

  switch (font) {
#ifdef TREZOR_FONT_NORMAL_ENABLE
    case FONT_NORMAL:
      return NONPRINTABLE_GLYPH(FONT_NORMAL_DATA);
#endif
#ifdef TREZOR_FONT_DEMIBOLD_ENABLE
    case FONT_DEMIBOLD:
      return NONPRINTABLE_GLYPH(FONT_DEMIBOLD_DATA);
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
    case FONT_BOLD:
      return NONPRINTABLE_GLYPH(FONT_BOLD_DATA);
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
    case FONT_MONO:
      return NONPRINTABLE_GLYPH(FONT_MONO_DATA);
#endif
#ifdef TREZOR_FONT_BIG_ENABLE
    case FONT_BIG:
      return NONPRINTABLE_GLYPH(FONT_BIG_DATA);
#endif
  }
  return 0;
}
