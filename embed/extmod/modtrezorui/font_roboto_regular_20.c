#include "font_roboto_regular_20.h"

// first two bytes are width and height of the glyph
// third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph
// rest is packed 4-bit glyph data

/*   */ static const uint8_t Font_Roboto_Regular_20_glyph_32[] = { 0, 0, 5, 0, 0 };
/* ! */ static const uint8_t Font_Roboto_Regular_20_glyph_33[] = { 2, 15, 5, 2, 15, 255, 255, 255, 255, 255, 0, 4, 224 };
/* " */ static const uint8_t Font_Roboto_Regular_20_glyph_34[] = { 4, 5, 6, 1, 15, 255, 255, 239, 239, 222, 0 };
/* # */ static const uint8_t Font_Roboto_Regular_20_glyph_35[] = { 11, 15, 13, 1, 15, 0, 160, 208, 3, 67, 64, 13, 12, 0, 48, 112, 63, 255, 252, 175, 175, 160, 40, 52, 0, 208, 192, 3, 71, 2, 174, 174, 143, 255, 255, 2, 195, 128, 14, 13, 0, 52, 48, 0, 193, 192, 0 };
/* $ */ static const uint8_t Font_Roboto_Regular_20_glyph_36[] = { 9, 19, 11, 1, 17, 0, 240, 0, 60, 0, 47, 64, 191, 252, 124, 15, 108, 0, 255, 0, 62, 208, 0, 126, 0, 7, 249, 0, 31, 224, 0, 126, 0, 3, 252, 0, 255, 0, 61, 240, 45, 31, 254, 0, 60, 0, 15, 0 };
/* % */ static const uint8_t Font_Roboto_Regular_20_glyph_37[] = { 13, 15, 15, 1, 15, 47, 128, 0, 46, 184, 0, 15, 15, 3, 67, 195, 193, 192, 240, 240, 208, 46, 184, 224, 2, 248, 112, 0, 0, 52, 0, 0, 40, 190, 0, 28, 186, 224, 13, 60, 60, 10, 15, 15, 3, 3, 195, 192, 0, 186, 224, 0, 11, 224 };
/* & */ static const uint8_t Font_Roboto_Regular_20_glyph_38[] = { 12, 15, 13, 1, 15, 7, 244, 0, 15, 190, 0, 44, 15, 0, 60, 15, 0, 45, 30, 0, 15, 188, 0, 11, 224, 0, 15, 208, 0, 61, 240, 60, 180, 60, 56, 240, 31, 180, 240, 11, 240, 180, 7, 224, 62, 175, 244, 11, 248, 61, 0 };
/* ' */ static const uint8_t Font_Roboto_Regular_20_glyph_39[] = { 2, 5, 4, 1, 15, 255, 255, 240 };
/* ( */ static const uint8_t Font_Roboto_Regular_20_glyph_40[] = { 6, 22, 7, 1, 17, 0, 0, 28, 3, 128, 224, 28, 3, 128, 116, 11, 0, 240, 15, 0, 240, 15, 0, 240, 15, 0, 176, 7, 64, 56, 2, 192, 14, 0, 112, 2, 192, 4, 0 };
/* ) */ static const uint8_t Font_Roboto_Regular_20_glyph_41[] = { 6, 22, 7, 0, 17, 0, 3, 0, 44, 0, 224, 7, 64, 60, 2, 192, 29, 0, 224, 14, 0, 240, 15, 0, 224, 14, 1, 208, 28, 3, 192, 52, 11, 1, 208, 52, 1, 0, 0 };
/* * */ static const uint8_t Font_Roboto_Regular_20_glyph_42[] = { 10, 9, 9, 0, 15, 0, 240, 0, 15, 0, 32, 240, 67, 255, 252, 7, 249, 0, 63, 128, 11, 45, 0, 208, 240, 0, 0, 0 };
/* + */ static const uint8_t Font_Roboto_Regular_20_glyph_43[] = { 10, 11, 12, 1, 12, 0, 240, 0, 15, 0, 0, 240, 0, 15, 0, 0, 240, 15, 255, 255, 170, 250, 160, 15, 0, 0, 240, 0, 15, 0, 0, 240, 0 };
/* , */ static const uint8_t Font_Roboto_Regular_20_glyph_44[] = { 3, 6, 4, 0, 2, 60, 243, 173, 160, 0 };
/* - */ static const uint8_t Font_Roboto_Regular_20_glyph_45[] = { 5, 2, 7, 1, 7, 170, 191, 240 };
/* . */ static const uint8_t Font_Roboto_Regular_20_glyph_46[] = { 2, 3, 4, 1, 3, 14, 224 };
/* / */ static const uint8_t Font_Roboto_Regular_20_glyph_47[] = { 8, 16, 8, 0, 15, 0, 13, 0, 28, 0, 56, 0, 52, 0, 176, 0, 224, 1, 208, 2, 192, 3, 128, 7, 0, 15, 0, 13, 0, 44, 0, 56, 0, 116, 0, 176, 0, 0 };
/* 0 */ static const uint8_t Font_Roboto_Regular_20_glyph_48[] = { 9, 15, 11, 1, 15, 11, 248, 15, 171, 199, 128, 182, 192, 14, 240, 3, 252, 0, 255, 0, 63, 192, 15, 240, 3, 252, 0, 255, 0, 62, 192, 14, 120, 11, 79, 235, 192, 191, 128 };
/* 1 */ static const uint8_t Font_Roboto_Regular_20_glyph_49[] = { 6, 15, 11, 1, 15, 0, 177, 255, 126, 245, 15, 0, 240, 15, 0, 240, 15, 0, 240, 15, 0, 240, 15, 0, 240, 15, 0, 240 };
/* 2 */ static const uint8_t Font_Roboto_Regular_20_glyph_50[] = { 9, 15, 11, 1, 15, 11, 248, 15, 235, 203, 64, 123, 192, 15, 144, 3, 192, 0, 224, 0, 176, 0, 120, 0, 124, 0, 124, 0, 60, 0, 61, 0, 61, 0, 63, 170, 175, 255, 252 };
/* 3 */ static const uint8_t Font_Roboto_Regular_20_glyph_51[] = { 9, 15, 11, 1, 15, 11, 248, 15, 171, 203, 64, 123, 192, 15, 0, 3, 128, 2, 208, 43, 224, 15, 244, 0, 31, 0, 1, 224, 0, 63, 192, 14, 180, 11, 79, 175, 192, 191, 128 };
/* 4 */ static const uint8_t Font_Roboto_Regular_20_glyph_52[] = { 10, 15, 12, 1, 15, 0, 15, 0, 3, 240, 0, 127, 0, 14, 240, 2, 207, 0, 56, 240, 11, 15, 1, 208, 240, 60, 15, 7, 0, 240, 255, 255, 250, 170, 250, 0, 15, 0, 0, 240, 0, 15, 0 };
/* 5 */ static const uint8_t Font_Roboto_Regular_20_glyph_53[] = { 10, 15, 12, 1, 15, 15, 255, 208, 250, 168, 14, 0, 0, 208, 0, 29, 0, 1, 213, 64, 47, 255, 65, 208, 124, 0, 1, 224, 0, 15, 0, 0, 243, 128, 14, 60, 2, 208, 250, 252, 2, 254, 0 };
/* 6 */ static const uint8_t Font_Roboto_Regular_20_glyph_54[] = { 9, 15, 11, 1, 15, 1, 188, 2, 250, 1, 224, 0, 240, 0, 116, 0, 44, 84, 15, 255, 227, 244, 61, 240, 3, 188, 0, 255, 0, 62, 192, 15, 56, 11, 139, 235, 192, 127, 128 };
/* 7 */ static const uint8_t Font_Roboto_Regular_20_glyph_55[] = { 10, 15, 12, 1, 15, 255, 255, 250, 170, 175, 0, 1, 208, 0, 60, 0, 7, 64, 0, 240, 0, 30, 0, 2, 192, 0, 56, 0, 11, 64, 0, 240, 0, 45, 0, 3, 192, 0, 120, 0, 15, 0, 0 };
/* 8 */ static const uint8_t Font_Roboto_Regular_20_glyph_56[] = { 9, 15, 11, 1, 15, 11, 248, 15, 175, 203, 128, 187, 192, 15, 176, 3, 158, 2, 210, 234, 224, 127, 244, 60, 15, 60, 0, 239, 0, 63, 192, 15, 180, 7, 143, 171, 192, 191, 128 };
/* 9 */ static const uint8_t Font_Roboto_Regular_20_glyph_57[] = { 9, 15, 11, 1, 15, 11, 244, 15, 239, 135, 128, 243, 192, 14, 240, 3, 252, 0, 255, 0, 62, 224, 47, 62, 191, 194, 248, 224, 0, 56, 0, 44, 0, 30, 2, 190, 0, 249, 0 };
/* : */ static const uint8_t Font_Roboto_Regular_20_glyph_58[] = { 2, 11, 4, 1, 11, 238, 0, 0, 0, 14, 224 };
/* ; */ static const uint8_t Font_Roboto_Regular_20_glyph_59[] = { 3, 14, 4, 0, 11, 44, 240, 0, 0, 0, 0, 20, 243, 206, 116, 64 };
/* < */ static const uint8_t Font_Roboto_Regular_20_glyph_60[] = { 8, 10, 10, 1, 11, 0, 2, 0, 127, 7, 248, 127, 64, 244, 0, 191, 64, 7, 248, 0, 127, 0, 7, 0, 0, 0 };
/* = */ static const uint8_t Font_Roboto_Regular_20_glyph_61[] = { 8, 6, 10, 1, 10, 170, 170, 255, 255, 0, 0, 0, 0, 170, 170, 255, 255, 0 };
/* > */ static const uint8_t Font_Roboto_Regular_20_glyph_62[] = { 9, 10, 10, 1, 11, 144, 0, 63, 64, 2, 254, 0, 6, 248, 0, 15, 128, 111, 129, 254, 3, 244, 0, 208, 0, 0, 0, 0 };
/* ? */ static const uint8_t Font_Roboto_Regular_20_glyph_63[] = { 8, 15, 10, 1, 15, 11, 244, 126, 189, 240, 15, 160, 15, 0, 15, 0, 14, 0, 61, 0, 184, 1, 224, 3, 192, 3, 192, 0, 0, 0, 0, 1, 0, 3, 128, 0 };
/* @ */ static const uint8_t Font_Roboto_Regular_20_glyph_64[] = { 16, 19, 18, 1, 15, 0, 47, 249, 0, 1, 254, 175, 192, 7, 192, 1, 240, 14, 0, 0, 120, 60, 1, 80, 60, 120, 15, 248, 29, 176, 45, 28, 14, 240, 52, 28, 15, 240, 176, 44, 15, 240, 176, 40, 15, 240, 224, 40, 15, 240, 224, 56, 14, 176, 176, 120, 45, 116, 126, 238, 188, 60, 47, 75, 224, 45, 0, 0, 0, 15, 64, 0, 0, 3, 250, 172, 0, 0, 111, 228, 0, 0 };
/* A */ static const uint8_t Font_Roboto_Regular_20_glyph_65[] = { 13, 15, 13, 0, 15, 0, 30, 0, 0, 15, 192, 0, 3, 244, 0, 2, 222, 0, 0, 243, 192, 0, 116, 116, 0, 44, 14, 0, 15, 2, 192, 7, 64, 116, 2, 234, 175, 0, 255, 255, 192, 116, 0, 120, 60, 0, 15, 14, 0, 2, 219, 64, 0, 120 };
/* B */ static const uint8_t Font_Roboto_Regular_20_glyph_66[] = { 10, 15, 13, 2, 15, 255, 248, 15, 170, 244, 240, 7, 207, 0, 60, 240, 3, 207, 0, 120, 250, 175, 15, 255, 224, 240, 7, 207, 0, 30, 240, 0, 255, 0, 14, 240, 2, 223, 170, 252, 255, 254, 0 };
/* C */ static const uint8_t Font_Roboto_Regular_20_glyph_67[] = { 11, 15, 13, 1, 15, 2, 254, 64, 62, 175, 67, 208, 15, 30, 0, 30, 176, 0, 59, 192, 0, 15, 0, 0, 60, 0, 0, 240, 0, 3, 192, 0, 11, 0, 3, 158, 0, 30, 60, 0, 240, 62, 175, 64, 47, 228, 0 };
/* D */ static const uint8_t Font_Roboto_Regular_20_glyph_68[] = { 10, 15, 13, 2, 15, 255, 244, 15, 171, 240, 240, 7, 143, 0, 45, 240, 0, 239, 0, 15, 240, 0, 255, 0, 15, 240, 0, 255, 0, 15, 240, 0, 239, 0, 45, 240, 7, 143, 171, 240, 255, 244, 0 };
/* E */ static const uint8_t Font_Roboto_Regular_20_glyph_69[] = { 9, 15, 12, 2, 15, 255, 255, 254, 170, 175, 0, 3, 192, 0, 240, 0, 60, 0, 15, 170, 163, 255, 252, 240, 0, 60, 0, 15, 0, 3, 192, 0, 240, 0, 62, 170, 175, 255, 252 };
/* F */ static const uint8_t Font_Roboto_Regular_20_glyph_70[] = { 9, 15, 12, 2, 15, 255, 255, 254, 170, 175, 0, 3, 192, 0, 240, 0, 60, 0, 15, 0, 3, 255, 252, 250, 170, 60, 0, 15, 0, 3, 192, 0, 240, 0, 60, 0, 15, 0, 0 };
/* G */ static const uint8_t Font_Roboto_Regular_20_glyph_71[] = { 11, 15, 13, 1, 15, 2, 255, 64, 62, 175, 131, 192, 11, 93, 0, 15, 176, 0, 23, 192, 0, 15, 0, 0, 60, 2, 170, 240, 15, 255, 192, 0, 251, 0, 3, 222, 0, 15, 61, 0, 60, 63, 171, 208, 31, 248, 0 };
/* H */ static const uint8_t Font_Roboto_Regular_20_glyph_72[] = { 11, 15, 15, 2, 15, 240, 0, 63, 192, 0, 255, 0, 3, 252, 0, 15, 240, 0, 63, 192, 0, 255, 170, 171, 255, 255, 255, 240, 0, 63, 192, 0, 255, 0, 3, 252, 0, 15, 240, 0, 63, 192, 0, 255, 0, 3, 192 };
/* I */ static const uint8_t Font_Roboto_Regular_20_glyph_73[] = { 2, 15, 6, 2, 15, 255, 255, 255, 255, 255, 255, 255, 240 };
/* J */ static const uint8_t Font_Roboto_Regular_20_glyph_74[] = { 9, 15, 12, 1, 15, 0, 3, 192, 0, 240, 0, 60, 0, 15, 0, 3, 192, 0, 240, 0, 60, 0, 15, 0, 3, 192, 0, 240, 0, 63, 192, 15, 180, 7, 143, 171, 192, 191, 128 };
/* K */ static const uint8_t Font_Roboto_Regular_20_glyph_75[] = { 11, 15, 13, 2, 15, 240, 1, 243, 192, 15, 15, 0, 244, 60, 15, 64, 240, 184, 3, 203, 128, 15, 124, 0, 63, 244, 0, 253, 240, 3, 193, 240, 15, 2, 224, 60, 3, 208, 240, 3, 195, 192, 11, 143, 0, 15, 64 };
/* L */ static const uint8_t Font_Roboto_Regular_20_glyph_76[] = { 9, 15, 11, 2, 15, 240, 0, 60, 0, 15, 0, 3, 192, 0, 240, 0, 60, 0, 15, 0, 3, 192, 0, 240, 0, 60, 0, 15, 0, 3, 192, 0, 240, 0, 62, 170, 159, 255, 248 };
/* M */ static const uint8_t Font_Roboto_Regular_20_glyph_77[] = { 14, 15, 18, 2, 15, 248, 0, 2, 255, 192, 0, 63, 253, 0, 7, 255, 240, 0, 255, 251, 0, 14, 255, 56, 2, 207, 243, 192, 60, 255, 29, 7, 79, 240, 224, 176, 255, 11, 14, 15, 240, 117, 208, 255, 3, 252, 15, 240, 47, 128, 255, 1, 244, 15, 240, 15, 0, 240 };
/* N */ static const uint8_t Font_Roboto_Regular_20_glyph_78[] = { 11, 15, 15, 2, 15, 240, 0, 63, 240, 0, 255, 208, 3, 255, 192, 15, 251, 128, 63, 207, 64, 255, 15, 3, 252, 46, 15, 240, 60, 63, 192, 124, 255, 0, 183, 252, 0, 255, 240, 1, 255, 192, 3, 255, 0, 3, 192 };
/* O */ static const uint8_t Font_Roboto_Regular_20_glyph_79[] = { 11, 15, 13, 1, 15, 2, 254, 0, 62, 175, 3, 192, 15, 29, 0, 29, 176, 0, 59, 192, 0, 255, 0, 3, 252, 0, 15, 240, 0, 63, 192, 0, 251, 0, 3, 158, 0, 29, 61, 0, 240, 62, 175, 0, 47, 224, 0 };
/* P */ static const uint8_t Font_Roboto_Regular_20_glyph_80[] = { 10, 15, 13, 2, 15, 255, 254, 15, 170, 252, 240, 2, 223, 0, 15, 240, 0, 255, 0, 15, 240, 0, 239, 0, 125, 255, 255, 79, 169, 64, 240, 0, 15, 0, 0, 240, 0, 15, 0, 0, 240, 0, 0 };
/* Q */ static const uint8_t Font_Roboto_Regular_20_glyph_81[] = { 12, 18, 13, 1, 15, 2, 254, 0, 15, 171, 192, 61, 0, 240, 116, 0, 116, 176, 0, 56, 240, 0, 60, 240, 0, 60, 240, 0, 60, 240, 0, 60, 240, 0, 60, 176, 0, 56, 120, 0, 116, 61, 0, 240, 15, 171, 192, 2, 255, 192, 0, 1, 244, 0, 0, 56, 0, 0, 0, 0 };
/* R */ static const uint8_t Font_Roboto_Regular_20_glyph_82[] = { 11, 15, 13, 2, 15, 255, 253, 3, 234, 191, 15, 0, 45, 60, 0, 56, 240, 0, 243, 192, 3, 143, 0, 45, 62, 171, 224, 255, 253, 3, 192, 120, 15, 0, 240, 60, 1, 224, 240, 3, 195, 192, 7, 143, 0, 15, 0 };
/* S */ static const uint8_t Font_Roboto_Regular_20_glyph_83[] = { 10, 15, 12, 1, 15, 7, 253, 3, 250, 252, 120, 2, 239, 0, 15, 240, 0, 87, 192, 0, 47, 144, 0, 127, 224, 0, 47, 192, 0, 46, 80, 0, 255, 0, 15, 184, 1, 226, 250, 188, 6, 254, 0 };
/* T */ static const uint8_t Font_Roboto_Regular_20_glyph_84[] = { 11, 15, 13, 1, 15, 255, 255, 254, 171, 234, 160, 15, 0, 0, 60, 0, 0, 240, 0, 3, 192, 0, 15, 0, 0, 60, 0, 0, 240, 0, 3, 192, 0, 15, 0, 0, 60, 0, 0, 240, 0, 3, 192, 0, 15, 0, 0 };
/* U */ static const uint8_t Font_Roboto_Regular_20_glyph_85[] = { 10, 15, 12, 1, 15, 240, 0, 255, 0, 15, 240, 0, 255, 0, 15, 240, 0, 255, 0, 15, 240, 0, 255, 0, 15, 240, 0, 255, 0, 15, 240, 0, 255, 0, 15, 120, 2, 210, 250, 248, 7, 253, 0 };
/* V */ static const uint8_t Font_Roboto_Regular_20_glyph_86[] = { 13, 15, 13, 0, 15, 180, 0, 11, 79, 0, 3, 195, 192, 1, 224, 116, 0, 176, 15, 0, 60, 3, 192, 30, 0, 116, 11, 0, 15, 3, 192, 2, 193, 208, 0, 116, 176, 0, 15, 60, 0, 2, 221, 0, 0, 127, 0, 0, 15, 128, 0, 2, 208, 0 };
/* W */ static const uint8_t Font_Roboto_Regular_20_glyph_87[] = { 18, 15, 18, 0, 15, 120, 0, 240, 2, 195, 192, 15, 0, 60, 60, 1, 244, 3, 130, 192, 47, 128, 120, 29, 3, 172, 11, 64, 224, 117, 192, 176, 15, 11, 13, 15, 0, 176, 240, 224, 224, 7, 78, 11, 29, 0, 57, 208, 118, 192, 3, 172, 3, 188, 0, 63, 128, 63, 128, 2, 244, 2, 244, 0, 31, 0, 15, 0, 0, 240, 0, 240, 0 };
/* X */ static const uint8_t Font_Roboto_Regular_20_glyph_88[] = { 13, 15, 13, 0, 15, 60, 0, 46, 7, 192, 15, 0, 244, 15, 64, 15, 7, 192, 2, 227, 192, 0, 62, 224, 0, 7, 240, 0, 0, 248, 0, 0, 127, 0, 0, 62, 224, 0, 45, 61, 0, 31, 7, 192, 15, 64, 180, 11, 128, 15, 3, 192, 2, 224 };
/* Y */ static const uint8_t Font_Roboto_Regular_20_glyph_89[] = { 12, 15, 12, 0, 15, 184, 0, 45, 60, 0, 60, 45, 0, 180, 15, 0, 240, 11, 66, 208, 3, 195, 192, 2, 219, 64, 0, 255, 0, 0, 125, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0, 60, 0, 0 };
/* Z */ static const uint8_t Font_Roboto_Regular_20_glyph_90[] = { 10, 15, 12, 1, 15, 255, 255, 250, 170, 175, 0, 3, 208, 0, 184, 0, 15, 0, 3, 208, 0, 120, 0, 15, 0, 2, 208, 0, 120, 0, 15, 0, 2, 208, 0, 120, 0, 15, 170, 170, 255, 255, 240 };
/* [ */ static const uint8_t Font_Roboto_Regular_20_glyph_91[] = { 4, 20, 5, 1, 17, 169, 254, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 240, 249, 254, 0 };
/* \ */ static const uint8_t Font_Roboto_Regular_20_glyph_92[] = { 9, 16, 8, 0, 15, 116, 0, 14, 0, 2, 192, 0, 116, 0, 15, 0, 2, 192, 0, 56, 0, 15, 0, 1, 208, 0, 56, 0, 11, 0, 1, 208, 0, 60, 0, 11, 0, 0, 224, 0, 60, 0 };
/* ] */ static const uint8_t Font_Roboto_Regular_20_glyph_93[] = { 4, 20, 6, 1, 17, 169, 255, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 175, 255, 0 };
/* ^ */ static const uint8_t Font_Roboto_Regular_20_glyph_94[] = { 8, 8, 8, 0, 15, 1, 64, 3, 192, 3, 224, 11, 176, 14, 116, 28, 56, 60, 44, 52, 14, 0 };
/* _ */ static const uint8_t Font_Roboto_Regular_20_glyph_95[] = { 9, 2, 11, 1, 0, 170, 170, 191, 255, 240 };
/* ` */ static const uint8_t Font_Roboto_Regular_20_glyph_96[] = { 5, 3, 6, 0, 15, 60, 3, 128, 116 };
/* a */ static const uint8_t Font_Roboto_Regular_20_glyph_97[] = { 9, 11, 10, 1, 11, 11, 244, 31, 175, 79, 0, 240, 0, 60, 11, 255, 31, 171, 207, 0, 243, 192, 60, 240, 31, 31, 175, 193, 253, 176 };
/* b */ static const uint8_t Font_Roboto_Regular_20_glyph_98[] = { 9, 15, 11, 1, 15, 240, 0, 60, 0, 15, 0, 3, 192, 0, 247, 248, 63, 171, 207, 64, 183, 192, 15, 240, 3, 252, 0, 255, 0, 63, 192, 15, 244, 11, 127, 171, 206, 127, 128 };
/* c */ static const uint8_t Font_Roboto_Regular_20_glyph_99[] = { 9, 11, 11, 1, 11, 7, 248, 11, 235, 199, 128, 122, 192, 15, 240, 0, 60, 0, 15, 0, 2, 192, 6, 120, 3, 203, 235, 192, 127, 128 };
/* d */ static const uint8_t Font_Roboto_Regular_20_glyph_100[] = { 9, 15, 11, 1, 15, 0, 3, 192, 0, 240, 0, 60, 0, 15, 11, 247, 207, 235, 247, 128, 63, 192, 15, 240, 3, 252, 0, 255, 0, 63, 192, 15, 120, 7, 207, 235, 240, 191, 108 };
/* e */ static const uint8_t Font_Roboto_Regular_20_glyph_101[] = { 9, 11, 11, 1, 11, 7, 248, 11, 235, 199, 128, 118, 192, 15, 250, 171, 255, 255, 255, 0, 3, 192, 0, 120, 2, 75, 235, 208, 127, 144 };
/* f */ static const uint8_t Font_Roboto_Regular_20_glyph_102[] = { 7, 16, 8, 1, 16, 0, 80, 15, 224, 180, 3, 192, 15, 3, 255, 202, 250, 3, 192, 15, 0, 60, 0, 240, 3, 192, 15, 0, 60, 0, 240, 3, 192, 0 };
/* g */ static const uint8_t Font_Roboto_Regular_20_glyph_103[] = { 9, 15, 11, 1, 11, 11, 246, 207, 235, 247, 128, 127, 192, 15, 240, 3, 252, 0, 255, 0, 63, 192, 15, 120, 7, 207, 235, 240, 191, 124, 0, 15, 32, 7, 143, 171, 192, 191, 128 };
/* h */ static const uint8_t Font_Roboto_Regular_20_glyph_104[] = { 8, 15, 10, 1, 15, 240, 0, 240, 0, 240, 0, 240, 0, 243, 248, 254, 190, 244, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 0 };
/* i */ static const uint8_t Font_Roboto_Regular_20_glyph_105[] = { 2, 15, 4, 1, 15, 228, 0, 255, 255, 255, 255, 255, 240 };
/* j */ static const uint8_t Font_Roboto_Regular_20_glyph_106[] = { 4, 19, 4, -1, 15, 14, 4, 0, 0, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 14, 190, 248, 0 };
/* k */ static const uint8_t Font_Roboto_Regular_20_glyph_107[] = { 9, 15, 10, 1, 15, 240, 0, 60, 0, 15, 0, 3, 192, 0, 240, 31, 60, 31, 15, 15, 3, 207, 0, 255, 64, 63, 240, 15, 110, 3, 195, 208, 240, 60, 60, 7, 143, 0, 180 };
/* l */ static const uint8_t Font_Roboto_Regular_20_glyph_108[] = { 2, 15, 5, 2, 15, 255, 255, 255, 255, 255, 255, 255, 240 };
/* m */ static const uint8_t Font_Roboto_Regular_20_glyph_109[] = { 15, 11, 17, 1, 11, 231, 248, 63, 131, 250, 251, 175, 143, 0, 244, 15, 60, 3, 192, 44, 240, 15, 0, 179, 192, 60, 2, 207, 0, 240, 11, 60, 3, 192, 44, 240, 15, 0, 179, 192, 60, 2, 207, 0, 240, 11, 0 };
/* n */ static const uint8_t Font_Roboto_Regular_20_glyph_110[] = { 8, 11, 10, 1, 11, 227, 248, 254, 190, 244, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 0 };
/* o */ static const uint8_t Font_Roboto_Regular_20_glyph_111[] = { 10, 11, 12, 1, 11, 7, 249, 2, 250, 244, 120, 3, 203, 0, 30, 240, 0, 239, 0, 15, 240, 0, 235, 0, 30, 120, 3, 194, 250, 244, 7, 253, 0 };
/* p */ static const uint8_t Font_Roboto_Regular_20_glyph_112[] = { 9, 15, 11, 1, 11, 231, 248, 63, 175, 207, 0, 183, 192, 15, 240, 3, 252, 0, 255, 0, 63, 192, 15, 244, 11, 127, 175, 207, 127, 131, 192, 0, 240, 0, 60, 0, 15, 0, 0 };
/* q */ static const uint8_t Font_Roboto_Regular_20_glyph_113[] = { 9, 15, 12, 1, 11, 11, 246, 207, 235, 247, 128, 127, 192, 15, 240, 3, 252, 0, 255, 0, 63, 192, 15, 120, 7, 207, 235, 240, 191, 124, 0, 15, 0, 3, 192, 0, 240, 0, 60 };
/* r */ static const uint8_t Font_Roboto_Regular_20_glyph_114[] = { 5, 12, 7, 1, 12, 0, 61, 255, 235, 192, 240, 60, 15, 3, 192, 240, 60, 15, 3, 192, 0 };
/* s */ static const uint8_t Font_Roboto_Regular_20_glyph_115[] = { 8, 11, 10, 1, 11, 11, 244, 126, 189, 176, 15, 176, 5, 126, 0, 27, 244, 0, 110, 80, 15, 240, 15, 126, 189, 31, 244, 0 };
/* t */ static const uint8_t Font_Roboto_Regular_20_glyph_116[] = { 6, 14, 8, 1, 14, 9, 0, 240, 15, 15, 255, 175, 160, 240, 15, 0, 240, 15, 0, 240, 15, 0, 240, 15, 160, 62, 0 };
/* u */ static const uint8_t Font_Roboto_Regular_20_glyph_117[] = { 8, 11, 10, 1, 11, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 240, 15, 126, 191, 31, 219, 0 };
/* v */ static const uint8_t Font_Roboto_Regular_20_glyph_118[] = { 10, 11, 10, 0, 11, 180, 2, 195, 128, 60, 60, 7, 65, 208, 176, 14, 15, 0, 240, 208, 7, 44, 0, 59, 128, 2, 244, 0, 31, 0, 0, 224, 0 };
/* w */ static const uint8_t Font_Roboto_Regular_20_glyph_119[] = { 15, 11, 15, 0, 11, 116, 7, 64, 116, 224, 46, 2, 195, 192, 252, 15, 11, 7, 116, 56, 29, 44, 225, 208, 56, 226, 203, 0, 243, 71, 60, 1, 236, 14, 208, 3, 224, 47, 0, 15, 64, 124, 0, 44, 0, 224, 0 };
/* x */ static const uint8_t Font_Roboto_Regular_20_glyph_120[] = { 10, 11, 10, 0, 11, 60, 3, 194, 208, 180, 15, 15, 0, 123, 192, 2, 248, 0, 15, 0, 2, 248, 0, 122, 208, 15, 15, 2, 208, 120, 124, 3, 192 };
/* y */ static const uint8_t Font_Roboto_Regular_20_glyph_121[] = { 10, 15, 9, 0, 11, 180, 3, 195, 128, 56, 60, 7, 66, 208, 240, 14, 14, 0, 241, 208, 7, 108, 0, 59, 128, 3, 244, 0, 31, 0, 0, 224, 0, 29, 0, 3, 192, 2, 244, 0, 61, 0, 0 };
/* z */ static const uint8_t Font_Roboto_Regular_20_glyph_122[] = { 8, 11, 10, 1, 11, 255, 255, 170, 175, 0, 60, 0, 180, 1, 224, 3, 192, 15, 64, 30, 0, 60, 0, 250, 170, 255, 255, 0 };
/* { */ static const uint8_t Font_Roboto_Regular_20_glyph_123[] = { 6, 21, 7, 1, 16, 0, 16, 46, 7, 128, 240, 15, 0, 240, 15, 0, 240, 30, 11, 192, 248, 2, 208, 14, 0, 240, 15, 0, 240, 15, 0, 176, 3, 192, 10, 0, 0 };
/* | */ static const uint8_t Font_Roboto_Regular_20_glyph_124[] = { 2, 17, 6, 2, 15, 255, 255, 255, 255, 255, 255, 255, 255, 240 };
/* } */ static const uint8_t Font_Roboto_Regular_20_glyph_125[] = { 7, 21, 7, -1, 16, 16, 0, 244, 0, 176, 0, 224, 3, 128, 15, 0, 60, 0, 240, 3, 192, 3, 224, 11, 192, 184, 3, 192, 15, 0, 60, 0, 240, 3, 128, 29, 1, 240, 14, 0, 0, 0 };
/* ~ */ static const uint8_t Font_Roboto_Regular_20_glyph_126[] = { 11, 4, 13, 1, 8, 47, 128, 41, 251, 192, 255, 3, 239, 104, 2, 244, 0 };

