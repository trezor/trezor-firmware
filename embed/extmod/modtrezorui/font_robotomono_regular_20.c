#include "font_robotomono_regular_20.h"

// first two bytes are width and height of the glyph
// third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph
// rest is packed 4-bit glyph data

/*   */ static const uint8_t Font_RobotoMono_Regular_20_glyph_32[] = { 0, 0, 12, 0, 0 };
/* ! */ static const uint8_t Font_RobotoMono_Regular_20_glyph_33[] = { 3, 15, 12, 4, 15, 56, 227, 142, 56, 227, 142, 56, 224, 0, 0, 243, 192 };
/* " */ static const uint8_t Font_RobotoMono_Regular_20_glyph_34[] = { 6, 5, 12, 3, 15, 176, 219, 13, 176, 219, 13, 176, 192 };
/* # */ static const uint8_t Font_RobotoMono_Regular_20_glyph_35[] = { 12, 15, 12, 0, 15, 0, 48, 48, 0, 112, 112, 0, 176, 176, 0, 224, 224, 47, 255, 254, 26, 234, 233, 1, 193, 192, 1, 194, 192, 2, 130, 128, 43, 235, 228, 127, 255, 252, 3, 3, 0, 7, 7, 0, 11, 11, 0, 10, 14, 0, 0 };
/* $ */ static const uint8_t Font_RobotoMono_Regular_20_glyph_36[] = { 10, 19, 12, 1, 17, 0, 112, 0, 7, 0, 1, 184, 0, 191, 244, 30, 7, 194, 192, 45, 60, 1, 210, 208, 0, 31, 64, 0, 127, 128, 0, 191, 64, 0, 188, 0, 1, 231, 64, 14, 56, 1, 227, 224, 124, 11, 255, 64, 11, 0, 0, 176, 0 };
/* % */ static const uint8_t Font_RobotoMono_Regular_20_glyph_37[] = { 12, 15, 12, 0, 15, 31, 128, 0, 58, 208, 0, 176, 224, 128, 176, 161, 192, 112, 227, 64, 63, 203, 0, 5, 13, 0, 0, 44, 0, 0, 48, 80, 0, 163, 252, 1, 203, 13, 3, 138, 14, 2, 10, 13, 0, 7, 172, 0, 2, 244, 0 };
/* & */ static const uint8_t Font_RobotoMono_Regular_20_glyph_38[] = { 11, 15, 12, 1, 15, 7, 244, 0, 62, 244, 2, 208, 224, 11, 3, 192, 45, 29, 0, 62, 224, 0, 190, 0, 3, 244, 0, 61, 240, 114, 209, 226, 207, 2, 223, 60, 3, 244, 180, 11, 192, 250, 255, 128, 191, 79, 64 };
/* ' */ static const uint8_t Font_RobotoMono_Regular_20_glyph_39[] = { 3, 5, 12, 4, 15, 52, 211, 77, 48 };
/* ( */ static const uint8_t Font_RobotoMono_Regular_20_glyph_40[] = { 6, 22, 12, 3, 17, 0, 0, 5, 1, 208, 116, 15, 1, 208, 44, 3, 128, 120, 7, 64, 116, 7, 64, 116, 7, 64, 56, 3, 192, 44, 0, 208, 11, 0, 56, 0, 208, 0, 0 };
/* ) */ static const uint8_t Font_RobotoMono_Regular_20_glyph_41[] = { 6, 22, 12, 3, 17, 0, 9, 0, 116, 2, 192, 14, 0, 176, 3, 128, 60, 3, 192, 44, 2, 192, 45, 2, 192, 44, 3, 192, 56, 7, 64, 176, 13, 3, 128, 176, 4, 0, 0 };
/* * */ static const uint8_t Font_RobotoMono_Regular_20_glyph_42[] = { 10, 10, 12, 1, 12, 0, 176, 0, 11, 0, 0, 112, 3, 151, 30, 47, 255, 224, 15, 128, 2, 236, 0, 116, 224, 15, 7, 64, 64, 32, 0 };
/* + */ static const uint8_t Font_RobotoMono_Regular_20_glyph_43[] = { 10, 11, 12, 1, 12, 0, 240, 0, 15, 0, 0, 240, 0, 15, 0, 0, 240, 15, 255, 255, 106, 250, 144, 15, 0, 0, 240, 0, 15, 0, 0, 240, 0 };
/* , */ static const uint8_t Font_RobotoMono_Regular_20_glyph_44[] = { 4, 6, 12, 3, 2, 45, 45, 60, 60, 116, 16, 0 };
/* - */ static const uint8_t Font_RobotoMono_Regular_20_glyph_45[] = { 8, 2, 12, 2, 8, 106, 169, 255, 254, 0 };
/* . */ static const uint8_t Font_RobotoMono_Regular_20_glyph_46[] = { 4, 3, 12, 4, 3, 44, 62, 45, 0 };
/* / */ static const uint8_t Font_RobotoMono_Regular_20_glyph_47[] = { 9, 16, 12, 2, 15, 0, 15, 0, 3, 64, 2, 192, 0, 224, 0, 116, 0, 44, 0, 14, 0, 7, 0, 3, 192, 0, 208, 0, 176, 0, 56, 0, 28, 0, 15, 0, 3, 64, 0, 64, 0, 0 };
/* 0 */ static const uint8_t Font_RobotoMono_Regular_20_glyph_48[] = { 10, 15, 12, 1, 15, 6, 253, 1, 250, 244, 60, 3, 199, 128, 29, 116, 1, 235, 0, 126, 176, 46, 235, 15, 78, 187, 192, 235, 224, 14, 120, 1, 231, 64, 29, 60, 3, 193, 250, 244, 6, 253, 0 };
/* 1 */ static const uint8_t Font_RobotoMono_Regular_20_glyph_49[] = { 6, 15, 12, 2, 15, 0, 16, 126, 191, 238, 94, 1, 224, 30, 1, 224, 30, 1, 224, 30, 1, 224, 30, 1, 224, 30, 1, 224 };
/* 2 */ static const uint8_t Font_RobotoMono_Regular_20_glyph_50[] = { 11, 15, 12, 0, 15, 2, 254, 0, 62, 191, 2, 208, 45, 15, 0, 56, 36, 0, 224, 0, 7, 64, 0, 60, 0, 2, 208, 0, 30, 0, 1, 240, 0, 15, 0, 0, 240, 0, 15, 0, 0, 190, 170, 131, 255, 255, 64 };
/* 3 */ static const uint8_t Font_RobotoMono_Regular_20_glyph_51[] = { 10, 15, 12, 0, 15, 2, 254, 0, 250, 188, 45, 2, 211, 192, 14, 0, 0, 224, 0, 45, 0, 175, 128, 15, 244, 0, 7, 208, 0, 14, 0, 0, 243, 192, 15, 61, 1, 224, 250, 188, 2, 254, 0 };
/* 4 */ static const uint8_t Font_RobotoMono_Regular_20_glyph_52[] = { 11, 15, 12, 0, 15, 0, 3, 192, 0, 63, 0, 1, 252, 0, 14, 240, 0, 179, 192, 7, 79, 0, 60, 60, 1, 208, 240, 14, 3, 192, 176, 15, 3, 255, 255, 202, 170, 250, 0, 3, 192, 0, 15, 0, 0, 60, 0 };
/* 5 */ static const uint8_t Font_RobotoMono_Regular_20_glyph_53[] = { 10, 15, 12, 1, 15, 15, 255, 208, 250, 168, 13, 0, 1, 208, 0, 29, 0, 1, 213, 64, 47, 255, 65, 208, 124, 0, 1, 224, 0, 14, 0, 0, 227, 128, 14, 60, 2, 208, 250, 248, 2, 254, 0 };
/* 6 */ static const uint8_t Font_RobotoMono_Regular_20_glyph_54[] = { 10, 15, 12, 1, 15, 0, 189, 0, 127, 128, 15, 64, 2, 208, 0, 56, 0, 7, 69, 64, 123, 255, 11, 208, 184, 180, 3, 203, 0, 45, 180, 1, 215, 128, 44, 60, 3, 192, 250, 244, 2, 248, 0 };
/* 7 */ static const uint8_t Font_RobotoMono_Regular_20_glyph_55[] = { 10, 15, 12, 1, 15, 255, 255, 230, 170, 173, 0, 2, 192, 0, 56, 0, 11, 0, 0, 240, 0, 29, 0, 3, 192, 0, 120, 0, 11, 0, 0, 224, 0, 45, 0, 3, 192, 0, 116, 0, 15, 0, 0 };
/* 8 */ static const uint8_t Font_RobotoMono_Regular_20_glyph_56[] = { 10, 15, 12, 1, 15, 2, 253, 0, 250, 248, 45, 3, 195, 192, 29, 60, 1, 210, 208, 60, 15, 175, 64, 127, 240, 30, 7, 195, 192, 29, 56, 0, 227, 128, 14, 60, 2, 209, 250, 252, 2, 253, 0 };
/* 9 */ static const uint8_t Font_RobotoMono_Regular_20_glyph_57[] = { 10, 15, 12, 1, 15, 7, 248, 1, 250, 240, 60, 7, 135, 64, 60, 180, 2, 215, 64, 29, 116, 2, 211, 192, 61, 47, 175, 208, 127, 108, 0, 2, 192, 0, 56, 0, 15, 0, 111, 208, 11, 224, 0 };
/* : */ static const uint8_t Font_RobotoMono_Regular_20_glyph_58[] = { 4, 12, 12, 4, 12, 44, 62, 45, 0, 0, 0, 0, 0, 0, 44, 62, 45, 0 };
/* ; */ static const uint8_t Font_RobotoMono_Regular_20_glyph_59[] = { 4, 16, 12, 4, 12, 44, 62, 45, 0, 0, 0, 0, 0, 0, 0, 45, 45, 60, 60, 116, 16, 0 };
/* < */ static const uint8_t Font_RobotoMono_Regular_20_glyph_60[] = { 9, 10, 12, 1, 11, 0, 0, 64, 2, 240, 31, 244, 127, 128, 125, 0, 15, 224, 0, 47, 208, 0, 191, 0, 1, 192, 0, 0 };
/* = */ static const uint8_t Font_RobotoMono_Regular_20_glyph_61[] = { 10, 6, 12, 1, 10, 42, 170, 135, 255, 253, 0, 0, 0, 0, 0, 42, 170, 135, 255, 253, 0 };
/* > */ static const uint8_t Font_RobotoMono_Regular_20_glyph_62[] = { 10, 10, 12, 1, 11, 16, 0, 7, 224, 0, 31, 228, 0, 11, 244, 0, 7, 208, 2, 248, 7, 248, 3, 244, 0, 116, 0, 0, 0, 0, 0 };
/* ? */ static const uint8_t Font_RobotoMono_Regular_20_glyph_63[] = { 10, 15, 12, 1, 15, 6, 253, 1, 250, 248, 60, 3, 194, 64, 44, 0, 2, 192, 0, 60, 0, 15, 64, 3, 224, 0, 184, 0, 15, 0, 0, 224, 0, 0, 0, 0, 0, 0, 15, 0, 0, 240, 0 };
/* @ */ static const uint8_t Font_RobotoMono_Regular_20_glyph_64[] = { 12, 15, 12, 0, 15, 0, 127, 64, 3, 234, 224, 11, 0, 52, 28, 5, 28, 40, 127, 76, 48, 226, 76, 49, 194, 77, 113, 131, 13, 114, 131, 12, 114, 131, 12, 49, 239, 184, 56, 245, 224, 29, 0, 0, 11, 234, 64, 1, 254, 0, 0 };
/* A */ static const uint8_t Font_RobotoMono_Regular_20_glyph_65[] = { 12, 15, 12, 0, 15, 0, 60, 0, 0, 61, 0, 0, 126, 0, 0, 191, 0, 0, 231, 0, 1, 211, 128, 2, 195, 192, 3, 194, 192, 3, 129, 208, 11, 170, 224, 15, 255, 240, 14, 0, 116, 29, 0, 56, 44, 0, 60, 56, 0, 45, 0 };
/* B */ static const uint8_t Font_RobotoMono_Regular_20_glyph_66[] = { 10, 15, 12, 1, 15, 127, 253, 7, 234, 248, 120, 3, 215, 128, 29, 120, 1, 215, 128, 60, 126, 175, 71, 255, 240, 120, 7, 199, 128, 14, 120, 0, 247, 128, 15, 120, 2, 231, 234, 252, 127, 253, 0 };
/* C */ static const uint8_t Font_RobotoMono_Regular_20_glyph_67[] = { 10, 15, 12, 1, 15, 2, 253, 1, 250, 248, 60, 3, 215, 64, 14, 176, 0, 175, 0, 0, 240, 0, 15, 0, 0, 240, 0, 15, 0, 0, 176, 0, 167, 64, 14, 60, 2, 193, 250, 248, 2, 253, 0 };
/* D */ static const uint8_t Font_RobotoMono_Regular_20_glyph_68[] = { 11, 15, 12, 1, 15, 127, 244, 1, 234, 252, 7, 64, 124, 29, 0, 180, 116, 0, 225, 208, 3, 199, 64, 11, 29, 0, 44, 116, 0, 177, 208, 3, 199, 64, 14, 29, 0, 180, 116, 7, 193, 234, 252, 7, 255, 64, 0 };
/* E */ static const uint8_t Font_RobotoMono_Regular_20_glyph_69[] = { 10, 15, 12, 1, 15, 63, 255, 211, 234, 168, 56, 0, 3, 128, 0, 56, 0, 3, 128, 0, 56, 0, 3, 255, 248, 62, 170, 67, 128, 0, 56, 0, 3, 128, 0, 56, 0, 3, 234, 169, 63, 255, 224 };
/* F */ static const uint8_t Font_RobotoMono_Regular_20_glyph_70[] = { 10, 15, 12, 1, 15, 63, 255, 227, 234, 169, 56, 0, 3, 128, 0, 56, 0, 3, 128, 0, 56, 0, 3, 255, 248, 62, 170, 67, 128, 0, 56, 0, 3, 128, 0, 56, 0, 3, 128, 0, 56, 0, 0 };
/* G */ static const uint8_t Font_RobotoMono_Regular_20_glyph_71[] = { 11, 15, 12, 0, 15, 0, 191, 64, 31, 175, 128, 240, 11, 71, 64, 14, 44, 0, 20, 240, 0, 3, 192, 0, 15, 1, 169, 60, 11, 252, 240, 0, 242, 192, 3, 199, 64, 15, 15, 0, 60, 15, 171, 208, 11, 248, 0 };
/* H */ static const uint8_t Font_RobotoMono_Regular_20_glyph_72[] = { 10, 15, 12, 1, 15, 176, 0, 235, 0, 14, 176, 0, 235, 0, 14, 176, 0, 235, 0, 14, 176, 0, 235, 255, 254, 186, 170, 235, 0, 14, 176, 0, 235, 0, 14, 176, 0, 235, 0, 14, 176, 0, 224 };
/* I */ static const uint8_t Font_RobotoMono_Regular_20_glyph_73[] = { 10, 15, 12, 1, 15, 127, 255, 210, 175, 168, 0, 240, 0, 15, 0, 0, 240, 0, 15, 0, 0, 240, 0, 15, 0, 0, 240, 0, 15, 0, 0, 240, 0, 15, 0, 0, 240, 2, 175, 168, 127, 255, 208 };
/* J */ static const uint8_t Font_RobotoMono_Regular_20_glyph_74[] = { 11, 15, 12, 0, 15, 0, 0, 176, 0, 2, 192, 0, 11, 0, 0, 44, 0, 0, 176, 0, 2, 192, 0, 11, 0, 0, 44, 0, 0, 176, 0, 2, 193, 64, 11, 15, 0, 60, 46, 1, 224, 63, 175, 0, 47, 224, 0 };
/* K */ static const uint8_t Font_RobotoMono_Regular_20_glyph_75[] = { 11, 15, 12, 1, 15, 120, 1, 241, 224, 15, 7, 128, 244, 30, 11, 128, 120, 124, 1, 227, 192, 7, 189, 0, 31, 252, 0, 127, 184, 1, 240, 240, 7, 129, 240, 30, 3, 208, 120, 3, 193, 224, 11, 135, 128, 15, 64 };
/* L */ static const uint8_t Font_RobotoMono_Regular_20_glyph_76[] = { 10, 15, 12, 1, 15, 56, 0, 3, 128, 0, 56, 0, 3, 128, 0, 56, 0, 3, 128, 0, 56, 0, 3, 128, 0, 56, 0, 3, 128, 0, 56, 0, 3, 128, 0, 56, 0, 3, 234, 169, 63, 255, 224 };
/* M */ static const uint8_t Font_RobotoMono_Regular_20_glyph_77[] = { 10, 15, 12, 1, 15, 188, 2, 251, 192, 63, 189, 7, 251, 240, 191, 187, 14, 251, 117, 207, 179, 172, 251, 47, 143, 177, 244, 251, 15, 15, 176, 160, 251, 0, 15, 176, 0, 251, 0, 15, 176, 0, 240 };
/* N */ static const uint8_t Font_RobotoMono_Regular_20_glyph_78[] = { 10, 15, 12, 1, 15, 180, 0, 235, 192, 14, 189, 0, 235, 240, 14, 187, 64, 235, 124, 14, 177, 208, 235, 15, 14, 176, 116, 235, 3, 222, 176, 30, 235, 0, 254, 176, 7, 235, 0, 62, 176, 1, 224 };
/* O */ static const uint8_t Font_RobotoMono_Regular_20_glyph_79[] = { 10, 15, 12, 1, 15, 2, 248, 1, 250, 240, 60, 3, 199, 64, 29, 176, 0, 239, 0, 15, 240, 0, 255, 0, 15, 240, 0, 255, 0, 15, 176, 0, 231, 64, 29, 60, 3, 193, 250, 244, 2, 248, 0 };
/* P */ static const uint8_t Font_RobotoMono_Regular_20_glyph_80[] = { 11, 15, 12, 1, 15, 63, 254, 0, 250, 175, 3, 128, 30, 14, 0, 60, 56, 0, 176, 224, 3, 195, 128, 30, 15, 170, 240, 63, 254, 0, 224, 0, 3, 128, 0, 14, 0, 0, 56, 0, 0, 224, 0, 3, 128, 0, 0 };
/* Q */ static const uint8_t Font_RobotoMono_Regular_20_glyph_81[] = { 12, 18, 12, 0, 15, 0, 190, 0, 7, 235, 208, 15, 0, 240, 29, 0, 116, 60, 0, 56, 60, 0, 60, 56, 0, 44, 56, 0, 44, 56, 0, 44, 60, 0, 60, 60, 0, 60, 29, 0, 116, 15, 0, 240, 7, 235, 208, 0, 191, 208, 0, 0, 248, 0, 0, 44, 0, 0, 0, 0 };
/* R */ static const uint8_t Font_RobotoMono_Regular_20_glyph_82[] = { 11, 15, 12, 1, 15, 63, 253, 0, 250, 190, 3, 128, 61, 14, 0, 56, 56, 0, 224, 224, 3, 131, 128, 61, 15, 171, 224, 63, 253, 0, 224, 120, 3, 128, 240, 14, 1, 208, 56, 3, 192, 224, 7, 67, 128, 15, 0 };
/* S */ static const uint8_t Font_RobotoMono_Regular_20_glyph_83[] = { 11, 15, 12, 1, 15, 2, 253, 0, 126, 190, 3, 192, 45, 30, 0, 60, 120, 0, 80, 244, 0, 1, 253, 0, 0, 191, 128, 0, 47, 192, 0, 11, 133, 0, 15, 45, 0, 60, 124, 1, 224, 190, 175, 0, 111, 208, 0 };
/* T */ static const uint8_t Font_RobotoMono_Regular_20_glyph_84[] = { 12, 15, 12, 0, 15, 127, 255, 253, 42, 190, 168, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0 };
/* U */ static const uint8_t Font_RobotoMono_Regular_20_glyph_85[] = { 10, 15, 12, 1, 15, 176, 0, 235, 0, 14, 176, 0, 235, 0, 14, 176, 0, 235, 0, 14, 176, 0, 235, 0, 14, 176, 0, 235, 0, 14, 176, 0, 231, 64, 29, 60, 3, 193, 250, 244, 6, 248, 0 };
/* V */ static const uint8_t Font_RobotoMono_Regular_20_glyph_86[] = { 12, 15, 12, 0, 15, 60, 0, 60, 60, 0, 60, 45, 0, 116, 30, 0, 176, 15, 0, 240, 11, 1, 224, 7, 130, 208, 3, 195, 192, 3, 195, 128, 1, 219, 64, 0, 239, 0, 0, 255, 0, 0, 190, 0, 0, 124, 0, 0, 60, 0, 0 };
/* W */ static const uint8_t Font_RobotoMono_Regular_20_glyph_87[] = { 12, 15, 12, 0, 15, 52, 44, 13, 56, 60, 29, 56, 61, 29, 60, 62, 44, 60, 126, 44, 44, 187, 44, 44, 167, 60, 28, 227, 56, 29, 211, 120, 14, 195, 244, 15, 195, 244, 15, 194, 240, 15, 129, 240, 11, 129, 240, 11, 64, 240, 0 };
/* X */ static const uint8_t Font_RobotoMono_Regular_20_glyph_88[] = { 12, 15, 12, 0, 15, 61, 0, 60, 15, 0, 180, 11, 64, 240, 3, 194, 208, 2, 231, 192, 0, 255, 64, 0, 126, 0, 0, 61, 0, 0, 127, 0, 0, 251, 64, 2, 211, 192, 3, 194, 208, 11, 64, 240, 31, 0, 184, 60, 0, 60, 0 };
/* Y */ static const uint8_t Font_RobotoMono_Regular_20_glyph_89[] = { 12, 15, 12, 0, 15, 60, 0, 60, 45, 0, 180, 15, 0, 240, 15, 1, 224, 7, 131, 192, 3, 199, 128, 1, 239, 0, 0, 254, 0, 0, 124, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 56, 0, 0, 56, 0, 0, 56, 0, 0 };
/* Z */ static const uint8_t Font_RobotoMono_Regular_20_glyph_90[] = { 10, 15, 12, 1, 15, 255, 255, 214, 170, 188, 0, 7, 128, 0, 240, 0, 45, 0, 3, 192, 0, 180, 0, 30, 0, 3, 192, 0, 120, 0, 15, 0, 2, 208, 0, 60, 0, 15, 170, 169, 255, 255, 224 };
/* [ */ static const uint8_t Font_RobotoMono_Regular_20_glyph_91[] = { 5, 20, 12, 4, 17, 106, 63, 207, 3, 192, 240, 60, 15, 3, 192, 240, 60, 15, 3, 192, 240, 60, 15, 3, 192, 240, 60, 15, 163, 252, 0 };
/* \ */ static const uint8_t Font_RobotoMono_Regular_20_glyph_92[] = { 8, 16, 12, 2, 15, 176, 0, 52, 0, 60, 0, 28, 0, 14, 0, 11, 0, 7, 64, 3, 192, 1, 192, 0, 224, 0, 176, 0, 116, 0, 56, 0, 44, 0, 13, 0, 5, 0 };
/* ] */ static const uint8_t Font_RobotoMono_Regular_20_glyph_93[] = { 5, 20, 12, 3, 17, 42, 79, 240, 60, 15, 3, 192, 240, 60, 15, 3, 192, 240, 60, 15, 3, 192, 240, 60, 15, 3, 192, 242, 188, 255, 0 };
/* ^ */ static const uint8_t Font_RobotoMono_Regular_20_glyph_94[] = { 8, 8, 12, 2, 15, 3, 192, 3, 192, 11, 224, 14, 176, 29, 116, 60, 60, 56, 44, 176, 14, 0 };
/* _ */ static const uint8_t Font_RobotoMono_Regular_20_glyph_95[] = { 10, 2, 12, 1, 1, 42, 170, 135, 255, 253, 0 };
/* ` */ static const uint8_t Font_RobotoMono_Regular_20_glyph_96[] = { 4, 3, 12, 4, 15, 120, 29, 5, 0 };
/* a */ static const uint8_t Font_RobotoMono_Regular_20_glyph_97[] = { 10, 11, 12, 1, 11, 7, 253, 2, 250, 244, 56, 3, 192, 0, 44, 7, 255, 194, 250, 188, 120, 2, 199, 64, 44, 120, 3, 195, 234, 253, 11, 245, 208 };
/* b */ static const uint8_t Font_RobotoMono_Regular_20_glyph_98[] = { 10, 15, 12, 1, 15, 120, 0, 7, 128, 0, 120, 0, 7, 128, 0, 121, 253, 7, 250, 248, 124, 3, 199, 128, 29, 120, 1, 231, 128, 14, 120, 1, 231, 128, 29, 124, 3, 199, 250, 244, 117, 253, 0 };
/* c */ static const uint8_t Font_RobotoMono_Regular_20_glyph_99[] = { 10, 11, 12, 1, 11, 2, 253, 1, 250, 248, 60, 2, 199, 128, 29, 180, 0, 11, 0, 0, 180, 0, 7, 128, 9, 60, 2, 193, 250, 248, 2, 253, 0 };
/* d */ static const uint8_t Font_RobotoMono_Regular_20_glyph_100[] = { 10, 15, 12, 1, 15, 0, 2, 208, 0, 45, 0, 2, 208, 0, 45, 7, 250, 209, 250, 253, 60, 3, 215, 128, 45, 180, 2, 219, 0, 45, 180, 2, 215, 64, 45, 60, 3, 209, 250, 253, 7, 249, 208 };
/* e */ static const uint8_t Font_RobotoMono_Regular_20_glyph_101[] = { 10, 11, 12, 1, 11, 2, 253, 0, 250, 248, 60, 3, 199, 64, 29, 186, 170, 235, 255, 254, 176, 0, 7, 128, 0, 60, 0, 129, 250, 188, 2, 254, 0 };
/* f */ static const uint8_t Font_RobotoMono_Regular_20_glyph_102[] = { 11, 16, 12, 1, 16, 0, 5, 64, 1, 255, 192, 15, 64, 0, 180, 0, 2, 192, 2, 255, 255, 70, 190, 168, 0, 176, 0, 2, 192, 0, 11, 0, 0, 44, 0, 0, 176, 0, 2, 192, 0, 11, 0, 0, 44, 0, 0, 176, 0, 0 };
/* g */ static const uint8_t Font_RobotoMono_Regular_20_glyph_103[] = { 10, 15, 12, 1, 11, 7, 249, 209, 250, 253, 60, 3, 215, 128, 45, 180, 2, 219, 0, 45, 180, 2, 215, 64, 45, 60, 3, 209, 250, 253, 7, 250, 208, 0, 44, 36, 3, 194, 234, 244, 7, 248, 0 };
/* h */ static const uint8_t Font_RobotoMono_Regular_20_glyph_104[] = { 10, 15, 12, 1, 15, 120, 0, 7, 128, 0, 120, 0, 7, 128, 0, 120, 254, 7, 186, 252, 124, 3, 199, 128, 29, 120, 1, 215, 128, 29, 120, 1, 215, 128, 29, 120, 1, 215, 128, 29, 120, 1, 208 };
/* i */ static const uint8_t Font_RobotoMono_Regular_20_glyph_105[] = { 10, 15, 12, 1, 15, 0, 116, 0, 11, 64, 0, 0, 0, 0, 0, 63, 244, 2, 171, 64, 0, 116, 0, 7, 64, 0, 116, 0, 7, 64, 0, 116, 0, 7, 64, 0, 116, 2, 171, 169, 63, 255, 240 };
/* j */ static const uint8_t Font_RobotoMono_Regular_20_glyph_106[] = { 7, 19, 12, 2, 15, 0, 176, 2, 192, 0, 0, 0, 63, 244, 171, 208, 11, 64, 45, 0, 180, 2, 208, 11, 64, 45, 0, 180, 2, 208, 11, 0, 44, 0, 241, 175, 79, 244, 0 };
/* k */ static const uint8_t Font_RobotoMono_Regular_20_glyph_107[] = { 11, 15, 12, 1, 15, 120, 0, 1, 224, 0, 7, 128, 0, 30, 0, 0, 120, 7, 193, 224, 124, 7, 131, 192, 30, 60, 0, 123, 208, 1, 255, 192, 7, 219, 128, 30, 15, 64, 120, 15, 1, 224, 31, 7, 128, 46, 0 };
/* l */ static const uint8_t Font_RobotoMono_Regular_20_glyph_108[] = { 10, 15, 12, 1, 15, 63, 244, 2, 171, 64, 0, 116, 0, 7, 64, 0, 116, 0, 7, 64, 0, 116, 0, 7, 64, 0, 116, 0, 7, 64, 0, 116, 0, 7, 64, 0, 116, 2, 171, 169, 63, 255, 240 };
/* m */ static const uint8_t Font_RobotoMono_Regular_20_glyph_109[] = { 12, 11, 12, 0, 11, 58, 242, 240, 62, 190, 188, 56, 60, 44, 56, 60, 44, 56, 60, 44, 56, 60, 44, 56, 60, 44, 56, 60, 44, 56, 60, 44, 56, 60, 44, 56, 60, 44, 0 };
/* n */ static const uint8_t Font_RobotoMono_Regular_20_glyph_110[] = { 10, 11, 12, 1, 11, 117, 254, 7, 186, 248, 124, 3, 199, 128, 29, 120, 1, 215, 128, 29, 120, 1, 215, 128, 29, 120, 1, 215, 128, 29, 120, 1, 208 };
/* o */ static const uint8_t Font_RobotoMono_Regular_20_glyph_111[] = { 10, 11, 12, 1, 11, 6, 249, 1, 250, 244, 60, 3, 203, 64, 30, 176, 0, 239, 0, 15, 176, 0, 235, 64, 30, 60, 3, 193, 250, 244, 7, 253, 0 };
/* p */ static const uint8_t Font_RobotoMono_Regular_20_glyph_112[] = { 10, 15, 12, 1, 11, 118, 253, 7, 250, 244, 124, 3, 199, 128, 45, 120, 1, 231, 128, 14, 120, 1, 231, 128, 45, 124, 3, 199, 250, 244, 122, 253, 7, 128, 0, 120, 0, 7, 128, 0, 120, 0, 0 };
/* q */ static const uint8_t Font_RobotoMono_Regular_20_glyph_113[] = { 10, 15, 12, 1, 11, 7, 249, 209, 250, 253, 60, 3, 215, 128, 45, 180, 2, 219, 0, 45, 180, 2, 215, 128, 45, 60, 3, 209, 250, 253, 7, 250, 208, 0, 45, 0, 2, 208, 0, 45, 0, 2, 208 };
/* r */ static const uint8_t Font_RobotoMono_Regular_20_glyph_114[] = { 8, 11, 12, 3, 11, 241, 253, 255, 168, 252, 0, 240, 0, 240, 0, 240, 0, 240, 0, 240, 0, 240, 0, 240, 0, 240, 0, 0 };
/* s */ static const uint8_t Font_RobotoMono_Regular_20_glyph_115[] = { 10, 11, 12, 1, 11, 2, 253, 1, 250, 248, 60, 2, 211, 192, 4, 31, 144, 0, 111, 224, 0, 27, 194, 64, 29, 60, 1, 209, 250, 188, 6, 254, 0 };
/* t */ static const uint8_t Font_RobotoMono_Regular_20_glyph_116[] = { 10, 14, 12, 1, 14, 1, 64, 0, 60, 0, 3, 192, 11, 255, 252, 107, 234, 128, 60, 0, 3, 192, 0, 60, 0, 3, 192, 0, 60, 0, 3, 192, 0, 44, 0, 1, 250, 128, 7, 252, 0 };
/* u */ static const uint8_t Font_RobotoMono_Regular_20_glyph_117[] = { 10, 11, 12, 1, 11, 56, 2, 211, 128, 45, 56, 2, 211, 128, 45, 56, 2, 211, 128, 45, 56, 2, 211, 128, 45, 60, 3, 210, 250, 253, 11, 245, 208 };
/* v */ static const uint8_t Font_RobotoMono_Regular_20_glyph_118[] = { 11, 11, 12, 0, 11, 60, 0, 60, 116, 1, 208, 224, 11, 2, 192, 56, 7, 65, 192, 15, 15, 0, 28, 52, 0, 58, 192, 0, 190, 0, 1, 244, 0, 3, 192, 0 };
/* w */ static const uint8_t Font_RobotoMono_Regular_20_glyph_119[] = { 12, 11, 12, 0, 11, 112, 40, 14, 52, 60, 13, 56, 60, 28, 56, 125, 44, 44, 170, 40, 28, 215, 56, 13, 195, 52, 14, 195, 176, 15, 130, 240, 11, 129, 224, 7, 64, 208, 0 };
/* x */ static const uint8_t Font_RobotoMono_Regular_20_glyph_120[] = { 11, 11, 12, 1, 11, 120, 1, 224, 180, 15, 0, 240, 240, 1, 251, 64, 2, 252, 0, 3, 208, 0, 47, 192, 1, 231, 128, 15, 11, 64, 240, 15, 11, 128, 30, 0 };
/* y */ static const uint8_t Font_RobotoMono_Regular_20_glyph_121[] = { 12, 15, 12, 0, 11, 60, 0, 60, 45, 0, 120, 14, 0, 176, 15, 0, 240, 7, 129, 208, 3, 195, 192, 1, 215, 64, 0, 251, 0, 0, 190, 0, 0, 60, 0, 0, 56, 0, 0, 116, 0, 0, 240, 0, 11, 192, 0, 31, 64, 0, 0 };
/* z */ static const uint8_t Font_RobotoMono_Regular_20_glyph_122[] = { 10, 11, 12, 1, 11, 127, 255, 210, 170, 188, 0, 15, 64, 2, 224, 0, 120, 0, 15, 0, 3, 192, 0, 244, 0, 46, 0, 7, 234, 169, 127, 255, 224 };
/* { */ static const uint8_t Font_RobotoMono_Regular_20_glyph_123[] = { 7, 20, 12, 3, 16, 0, 20, 3, 224, 46, 0, 240, 3, 128, 14, 0, 56, 0, 224, 11, 65, 248, 15, 192, 7, 192, 7, 128, 14, 0, 56, 0, 224, 3, 192, 11, 0, 15, 64, 30, 0 };
/* | */ static const uint8_t Font_RobotoMono_Regular_20_glyph_124[] = { 2, 19, 12, 5, 15, 170, 170, 170, 170, 170, 170, 170, 170, 170, 160 };
/* } */ static const uint8_t Font_RobotoMono_Regular_20_glyph_125[] = { 7, 20, 12, 3, 16, 80, 3, 224, 2, 208, 3, 192, 15, 0, 60, 0, 240, 2, 192, 7, 128, 11, 144, 15, 192, 240, 11, 64, 44, 0, 240, 3, 192, 15, 0, 120, 7, 192, 44, 0, 0 };
/* ~ */ static const uint8_t Font_RobotoMono_Regular_20_glyph_126[] = { 12, 4, 12, 0, 8, 15, 208, 4, 62, 248, 13, 112, 47, 188, 16, 7, 240, 0 };

