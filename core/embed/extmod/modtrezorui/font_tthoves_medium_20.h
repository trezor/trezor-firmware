#include <stdint.h>

#if TREZOR_FONT_BPP != 4
#error Wrong TREZOR_FONT_BPP (expected 4)
#endif
extern const uint8_t* const Font_TTHoves_Medium_20[126 + 1 - 32];
extern const uint8_t Font_TTHoves_Medium_20_glyph_nonprintable[];
