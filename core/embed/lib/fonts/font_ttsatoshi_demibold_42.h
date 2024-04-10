#include <stdint.h>

#if TREZOR_FONT_BPP != 4
#error Wrong TREZOR_FONT_BPP (expected 4)
#endif
#define Font_TTSatoshi_DemiBold_42_HEIGHT 42
#define Font_TTSatoshi_DemiBold_42_MAX_HEIGHT 44
#define Font_TTSatoshi_DemiBold_42_BASELINE 9
extern const uint8_t* const Font_TTSatoshi_DemiBold_42[126 + 1 - 32];
extern const uint8_t Font_TTSatoshi_DemiBold_42_glyph_nonprintable[];
