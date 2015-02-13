#ifndef __FONTS_H__
#define __FONTS_H__

#include <stdint.h>

#define FONT_START 32
#define FONT_END 132
#define FONT_HEIGHT 8

int fontCharWidth(char c);
int fontStringWidth(const char *s);

extern const uint8_t *font_data[FONT_END - FONT_START + 1];

#endif
