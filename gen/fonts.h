#ifndef __FONTS_H__
#define __FONTS_H__

#include <stdint.h>

#define FONT_HEIGHT 8

extern const uint8_t * const font_data[256];

int fontCharWidth(char c);
const uint8_t *fontCharData(char c);

#endif
