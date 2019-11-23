#ifndef __FONTS_H__
#define __FONTS_H__

#include <stdint.h>

#define FONT_HEIGHT 8
#define FONT_STANDARD 0

#ifndef FONT_SKIP_FIXED
#define FONT_FIXED 1
#define FONTS 2
#else
#define FONTS 1
#endif

#define FONT_DOUBLE 0x80

#define CHAR_BCKSPC '\x08'  // Backspace
#define CHAR_SPACE '\x09'
#define CHAR_DONE '\x06'

#define CHAR_FULL_WIDTH (5 + 1)

extern const uint8_t *const font_data[FONTS][128];

int fontCharWidth(uint8_t font, uint8_t c);
const uint8_t *fontCharData(uint8_t font, uint8_t c);

#endif
