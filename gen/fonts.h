#ifndef __FONTS_H__
#define __FONTS_H__

#include <stdint.h>

#define FONT_HEIGHT 8
#define FONT_STANDARD 0
#define FONT_FIXED    1
#define FONT_DOUBLE   0x80

extern const uint8_t * const font_data[2][128];

int fontCharWidth(int font, char c);
const uint8_t *fontCharData(int font, char c);

#endif
