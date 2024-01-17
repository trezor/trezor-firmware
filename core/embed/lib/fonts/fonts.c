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
#include <string.h>

static uint8_t convert_char(const uint8_t c) {
  static char last_was_utf8 = 0;

  // non-printable ASCII character
  if (c < ' ') {
    last_was_utf8 = 0;
    return 0x7F;
  }

  // regular ASCII character
  if (c < 0x80) {
    last_was_utf8 = 0;
    return c;
  }

  // UTF-8 handling: https://en.wikipedia.org/wiki/UTF-8#Encoding

  // bytes 11xxxxxx are first bytes of UTF-8 characters
  if (c >= 0xC0) {
    last_was_utf8 = 1;
    return 0x7F;
  }

  if (last_was_utf8) {
    // bytes 10xxxxxx can be successive UTF-8 characters ...
    return 0;  // skip glyph
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
  c = convert_char(c);
  if (!c) return 0;

  // printable ASCII character
  if (c >= ' ' && c < 0x7F) {
    switch (font) {
#ifdef TREZOR_FONT_NORMAL_ENABLE
      case FONT_NORMAL:
        return FONT_NORMAL_DATA[c - ' '];
#endif
#ifdef TREZOR_FONT_DEMIBOLD_ENABLE
      case FONT_DEMIBOLD:
        return FONT_DEMIBOLD_DATA[c - ' '];
#endif
#ifdef TREZOR_FONT_BOLD_ENABLE
      case FONT_BOLD:
        return FONT_BOLD_DATA[c - ' '];
#endif
#ifdef TREZOR_FONT_MONO_ENABLE
      case FONT_MONO:
        return FONT_MONO_DATA[c - ' '];
#endif
#ifdef TREZOR_FONT_BIG_ENABLE
      case FONT_BIG:
        return FONT_BIG_DATA[c - ' '];
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
  }
  return 0;
}

// compute the width of the text (in pixels)
int font_text_width(int font, const char *text, int textlen) {
  int width = 0;
  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }
  for (int i = 0; i < textlen; i++) {
    const uint8_t *g = font_get_glyph(font, (uint8_t)text[i]);
    if (!g) continue;
    const uint8_t adv = g[2];  // advance
    width += adv;
    /*
    if (i != textlen - 1) {
        const uint8_t adv = g[2]; // advance
        width += adv;
    } else { // last character
        const uint8_t w = g[0]; // width
        const uint8_t bearX = g[3]; // bearingX
        width += (bearX + w);
    }
    */
  }
  return width;
}

// Returns how many characters of the string can be used before exceeding
// the requested width. Tries to avoid breaking words if possible.
int font_text_split(int font, const char *text, int textlen,
                    int requested_width) {
  int width = 0;
  int lastspace = 0;
  // determine text length if not provided
  if (textlen < 0) {
    textlen = strlen(text);
  }
  for (int i = 0; i < textlen; i++) {
    if (text[i] == ' ') {
      lastspace = i;
    }
    const uint8_t *g = font_get_glyph(font, (uint8_t)text[i]);
    if (!g) continue;
    const uint8_t adv = g[2];  // advance
    width += adv;
    if (width > requested_width) {
      if (lastspace > 0) {
        return lastspace;
      } else {
        return i;
      }
    }
  }
  return textlen;
}
