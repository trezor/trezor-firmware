#include <stdint.h>

#if TREZOR_FONT_BPP != 4
#error Wrong TREZOR_FONT_BPP (expected 4)
#endif
#define Font_TTHoves_Bold_16_HEIGHT 16
#define Font_TTHoves_Bold_16_MAX_HEIGHT 17
#define Font_TTHoves_Bold_16_BASELINE 4
extern const uint8_t* const Font_TTHoves_Bold_16[126 + 1 - 32];
extern const uint8_t Font_TTHoves_Bold_16_glyph_nonprintable[];
