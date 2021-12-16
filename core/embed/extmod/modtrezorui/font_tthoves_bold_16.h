#include <stdint.h>

#if TREZOR_FONT_BPP != 4
#error Wrong TREZOR_FONT_BPP (expected 4)
#endif
extern const uint8_t* const Font_TTHoves_Bold_16[126 + 1 - 32];
extern const uint8_t Font_TTHoves_Bold_16_glyph_nonprintable[];
