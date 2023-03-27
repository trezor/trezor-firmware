#include <stdint.h>

#if TREZOR_FONT_BPP != 1
#error Wrong TREZOR_FONT_BPP (expected 1)
#endif
#define Font_PixelOperator_Bold_8_HEIGHT 8
#define Font_PixelOperator_Bold_8_MAX_HEIGHT 8
#define Font_PixelOperator_Bold_8_BASELINE 1
extern const uint8_t* const Font_PixelOperator_Bold_8[126 + 1 - 32];
extern const uint8_t Font_PixelOperator_Bold_8_glyph_nonprintable[];
