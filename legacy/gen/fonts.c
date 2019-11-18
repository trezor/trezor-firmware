#include "fonts.h"

const uint8_t *const font_data[FONTS][128] = {
    {
#include "font.inc"
    },
#ifndef FONT_SKIP_FIXED
    {
#include "fontfixed.inc"
    },
#endif
};

int fontCharWidth(uint8_t font, uint8_t c) {
  return (c >= 0x80) ? 0 : font_data[font % FONTS][c][0];
}

const uint8_t *fontCharData(uint8_t font, uint8_t c) {
  return (c >= 0x80) ? (const uint8_t *)"" : font_data[font % FONTS][c] + 1;
}
