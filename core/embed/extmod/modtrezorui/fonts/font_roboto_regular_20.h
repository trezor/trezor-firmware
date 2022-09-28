#include <stdint.h>

#if TREZOR_FONT_BPP != 4
#error Wrong TREZOR_FONT_BPP (expected 4)
#endif
#define Font_Roboto_Regular_20_HEIGHT 20
#define Font_Roboto_Regular_20_MAX_HEIGHT 22
#define Font_Roboto_Regular_20_BASELINE 5
extern const uint8_t* const Font_Roboto_Regular_20[126 + 1 - 32];
extern const uint8_t Font_Roboto_Regular_20_glyph_nonprintable[];
