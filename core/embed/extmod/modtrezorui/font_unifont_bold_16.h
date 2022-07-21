#include <stdint.h>

#if TREZOR_FONT_BPP != 1
#error Wrong TREZOR_FONT_BPP (expected 1)
#endif
extern const uint8_t* const Font_Unifont_Bold_16[126 + 1 - 32];
extern const uint8_t Font_Unifont_Bold_16_glyph_nonprintable[];
