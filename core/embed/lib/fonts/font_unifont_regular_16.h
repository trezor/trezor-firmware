#include <stdint.h>

#if TREZOR_FONT_BPP != 1
#error Wrong TREZOR_FONT_BPP (expected 1)
#endif
#define Font_Unifont_Regular_16_HEIGHT 12      // <--- 12 from 16
#define Font_Unifont_Regular_16_MAX_HEIGHT 12  // <--- 12 from 15
#define Font_Unifont_Regular_16_BASELINE 2
extern const uint8_t* const Font_Unifont_Regular_16[126 + 1 - 32];
extern const uint8_t Font_Unifont_Regular_16_glyph_nonprintable[];
