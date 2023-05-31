#include <stdint.h>

// clang-format off

// - the first two bytes are width and height of the glyph
// - the third, fourth and fifth bytes are advance, bearingX and bearingY of the horizontal metrics of the glyph
// - the rest is packed 1-bit glyph data

// MANUAL CHANGES!
// In cases where the width and advance were the same (usually 7 and 7), increasing
// the advance to 8, so that these wide letters do not collide with the following one.

/*   */ static const uint8_t Font_Unifont_Regular_16_glyph_32[] = { 0, 0, 8, 0, 0 };
/* ! */ static const uint8_t Font_Unifont_Regular_16_glyph_33[] = { 1, 10, 7, 3, 10, 254, 192 };
/* " */ static const uint8_t Font_Unifont_Regular_16_glyph_34[] = { 5, 4, 7, 1, 12, 140, 99, 16 };
/* # */ static const uint8_t Font_Unifont_Regular_16_glyph_35[] = { 6, 10, 7, 0, 10, 36, 146, 127, 73, 47, 228, 146, 64 };
/* $ */ static const uint8_t Font_Unifont_Regular_16_glyph_36[] = { 7, 10, 8, 0, 10, 16, 250, 76, 135, 3, 132, 201, 124, 32 };  // < --- advanced changed from 7 to 8
/* % */ static const uint8_t Font_Unifont_Regular_16_glyph_37[] = { 7, 10, 8, 0, 10, 99, 42, 83, 65, 2, 11, 41, 83, 24 };  // < --- advanced changed from 7 to 8
/* & */ static const uint8_t Font_Unifont_Regular_16_glyph_38[] = { 7, 10, 8, 0, 10, 56, 137, 17, 67, 10, 98, 194, 140, 228 };  // < --- advanced changed from 7 to 8
/* ' */ static const uint8_t Font_Unifont_Regular_16_glyph_39[] = { 1, 4, 7, 3, 12, 240 };
/* ( */ static const uint8_t Font_Unifont_Regular_16_glyph_40[] = { 3, 12, 7, 2, 11, 41, 73, 36, 137, 16 };
/* ) */ static const uint8_t Font_Unifont_Regular_16_glyph_41[] = { 3, 12, 7, 1, 11, 137, 18, 73, 41, 64 };
/* * */ static const uint8_t Font_Unifont_Regular_16_glyph_42[] = { 7, 7, 8, 0, 8, 17, 37, 81, 197, 82, 68, 0 };  // < --- advanced changed from 7 to 8
/* + */ static const uint8_t Font_Unifont_Regular_16_glyph_43[] = { 7, 7, 8, 0, 8, 16, 32, 71, 241, 2, 4, 0 };  // < --- advanced changed from 7 to 8
/* , */ static const uint8_t Font_Unifont_Regular_16_glyph_44[] = { 2, 4, 7, 2, 2, 214, 0 };
/* - */ static const uint8_t Font_Unifont_Regular_16_glyph_45[] = { 4, 1, 7, 1, 5, 240 };
/* . */ static const uint8_t Font_Unifont_Regular_16_glyph_46[] = { 2, 2, 7, 2, 2, 240 };
/* / */ static const uint8_t Font_Unifont_Regular_16_glyph_47[] = { 6, 10, 7, 0, 10, 4, 16, 132, 16, 130, 16, 130, 0 };
/* 0 */ static const uint8_t Font_Unifont_Regular_16_glyph_48[] = { 6, 10, 7, 0, 10, 49, 40, 99, 150, 156, 97, 72, 192 };
/* 1 */ static const uint8_t Font_Unifont_Regular_16_glyph_49[] = { 5, 10, 7, 1, 10, 35, 40, 66, 16, 132, 39, 192 };
/* 2 */ static const uint8_t Font_Unifont_Regular_16_glyph_50[] = { 6, 10, 7, 0, 10, 122, 24, 65, 24, 132, 32, 131, 240 };
/* 3 */ static const uint8_t Font_Unifont_Regular_16_glyph_51[] = { 6, 10, 7, 0, 10, 122, 24, 65, 56, 16, 97, 133, 224 };
/* 4 */ static const uint8_t Font_Unifont_Regular_16_glyph_52[] = { 6, 10, 7, 0, 10, 8, 98, 146, 138, 47, 194, 8, 32 };
/* 5 */ static const uint8_t Font_Unifont_Regular_16_glyph_53[] = { 6, 10, 7, 0, 10, 254, 8, 32, 248, 16, 65, 133, 224 };
/* 6 */ static const uint8_t Font_Unifont_Regular_16_glyph_54[] = { 6, 10, 7, 0, 10, 57, 8, 32, 250, 24, 97, 133, 224 };
/* 7 */ static const uint8_t Font_Unifont_Regular_16_glyph_55[] = { 6, 10, 7, 0, 10, 252, 16, 66, 8, 33, 4, 16, 64 };
/* 8 */ static const uint8_t Font_Unifont_Regular_16_glyph_56[] = { 6, 10, 7, 0, 10, 122, 24, 97, 122, 24, 97, 133, 224 };
/* 9 */ static const uint8_t Font_Unifont_Regular_16_glyph_57[] = { 6, 10, 7, 0, 10, 122, 24, 97, 124, 16, 65, 9, 192 };
/* : */ static const uint8_t Font_Unifont_Regular_16_glyph_58[] = { 2, 7, 7, 2, 8, 240, 60 };
/* ; */ static const uint8_t Font_Unifont_Regular_16_glyph_59[] = { 2, 9, 7, 2, 8, 240, 53, 128 };
/* < */ static const uint8_t Font_Unifont_Regular_16_glyph_60[] = { 5, 9, 7, 1, 9, 8, 136, 136, 32, 130, 8 };
/* = */ static const uint8_t Font_Unifont_Regular_16_glyph_61[] = { 6, 5, 7, 0, 7, 252, 0, 0, 252 };
/* > */ static const uint8_t Font_Unifont_Regular_16_glyph_62[] = { 5, 9, 7, 0, 9, 130, 8, 32, 136, 136, 128 };
/* ? */ static const uint8_t Font_Unifont_Regular_16_glyph_63[] = { 6, 10, 7, 0, 10, 122, 24, 65, 8, 65, 0, 16, 64 };
/* @ */ static const uint8_t Font_Unifont_Regular_16_glyph_64[] = { 6, 10, 7, 0, 10, 57, 25, 107, 166, 154, 103, 64, 240 };
/* A */ static const uint8_t Font_Unifont_Regular_16_glyph_65[] = { 6, 10, 7, 0, 10, 49, 36, 161, 135, 248, 97, 134, 16 };
/* B */ static const uint8_t Font_Unifont_Regular_16_glyph_66[] = { 6, 10, 7, 0, 10, 250, 24, 97, 250, 24, 97, 135, 224 };
/* C */ static const uint8_t Font_Unifont_Regular_16_glyph_67[] = { 6, 10, 7, 0, 10, 122, 24, 96, 130, 8, 33, 133, 224 };
/* D */ static const uint8_t Font_Unifont_Regular_16_glyph_68[] = { 6, 10, 7, 0, 10, 242, 40, 97, 134, 24, 97, 139, 192 };
/* E */ static const uint8_t Font_Unifont_Regular_16_glyph_69[] = { 6, 10, 7, 0, 10, 254, 8, 32, 250, 8, 32, 131, 240 };
/* F */ static const uint8_t Font_Unifont_Regular_16_glyph_70[] = { 6, 10, 7, 0, 10, 254, 8, 32, 250, 8, 32, 130, 0 };
/* G */ static const uint8_t Font_Unifont_Regular_16_glyph_71[] = { 6, 10, 7, 0, 10, 122, 24, 96, 130, 120, 97, 141, 208 };
/* H */ static const uint8_t Font_Unifont_Regular_16_glyph_72[] = { 6, 10, 7, 0, 10, 134, 24, 97, 254, 24, 97, 134, 16 };
/* I */ static const uint8_t Font_Unifont_Regular_16_glyph_73[] = { 5, 10, 7, 1, 10, 249, 8, 66, 16, 132, 39, 192 };
/* J */ static const uint8_t Font_Unifont_Regular_16_glyph_74[] = { 7, 10, 8, 0, 10, 62, 16, 32, 64, 129, 2, 68, 136, 224 };  // < --- advanced changed from 7 to 8
/* K */ static const uint8_t Font_Unifont_Regular_16_glyph_75[] = { 6, 10, 7, 0, 10, 134, 41, 40, 195, 10, 36, 138, 16 };
/* L */ static const uint8_t Font_Unifont_Regular_16_glyph_76[] = { 6, 10, 7, 0, 10, 130, 8, 32, 130, 8, 32, 131, 240 };
/* M */ static const uint8_t Font_Unifont_Regular_16_glyph_77[] = { 6, 10, 7, 0, 10, 134, 28, 243, 182, 216, 97, 134, 16 };
/* N */ static const uint8_t Font_Unifont_Regular_16_glyph_78[] = { 6, 10, 7, 0, 10, 135, 28, 105, 166, 89, 99, 142, 16 };
/* O */ static const uint8_t Font_Unifont_Regular_16_glyph_79[] = { 6, 10, 7, 0, 10, 122, 24, 97, 134, 24, 97, 133, 224 };
/* P */ static const uint8_t Font_Unifont_Regular_16_glyph_80[] = { 6, 10, 7, 0, 10, 250, 24, 97, 250, 8, 32, 130, 0 };
/* Q */ static const uint8_t Font_Unifont_Regular_16_glyph_81[] = { 7, 11, 8, 0, 10, 121, 10, 20, 40, 80, 161, 90, 204, 240, 24 };  // < --- advanced changed from 7 to 8
/* R */ static const uint8_t Font_Unifont_Regular_16_glyph_82[] = { 6, 10, 7, 0, 10, 250, 24, 97, 250, 72, 162, 134, 16 };
/* S */ static const uint8_t Font_Unifont_Regular_16_glyph_83[] = { 6, 10, 7, 0, 10, 122, 24, 96, 96, 96, 97, 133, 224 };
/* T */ static const uint8_t Font_Unifont_Regular_16_glyph_84[] = { 7, 10, 8, 0, 10, 254, 32, 64, 129, 2, 4, 8, 16, 32 };  // < --- advanced changed from 7 to 8
/* U */ static const uint8_t Font_Unifont_Regular_16_glyph_85[] = { 6, 10, 7, 0, 10, 134, 24, 97, 134, 24, 97, 133, 224 };
/* V */ static const uint8_t Font_Unifont_Regular_16_glyph_86[] = { 7, 10, 8, 0, 10, 131, 6, 10, 36, 72, 138, 20, 16, 32 };  // < --- advanced changed from 7 to 8
/* W */ static const uint8_t Font_Unifont_Regular_16_glyph_87[] = { 6, 10, 7, 0, 10, 134, 24, 97, 182, 220, 243, 134, 16 };
/* X */ static const uint8_t Font_Unifont_Regular_16_glyph_88[] = { 6, 10, 7, 0, 10, 134, 20, 146, 48, 196, 146, 134, 16 };
/* Y */ static const uint8_t Font_Unifont_Regular_16_glyph_89[] = { 7, 10, 8, 0, 10, 131, 5, 18, 34, 130, 4, 8, 16, 32 };  // < --- advanced changed from 7 to 8
/* Z */ static const uint8_t Font_Unifont_Regular_16_glyph_90[] = { 6, 10, 7, 0, 10, 252, 16, 66, 16, 132, 32, 131, 240 };
/* [ */ static const uint8_t Font_Unifont_Regular_16_glyph_91[] = { 3, 12, 7, 3, 11, 242, 73, 36, 146, 112 };
/* \ */ static const uint8_t Font_Unifont_Regular_16_glyph_92[] = { 6, 10, 7, 0, 10, 130, 4, 8, 32, 65, 2, 4, 16 };
/* ] */ static const uint8_t Font_Unifont_Regular_16_glyph_93[] = { 3, 12, 7, 0, 11, 228, 146, 73, 36, 240 };
/* ^ */ static const uint8_t Font_Unifont_Regular_16_glyph_94[] = { 6, 3, 7, 0, 12, 49, 40, 64 };
/* _ */ static const uint8_t Font_Unifont_Regular_16_glyph_95[] = { 7, 1, 8, 0, 0, 254 };  // < --- advanced changed from 7 to 8
/* ` */ static const uint8_t Font_Unifont_Regular_16_glyph_96[] = { 3, 3, 7, 1, 13, 136, 128 };
/* a */ static const uint8_t Font_Unifont_Regular_16_glyph_97[] = { 6, 8, 7, 0, 8, 122, 16, 95, 134, 24, 221, 0 };
/* b */ static const uint8_t Font_Unifont_Regular_16_glyph_98[] = { 6, 11, 7, 0, 11, 130, 8, 46, 198, 24, 97, 135, 27, 128 };
/* c */ static const uint8_t Font_Unifont_Regular_16_glyph_99[] = { 6, 8, 7, 0, 8, 122, 24, 32, 130, 8, 94, 0 };
/* d */ static const uint8_t Font_Unifont_Regular_16_glyph_100[] = { 6, 11, 7, 0, 11, 4, 16, 93, 142, 24, 97, 134, 55, 64 };
/* e */ static const uint8_t Font_Unifont_Regular_16_glyph_101[] = { 6, 8, 7, 0, 8, 122, 24, 127, 130, 8, 94, 0 };
/* f */ static const uint8_t Font_Unifont_Regular_16_glyph_102[] = { 5, 11, 7, 0, 11, 25, 8, 79, 144, 132, 33, 8 };
/* g */ static const uint8_t Font_Unifont_Regular_16_glyph_103[] = { 6, 11, 7, 0, 9, 5, 216, 162, 137, 196, 30, 134, 23, 128 };
/* h */ static const uint8_t Font_Unifont_Regular_16_glyph_104[] = { 6, 11, 7, 0, 11, 130, 8, 46, 198, 24, 97, 134, 24, 64 };
/* i */ static const uint8_t Font_Unifont_Regular_16_glyph_105[] = { 5, 11, 7, 1, 11, 33, 0, 194, 16, 132, 33, 62 };
/* j */ static const uint8_t Font_Unifont_Regular_16_glyph_106[] = { 5, 13, 7, 0, 11, 8, 64, 48, 132, 33, 8, 67, 38, 0 };
/* k */ static const uint8_t Font_Unifont_Regular_16_glyph_107[] = { 6, 11, 7, 0, 11, 130, 8, 34, 146, 140, 40, 146, 40, 64 };
/* l */ static const uint8_t Font_Unifont_Regular_16_glyph_108[] = { 5, 11, 7, 1, 11, 97, 8, 66, 16, 132, 33, 62 };
/* m */ static const uint8_t Font_Unifont_Regular_16_glyph_109[] = { 7, 8, 8, 0, 8, 237, 38, 76, 153, 50, 100, 201, 0 };  // < --- advanced changed from 7 to 8
/* n */ static const uint8_t Font_Unifont_Regular_16_glyph_110[] = { 6, 8, 7, 0, 8, 187, 24, 97, 134, 24, 97, 0 };
/* o */ static const uint8_t Font_Unifont_Regular_16_glyph_111[] = { 6, 8, 7, 0, 8, 122, 24, 97, 134, 24, 94, 0 };
/* p */ static const uint8_t Font_Unifont_Regular_16_glyph_112[] = { 6, 10, 7, 0, 8, 187, 24, 97, 134, 28, 110, 130, 0 };
/* q */ static const uint8_t Font_Unifont_Regular_16_glyph_113[] = { 6, 10, 7, 0, 8, 118, 56, 97, 134, 24, 221, 4, 16 };
/* r */ static const uint8_t Font_Unifont_Regular_16_glyph_114[] = { 6, 8, 7, 0, 8, 187, 24, 96, 130, 8, 32, 0 };
/* s */ static const uint8_t Font_Unifont_Regular_16_glyph_115[] = { 6, 8, 7, 0, 8, 122, 24, 24, 24, 24, 94, 0 };
/* t */ static const uint8_t Font_Unifont_Regular_16_glyph_116[] = { 5, 10, 7, 0, 10, 33, 9, 242, 16, 132, 32, 192 };
/* u */ static const uint8_t Font_Unifont_Regular_16_glyph_117[] = { 6, 8, 7, 0, 8, 134, 24, 97, 134, 24, 221, 0 };
/* v */ static const uint8_t Font_Unifont_Regular_16_glyph_118[] = { 6, 8, 7, 0, 8, 134, 24, 82, 73, 35, 12, 0 };
/* w */ static const uint8_t Font_Unifont_Regular_16_glyph_119[] = { 7, 8, 8, 0, 8, 131, 38, 76, 153, 50, 100, 182, 0 };  // < --- advanced changed from 7 to 8
/* x */ static const uint8_t Font_Unifont_Regular_16_glyph_120[] = { 6, 8, 7, 0, 8, 134, 20, 140, 49, 40, 97, 0 };
/* y */ static const uint8_t Font_Unifont_Regular_16_glyph_121[] = { 6, 10, 7, 0, 8, 134, 24, 97, 133, 51, 65, 5, 224 };
/* z */ static const uint8_t Font_Unifont_Regular_16_glyph_122[] = { 6, 8, 7, 0, 8, 252, 16, 132, 33, 8, 63, 0 };
/* { */ static const uint8_t Font_Unifont_Regular_16_glyph_123[] = { 4, 13, 7, 1, 11, 52, 66, 36, 132, 34, 68, 48 };
/* | */ static const uint8_t Font_Unifont_Regular_16_glyph_124[] = { 1, 14, 7, 3, 12, 255, 252 };
/* } */ static const uint8_t Font_Unifont_Regular_16_glyph_125[] = { 4, 13, 7, 1, 11, 194, 36, 66, 18, 68, 34, 192 };
/* ~ */ static const uint8_t Font_Unifont_Regular_16_glyph_126[] = { 7, 3, 8, 0, 11, 99, 38, 48 };  // < --- advanced changed from 7 to 8

