#ifndef _FONTS_TYPES_H
#define _FONTS_TYPES_H

#include <stdint.h>

/// Font information structure containing metadata and pointers to font data
typedef struct {
  int height;
  int max_height;
  int baseline;
  const uint8_t* const* glyph_data;
  const uint8_t* glyph_nonprintable;
} font_info_t;

/// Font identifiers
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

/// Font glyph iterator structure
typedef struct {
  const int font;
  const uint8_t* text;
  int remaining;
} font_glyph_iter_t;

#endif  // _FONTS_TYPES_H
