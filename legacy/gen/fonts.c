#include "fonts.h"

const uint8_t * const font_data[2][128] = {
	{
#include"font.inc"
	},
	{
#include"fontfixed.inc"
	},
};

int fontCharWidth(int font, char c) {
	return font_data[font][c & 0x7f][0];
}

const uint8_t *fontCharData(int font, char c) {
	return font_data[font][c & 0x7f] + 1;
}