const uint8_t Font_Unifont_Regular_16_glyph_nonprintable[] = { 6, 10, 7, 0, 10, 133, 231, 190, 247, 190, 255, 239, 191 };

const uint8_t * const Font_Unifont_Regular_16[126 + 1 - 32] = {
    Font_Unifont_Regular_16_glyph_32,
    Font_Unifont_Regular_16_glyph_33,
    Font_Unifont_Regular_16_glyph_34,
    Font_Unifont_Regular_16_glyph_35,
    Font_Unifont_Regular_16_glyph_36,
    Font_Unifont_Regular_16_glyph_37,
    Font_Unifont_Regular_16_glyph_38,
    Font_Unifont_Regular_16_glyph_39,
    Font_Unifont_Regular_16_glyph_40,
    Font_Unifont_Regular_16_glyph_41,
    Font_Unifont_Regular_16_glyph_42,
    Font_Unifont_Regular_16_glyph_43,
    Font_Unifont_Regular_16_glyph_44,
    Font_Unifont_Regular_16_glyph_45,
    Font_Unifont_Regular_16_glyph_46,
    Font_Unifont_Regular_16_glyph_47,
    Font_Unifont_Regular_16_glyph_48,
    Font_Unifont_Regular_16_glyph_49,
    Font_Unifont_Regular_16_glyph_50,
    Font_Unifont_Regular_16_glyph_51,
    Font_Unifont_Regular_16_glyph_52,
    Font_Unifont_Regular_16_glyph_53,
    Font_Unifont_Regular_16_glyph_54,
    Font_Unifont_Regular_16_glyph_55,
    Font_Unifont_Regular_16_glyph_56,
    Font_Unifont_Regular_16_glyph_57,
    Font_Unifont_Regular_16_glyph_58,
    Font_Unifont_Regular_16_glyph_59,
    Font_Unifont_Regular_16_glyph_60,
    Font_Unifont_Regular_16_glyph_61,
    Font_Unifont_Regular_16_glyph_62,
    Font_Unifont_Regular_16_glyph_63,
    Font_Unifont_Regular_16_glyph_64,
    Font_Unifont_Regular_16_glyph_65,
    Font_Unifont_Regular_16_glyph_66,
    Font_Unifont_Regular_16_glyph_67,
    Font_Unifont_Regular_16_glyph_68,
    Font_Unifont_Regular_16_glyph_69,
    Font_Unifont_Regular_16_glyph_70,
    Font_Unifont_Regular_16_glyph_71,
    Font_Unifont_Regular_16_glyph_72,
    Font_Unifont_Regular_16_glyph_73,
    Font_Unifont_Regular_16_glyph_74,
    Font_Unifont_Regular_16_glyph_75,
    Font_Unifont_Regular_16_glyph_76,
    Font_Unifont_Regular_16_glyph_77,
    Font_Unifont_Regular_16_glyph_78,
    Font_Unifont_Regular_16_glyph_79,
    Font_Unifont_Regular_16_glyph_80,
    Font_Unifont_Regular_16_glyph_81,
    Font_Unifont_Regular_16_glyph_82,
    Font_Unifont_Regular_16_glyph_83,
    Font_Unifont_Regular_16_glyph_84,
    Font_Unifont_Regular_16_glyph_85,
    Font_Unifont_Regular_16_glyph_86,
    Font_Unifont_Regular_16_glyph_87,
    Font_Unifont_Regular_16_glyph_88,
    Font_Unifont_Regular_16_glyph_89,
    Font_Unifont_Regular_16_glyph_90,
    Font_Unifont_Regular_16_glyph_91,
    Font_Unifont_Regular_16_glyph_92,
    Font_Unifont_Regular_16_glyph_93,
    Font_Unifont_Regular_16_glyph_94,
    Font_Unifont_Regular_16_glyph_95,
    Font_Unifont_Regular_16_glyph_96,
    Font_Unifont_Regular_16_glyph_97,
    Font_Unifont_Regular_16_glyph_98,
    Font_Unifont_Regular_16_glyph_99,
    Font_Unifont_Regular_16_glyph_100,
    Font_Unifont_Regular_16_glyph_101,
    Font_Unifont_Regular_16_glyph_102,
    Font_Unifont_Regular_16_glyph_103,
    Font_Unifont_Regular_16_glyph_104,
    Font_Unifont_Regular_16_glyph_105,
    Font_Unifont_Regular_16_glyph_106,
    Font_Unifont_Regular_16_glyph_107,
    Font_Unifont_Regular_16_glyph_108,
    Font_Unifont_Regular_16_glyph_109,
    Font_Unifont_Regular_16_glyph_110,
    Font_Unifont_Regular_16_glyph_111,
    Font_Unifont_Regular_16_glyph_112,
    Font_Unifont_Regular_16_glyph_113,
    Font_Unifont_Regular_16_glyph_114,
    Font_Unifont_Regular_16_glyph_115,
    Font_Unifont_Regular_16_glyph_116,
    Font_Unifont_Regular_16_glyph_117,
    Font_Unifont_Regular_16_glyph_118,
    Font_Unifont_Regular_16_glyph_119,
    Font_Unifont_Regular_16_glyph_120,
    Font_Unifont_Regular_16_glyph_121,
    Font_Unifont_Regular_16_glyph_122,
    Font_Unifont_Regular_16_glyph_123,
    Font_Unifont_Regular_16_glyph_124,
    Font_Unifont_Regular_16_glyph_125,
    Font_Unifont_Regular_16_glyph_126,
};