const uint8_t * const Font_RobotoMono_Regular_20[126 + 1 - 32] = {
    Font_RobotoMono_Regular_20_glyph_32,
    Font_RobotoMono_Regular_20_glyph_33,
    Font_RobotoMono_Regular_20_glyph_34,
    Font_RobotoMono_Regular_20_glyph_35,
    Font_RobotoMono_Regular_20_glyph_36,
    Font_RobotoMono_Regular_20_glyph_37,
    Font_RobotoMono_Regular_20_glyph_38,
    Font_RobotoMono_Regular_20_glyph_39,
    Font_RobotoMono_Regular_20_glyph_40,
    Font_RobotoMono_Regular_20_glyph_41,
    Font_RobotoMono_Regular_20_glyph_42,
    Font_RobotoMono_Regular_20_glyph_43,
    Font_RobotoMono_Regular_20_glyph_44,
    Font_RobotoMono_Regular_20_glyph_45,
    Font_RobotoMono_Regular_20_glyph_46,
    Font_RobotoMono_Regular_20_glyph_47,
    Font_RobotoMono_Regular_20_glyph_48,
    Font_RobotoMono_Regular_20_glyph_49,
    Font_RobotoMono_Regular_20_glyph_50,
    Font_RobotoMono_Regular_20_glyph_51,
    Font_RobotoMono_Regular_20_glyph_52,
    Font_RobotoMono_Regular_20_glyph_53,
    Font_RobotoMono_Regular_20_glyph_54,
    Font_RobotoMono_Regular_20_glyph_55,
    Font_RobotoMono_Regular_20_glyph_56,
    Font_RobotoMono_Regular_20_glyph_57,
    Font_RobotoMono_Regular_20_glyph_58,
    Font_RobotoMono_Regular_20_glyph_59,
    Font_RobotoMono_Regular_20_glyph_60,
    Font_RobotoMono_Regular_20_glyph_61,
    Font_RobotoMono_Regular_20_glyph_62,
    Font_RobotoMono_Regular_20_glyph_63,
    Font_RobotoMono_Regular_20_glyph_64,
    Font_RobotoMono_Regular_20_glyph_65,
    Font_RobotoMono_Regular_20_glyph_66,
    Font_RobotoMono_Regular_20_glyph_67,
    Font_RobotoMono_Regular_20_glyph_68,
    Font_RobotoMono_Regular_20_glyph_69,
    Font_RobotoMono_Regular_20_glyph_70,
    Font_RobotoMono_Regular_20_glyph_71,
    Font_RobotoMono_Regular_20_glyph_72,
    Font_RobotoMono_Regular_20_glyph_73,
    Font_RobotoMono_Regular_20_glyph_74,
    Font_RobotoMono_Regular_20_glyph_75,
    Font_RobotoMono_Regular_20_glyph_76,
    Font_RobotoMono_Regular_20_glyph_77,
    Font_RobotoMono_Regular_20_glyph_78,
    Font_RobotoMono_Regular_20_glyph_79,
    Font_RobotoMono_Regular_20_glyph_80,
    Font_RobotoMono_Regular_20_glyph_81,
    Font_RobotoMono_Regular_20_glyph_82,
    Font_RobotoMono_Regular_20_glyph_83,
    Font_RobotoMono_Regular_20_glyph_84,
    Font_RobotoMono_Regular_20_glyph_85,
    Font_RobotoMono_Regular_20_glyph_86,
    Font_RobotoMono_Regular_20_glyph_87,
    Font_RobotoMono_Regular_20_glyph_88,
    Font_RobotoMono_Regular_20_glyph_89,
    Font_RobotoMono_Regular_20_glyph_90,
    Font_RobotoMono_Regular_20_glyph_91,
    Font_RobotoMono_Regular_20_glyph_92,
    Font_RobotoMono_Regular_20_glyph_93,
    Font_RobotoMono_Regular_20_glyph_94,
    Font_RobotoMono_Regular_20_glyph_95,
    Font_RobotoMono_Regular_20_glyph_96,
    Font_RobotoMono_Regular_20_glyph_97,
    Font_RobotoMono_Regular_20_glyph_98,
    Font_RobotoMono_Regular_20_glyph_99,
    Font_RobotoMono_Regular_20_glyph_100,
    Font_RobotoMono_Regular_20_glyph_101,
    Font_RobotoMono_Regular_20_glyph_102,
    Font_RobotoMono_Regular_20_glyph_103,
    Font_RobotoMono_Regular_20_glyph_104,
    Font_RobotoMono_Regular_20_glyph_105,
    Font_RobotoMono_Regular_20_glyph_106,
    Font_RobotoMono_Regular_20_glyph_107,
    Font_RobotoMono_Regular_20_glyph_108,
    Font_RobotoMono_Regular_20_glyph_109,
    Font_RobotoMono_Regular_20_glyph_110,
    Font_RobotoMono_Regular_20_glyph_111,
    Font_RobotoMono_Regular_20_glyph_112,
    Font_RobotoMono_Regular_20_glyph_113,
    Font_RobotoMono_Regular_20_glyph_114,
    Font_RobotoMono_Regular_20_glyph_115,
    Font_RobotoMono_Regular_20_glyph_116,
    Font_RobotoMono_Regular_20_glyph_117,
    Font_RobotoMono_Regular_20_glyph_118,
    Font_RobotoMono_Regular_20_glyph_119,
    Font_RobotoMono_Regular_20_glyph_120,
    Font_RobotoMono_Regular_20_glyph_121,
    Font_RobotoMono_Regular_20_glyph_122,
    Font_RobotoMono_Regular_20_glyph_123,
    Font_RobotoMono_Regular_20_glyph_124,
    Font_RobotoMono_Regular_20_glyph_125,
    Font_RobotoMono_Regular_20_glyph_126,
};