const uint8_t * const Font_Roboto_Regular_20[126 + 1 - 32] = {
    Font_Roboto_Regular_20_glyph_32,
    Font_Roboto_Regular_20_glyph_33,
    Font_Roboto_Regular_20_glyph_34,
    Font_Roboto_Regular_20_glyph_35,
    Font_Roboto_Regular_20_glyph_36,
    Font_Roboto_Regular_20_glyph_37,
    Font_Roboto_Regular_20_glyph_38,
    Font_Roboto_Regular_20_glyph_39,
    Font_Roboto_Regular_20_glyph_40,
    Font_Roboto_Regular_20_glyph_41,
    Font_Roboto_Regular_20_glyph_42,
    Font_Roboto_Regular_20_glyph_43,
    Font_Roboto_Regular_20_glyph_44,
    Font_Roboto_Regular_20_glyph_45,
    Font_Roboto_Regular_20_glyph_46,
    Font_Roboto_Regular_20_glyph_47,
    Font_Roboto_Regular_20_glyph_48,
    Font_Roboto_Regular_20_glyph_49,
    Font_Roboto_Regular_20_glyph_50,
    Font_Roboto_Regular_20_glyph_51,
    Font_Roboto_Regular_20_glyph_52,
    Font_Roboto_Regular_20_glyph_53,
    Font_Roboto_Regular_20_glyph_54,
    Font_Roboto_Regular_20_glyph_55,
    Font_Roboto_Regular_20_glyph_56,
    Font_Roboto_Regular_20_glyph_57,
    Font_Roboto_Regular_20_glyph_58,
    Font_Roboto_Regular_20_glyph_59,
    Font_Roboto_Regular_20_glyph_60,
    Font_Roboto_Regular_20_glyph_61,
    Font_Roboto_Regular_20_glyph_62,
    Font_Roboto_Regular_20_glyph_63,
    Font_Roboto_Regular_20_glyph_64,
    Font_Roboto_Regular_20_glyph_65,
    Font_Roboto_Regular_20_glyph_66,
    Font_Roboto_Regular_20_glyph_67,
    Font_Roboto_Regular_20_glyph_68,
    Font_Roboto_Regular_20_glyph_69,
    Font_Roboto_Regular_20_glyph_70,
    Font_Roboto_Regular_20_glyph_71,
    Font_Roboto_Regular_20_glyph_72,
    Font_Roboto_Regular_20_glyph_73,
    Font_Roboto_Regular_20_glyph_74,
    Font_Roboto_Regular_20_glyph_75,
    Font_Roboto_Regular_20_glyph_76,
    Font_Roboto_Regular_20_glyph_77,
    Font_Roboto_Regular_20_glyph_78,
    Font_Roboto_Regular_20_glyph_79,
    Font_Roboto_Regular_20_glyph_80,
    Font_Roboto_Regular_20_glyph_81,
    Font_Roboto_Regular_20_glyph_82,
    Font_Roboto_Regular_20_glyph_83,
    Font_Roboto_Regular_20_glyph_84,
    Font_Roboto_Regular_20_glyph_85,
    Font_Roboto_Regular_20_glyph_86,
    Font_Roboto_Regular_20_glyph_87,
    Font_Roboto_Regular_20_glyph_88,
    Font_Roboto_Regular_20_glyph_89,
    Font_Roboto_Regular_20_glyph_90,
    Font_Roboto_Regular_20_glyph_91,
    Font_Roboto_Regular_20_glyph_92,
    Font_Roboto_Regular_20_glyph_93,
    Font_Roboto_Regular_20_glyph_94,
    Font_Roboto_Regular_20_glyph_95,
    Font_Roboto_Regular_20_glyph_96,
    Font_Roboto_Regular_20_glyph_97,
    Font_Roboto_Regular_20_glyph_98,
    Font_Roboto_Regular_20_glyph_99,
    Font_Roboto_Regular_20_glyph_100,
    Font_Roboto_Regular_20_glyph_101,
    Font_Roboto_Regular_20_glyph_102,
    Font_Roboto_Regular_20_glyph_103,
    Font_Roboto_Regular_20_glyph_104,
    Font_Roboto_Regular_20_glyph_105,
    Font_Roboto_Regular_20_glyph_106,
    Font_Roboto_Regular_20_glyph_107,
    Font_Roboto_Regular_20_glyph_108,
    Font_Roboto_Regular_20_glyph_109,
    Font_Roboto_Regular_20_glyph_110,
    Font_Roboto_Regular_20_glyph_111,
    Font_Roboto_Regular_20_glyph_112,
    Font_Roboto_Regular_20_glyph_113,
    Font_Roboto_Regular_20_glyph_114,
    Font_Roboto_Regular_20_glyph_115,
    Font_Roboto_Regular_20_glyph_116,
    Font_Roboto_Regular_20_glyph_117,
    Font_Roboto_Regular_20_glyph_118,
    Font_Roboto_Regular_20_glyph_119,
    Font_Roboto_Regular_20_glyph_120,
    Font_Roboto_Regular_20_glyph_121,
    Font_Roboto_Regular_20_glyph_122,
    Font_Roboto_Regular_20_glyph_123,
    Font_Roboto_Regular_20_glyph_124,
    Font_Roboto_Regular_20_glyph_125,
    Font_Roboto_Regular_20_glyph_126,
};
