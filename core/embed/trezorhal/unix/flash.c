/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <fcntl.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <string.h>

#include "common.h"
#include "flash.h"
#include "model.h"
#include "profile.h"

#ifndef FLASH_FILE
#define FLASH_FILE profile_flash_path()
#endif

#if defined TREZOR_MODEL_T || defined TREZOR_MODEL_R
#define FLASH_SECTOR_COUNT 24
#elif defined TREZOR_MODEL_1
#define FLASH_SECTOR_COUNT 12
#elif defined TREZOR_MODEL_T3T1
#define FLASH_SECTOR_COUNT 256
#else
#error Unknown MCU
#endif

static const uint32_t FLASH_SECTOR_TABLE[FLASH_SECTOR_COUNT + 1] = {
#if defined TREZOR_MODEL_T || defined TREZOR_MODEL_R
    [0] = 0x08000000,   // - 0x08003FFF |  16 KiB
    [1] = 0x08004000,   // - 0x08007FFF |  16 KiB
    [2] = 0x08008000,   // - 0x0800BFFF |  16 KiB
    [3] = 0x0800C000,   // - 0x0800FFFF |  16 KiB
    [4] = 0x08010000,   // - 0x0801FFFF |  64 KiB
    [5] = 0x08020000,   // - 0x0803FFFF | 128 KiB
    [6] = 0x08040000,   // - 0x0805FFFF | 128 KiB
    [7] = 0x08060000,   // - 0x0807FFFF | 128 KiB
    [8] = 0x08080000,   // - 0x0809FFFF | 128 KiB
    [9] = 0x080A0000,   // - 0x080BFFFF | 128 KiB
    [10] = 0x080C0000,  // - 0x080DFFFF | 128 KiB
    [11] = 0x080E0000,  // - 0x080FFFFF | 128 KiB
    [12] = 0x08100000,  // - 0x08103FFF |  16 KiB
    [13] = 0x08104000,  // - 0x08107FFF |  16 KiB
    [14] = 0x08108000,  // - 0x0810BFFF |  16 KiB
    [15] = 0x0810C000,  // - 0x0810FFFF |  16 KiB
    [16] = 0x08110000,  // - 0x0811FFFF |  64 KiB
    [17] = 0x08120000,  // - 0x0813FFFF | 128 KiB
    [18] = 0x08140000,  // - 0x0815FFFF | 128 KiB
    [19] = 0x08160000,  // - 0x0817FFFF | 128 KiB
    [20] = 0x08180000,  // - 0x0819FFFF | 128 KiB
    [21] = 0x081A0000,  // - 0x081BFFFF | 128 KiB
    [22] = 0x081C0000,  // - 0x081DFFFF | 128 KiB
    [23] = 0x081E0000,  // - 0x081FFFFF | 128 KiB
    [24] = 0x08200000,  // last element - not a valid sector
#elif defined TREZOR_MODEL_1
    [0] = 0x08000000,   // - 0x08003FFF |  16 KiB
    [1] = 0x08004000,   // - 0x08007FFF |  16 KiB
    [2] = 0x08008000,   // - 0x0800BFFF |  16 KiB
    [3] = 0x0800C000,   // - 0x0800FFFF |  16 KiB
    [4] = 0x08010000,   // - 0x0801FFFF |  64 KiB
    [5] = 0x08020000,   // - 0x0803FFFF | 128 KiB
    [6] = 0x08040000,   // - 0x0805FFFF | 128 KiB
    [7] = 0x08060000,   // - 0x0807FFFF | 128 KiB
    [8] = 0x08080000,   // - 0x0809FFFF | 128 KiB
    [9] = 0x080A0000,   // - 0x080BFFFF | 128 KiB
    [10] = 0x080C0000,  // - 0x080DFFFF | 128 KiB
    [11] = 0x080E0000,  // - 0x080FFFFF | 128 KiB
    [12] = 0x08100000,  // last element - not a valid sector
#elif defined TREZOR_MODEL_T3T1
    [0] = 0x08000000,    // - 0x08001FFF |   8 KiB
    [1] = 0x08002000,    // - 0x08003FFF |   8 KiB
    [2] = 0x08004000,    // - 0x08005FFF |   8 KiB
    [3] = 0x08006000,    // - 0x08007FFF |   8 KiB
    [4] = 0x08008000,    // - 0x08009FFF |   8 KiB
    [5] = 0x0800A000,    // - 0x0800BFFF |   8 KiB
    [6] = 0x0800C000,    // - 0x0800DFFF |   8 KiB
    [7] = 0x0800E000,    // - 0x0800FFFF |   8 KiB
    [8] = 0x08010000,    // - 0x08011FFF |   8 KiB
    [9] = 0x08012000,    // - 0x08013FFF |   8 KiB
    [10] = 0x08014000,   // - 0x08015FFF |   8 KiB
    [11] = 0x08016000,   // - 0x08017FFF |   8 KiB
    [12] = 0x08018000,   // - 0x08019FFF |   8 KiB
    [13] = 0x0801A000,   // - 0x0801BFFF |   8 KiB
    [14] = 0x0801C000,   // - 0x0801DFFF |   8 KiB
    [15] = 0x0801E000,   // - 0x0801FFFF |   8 KiB
    [16] = 0x08020000,   // - 0x08021FFF |   8 KiB
    [17] = 0x08022000,   // - 0x08023FFF |   8 KiB
    [18] = 0x08024000,   // - 0x08025FFF |   8 KiB
    [19] = 0x08026000,   // - 0x08027FFF |   8 KiB
    [20] = 0x08028000,   // - 0x08029FFF |   8 KiB
    [21] = 0x0802A000,   // - 0x0802BFFF |   8 KiB
    [22] = 0x0802C000,   // - 0x0802DFFF |   8 KiB
    [23] = 0x0802E000,   // - 0x0802FFFF |   8 KiB
    [24] = 0x08030000,   // - 0x08031FFF |   8 KiB
    [25] = 0x08032000,   // - 0x08033FFF |   8 KiB
    [26] = 0x08034000,   // - 0x08035FFF |   8 KiB
    [27] = 0x08036000,   // - 0x08037FFF |   8 KiB
    [28] = 0x08038000,   // - 0x08039FFF |   8 KiB
    [29] = 0x0803A000,   // - 0x0803BFFF |   8 KiB
    [30] = 0x0803C000,   // - 0x0803DFFF |   8 KiB
    [31] = 0x0803E000,   // - 0x0803FFFF |   8 KiB
    [32] = 0x08040000,   // - 0x08041FFF |   8 KiB
    [33] = 0x08042000,   // - 0x08043FFF |   8 KiB
    [34] = 0x08044000,   // - 0x08045FFF |   8 KiB
    [35] = 0x08046000,   // - 0x08047FFF |   8 KiB
    [36] = 0x08048000,   // - 0x08049FFF |   8 KiB
    [37] = 0x0804A000,   // - 0x0804BFFF |   8 KiB
    [38] = 0x0804C000,   // - 0x0804DFFF |   8 KiB
    [39] = 0x0804E000,   // - 0x0804FFFF |   8 KiB
    [40] = 0x08050000,   // - 0x08051FFF |   8 KiB
    [41] = 0x08052000,   // - 0x08053FFF |   8 KiB
    [42] = 0x08054000,   // - 0x08055FFF |   8 KiB
    [43] = 0x08056000,   // - 0x08057FFF |   8 KiB
    [44] = 0x08058000,   // - 0x08059FFF |   8 KiB
    [45] = 0x0805A000,   // - 0x0805BFFF |   8 KiB
    [46] = 0x0805C000,   // - 0x0805DFFF |   8 KiB
    [47] = 0x0805E000,   // - 0x0805FFFF |   8 KiB
    [48] = 0x08060000,   // - 0x08061FFF |   8 KiB
    [49] = 0x08062000,   // - 0x08063FFF |   8 KiB
    [50] = 0x08064000,   // - 0x08065FFF |   8 KiB
    [51] = 0x08066000,   // - 0x08067FFF |   8 KiB
    [52] = 0x08068000,   // - 0x08069FFF |   8 KiB
    [53] = 0x0806A000,   // - 0x0806BFFF |   8 KiB
    [54] = 0x0806C000,   // - 0x0806DFFF |   8 KiB
    [55] = 0x0806E000,   // - 0x0806FFFF |   8 KiB
    [56] = 0x08070000,   // - 0x08071FFF |   8 KiB
    [57] = 0x08072000,   // - 0x08073FFF |   8 KiB
    [58] = 0x08074000,   // - 0x08075FFF |   8 KiB
    [59] = 0x08076000,   // - 0x08077FFF |   8 KiB
    [60] = 0x08078000,   // - 0x08079FFF |   8 KiB
    [61] = 0x0807A000,   // - 0x0807BFFF |   8 KiB
    [62] = 0x0807C000,   // - 0x0807DFFF |   8 KiB
    [63] = 0x0807E000,   // - 0x0807FFFF |   8 KiB
    [64] = 0x08080000,   // - 0x08081FFF |   8 KiB
    [65] = 0x08082000,   // - 0x08083FFF |   8 KiB
    [66] = 0x08084000,   // - 0x08085FFF |   8 KiB
    [67] = 0x08086000,   // - 0x08087FFF |   8 KiB
    [68] = 0x08088000,   // - 0x08089FFF |   8 KiB
    [69] = 0x0808A000,   // - 0x0808BFFF |   8 KiB
    [70] = 0x0808C000,   // - 0x0808DFFF |   8 KiB
    [71] = 0x0808E000,   // - 0x0808FFFF |   8 KiB
    [72] = 0x08090000,   // - 0x08091FFF |   8 KiB
    [73] = 0x08092000,   // - 0x08093FFF |   8 KiB
    [74] = 0x08094000,   // - 0x08095FFF |   8 KiB
    [75] = 0x08096000,   // - 0x08097FFF |   8 KiB
    [76] = 0x08098000,   // - 0x08099FFF |   8 KiB
    [77] = 0x0809A000,   // - 0x0809BFFF |   8 KiB
    [78] = 0x0809C000,   // - 0x0809DFFF |   8 KiB
    [79] = 0x0809E000,   // - 0x0809FFFF |   8 KiB
    [80] = 0x080A0000,   // - 0x080A1FFF |   8 KiB
    [81] = 0x080A2000,   // - 0x080A3FFF |   8 KiB
    [82] = 0x080A4000,   // - 0x080A5FFF |   8 KiB
    [83] = 0x080A6000,   // - 0x080A7FFF |   8 KiB
    [84] = 0x080A8000,   // - 0x080A9FFF |   8 KiB
    [85] = 0x080AA000,   // - 0x080ABFFF |   8 KiB
    [86] = 0x080AC000,   // - 0x080ADFFF |   8 KiB
    [87] = 0x080AE000,   // - 0x080AFFFF |   8 KiB
    [88] = 0x080B0000,   // - 0x080B1FFF |   8 KiB
    [89] = 0x080B2000,   // - 0x080B3FFF |   8 KiB
    [90] = 0x080B4000,   // - 0x080B5FFF |   8 KiB
    [91] = 0x080B6000,   // - 0x080B7FFF |   8 KiB
    [92] = 0x080B8000,   // - 0x080B9FFF |   8 KiB
    [93] = 0x080BA000,   // - 0x080BBFFF |   8 KiB
    [94] = 0x080BC000,   // - 0x080BDFFF |   8 KiB
    [95] = 0x080BE000,   // - 0x080BFFFF |   8 KiB
    [96] = 0x080C0000,   // - 0x080C1FFF |   8 KiB
    [97] = 0x080C2000,   // - 0x080C3FFF |   8 KiB
    [98] = 0x080C4000,   // - 0x080C5FFF |   8 KiB
    [99] = 0x080C6000,   // - 0x080C7FFF |   8 KiB
    [100] = 0x080C8000,  // - 0x080C9FFF |   8 KiB
    [101] = 0x080CA000,  // - 0x080CBFFF |   8 KiB
    [102] = 0x080CC000,  // - 0x080CDFFF |   8 KiB
    [103] = 0x080CE000,  // - 0x080CFFFF |   8 KiB
    [104] = 0x080D0000,  // - 0x080D1FFF |   8 KiB
    [105] = 0x080D2000,  // - 0x080D3FFF |   8 KiB
    [106] = 0x080D4000,  // - 0x080D5FFF |   8 KiB
    [107] = 0x080D6000,  // - 0x080D7FFF |   8 KiB
    [108] = 0x080D8000,  // - 0x080D9FFF |   8 KiB
    [109] = 0x080DA000,  // - 0x080DBFFF |   8 KiB
    [110] = 0x080DC000,  // - 0x080DDFFF |   8 KiB
    [111] = 0x080DE000,  // - 0x080DFFFF |   8 KiB
    [112] = 0x080E0000,  // - 0x080E1FFF |   8 KiB
    [113] = 0x080E2000,  // - 0x080E3FFF |   8 KiB
    [114] = 0x080E4000,  // - 0x080E5FFF |   8 KiB
    [115] = 0x080E6000,  // - 0x080E7FFF |   8 KiB
    [116] = 0x080E8000,  // - 0x080E9FFF |   8 KiB
    [117] = 0x080EA000,  // - 0x080EBFFF |   8 KiB
    [118] = 0x080EC000,  // - 0x080EDFFF |   8 KiB
    [119] = 0x080EE000,  // - 0x080EFFFF |   8 KiB
    [120] = 0x080F0000,  // - 0x080F1FFF |   8 KiB
    [121] = 0x080F2000,  // - 0x080F3FFF |   8 KiB
    [122] = 0x080F4000,  // - 0x080F5FFF |   8 KiB
    [123] = 0x080F6000,  // - 0x080F7FFF |   8 KiB
    [124] = 0x080F8000,  // - 0x080F9FFF |   8 KiB
    [125] = 0x080FA000,  // - 0x080FBFFF |   8 KiB
    [126] = 0x080FC000,  // - 0x080FDFFF |   8 KiB
    [127] = 0x080FE000,  // - 0x080FFFFF |   8 KiB
    [128] = 0x08100000,  // - 0x08101FFF |   8 KiB
    [129] = 0x08102000,  // - 0x08103FFF |   8 KiB
    [130] = 0x08104000,  // - 0x08105FFF |   8 KiB
    [131] = 0x08106000,  // - 0x08107FFF |   8 KiB
    [132] = 0x08108000,  // - 0x08109FFF |   8 KiB
    [133] = 0x0810A000,  // - 0x0810BFFF |   8 KiB
    [134] = 0x0810C000,  // - 0x0810DFFF |   8 KiB
    [135] = 0x0810E000,  // - 0x0810FFFF |   8 KiB
    [136] = 0x08110000,  // - 0x08111FFF |   8 KiB
    [137] = 0x08112000,  // - 0x08113FFF |   8 KiB
    [138] = 0x08114000,  // - 0x08115FFF |   8 KiB
    [139] = 0x08116000,  // - 0x08117FFF |   8 KiB
    [140] = 0x08118000,  // - 0x08119FFF |   8 KiB
    [141] = 0x0811A000,  // - 0x0811BFFF |   8 KiB
    [142] = 0x0811C000,  // - 0x0811DFFF |   8 KiB
    [143] = 0x0811E000,  // - 0x0811FFFF |   8 KiB
    [144] = 0x08120000,  // - 0x08121FFF |   8 KiB
    [145] = 0x08122000,  // - 0x08123FFF |   8 KiB
    [146] = 0x08124000,  // - 0x08125FFF |   8 KiB
    [147] = 0x08126000,  // - 0x08127FFF |   8 KiB
    [148] = 0x08128000,  // - 0x08129FFF |   8 KiB
    [149] = 0x0812A000,  // - 0x0812BFFF |   8 KiB
    [150] = 0x0812C000,  // - 0x0812DFFF |   8 KiB
    [151] = 0x0812E000,  // - 0x0812FFFF |   8 KiB
    [152] = 0x08130000,  // - 0x08131FFF |   8 KiB
    [153] = 0x08132000,  // - 0x08133FFF |   8 KiB
    [154] = 0x08134000,  // - 0x08135FFF |   8 KiB
    [155] = 0x08136000,  // - 0x08137FFF |   8 KiB
    [156] = 0x08138000,  // - 0x08139FFF |   8 KiB
    [157] = 0x0813A000,  // - 0x0813BFFF |   8 KiB
    [158] = 0x0813C000,  // - 0x0813DFFF |   8 KiB
    [159] = 0x0813E000,  // - 0x0813FFFF |   8 KiB
    [160] = 0x08140000,  // - 0x08141FFF |   8 KiB
    [161] = 0x08142000,  // - 0x08143FFF |   8 KiB
    [162] = 0x08144000,  // - 0x08145FFF |   8 KiB
    [163] = 0x08146000,  // - 0x08147FFF |   8 KiB
    [164] = 0x08148000,  // - 0x08149FFF |   8 KiB
    [165] = 0x0814A000,  // - 0x0814BFFF |   8 KiB
    [166] = 0x0814C000,  // - 0x0814DFFF |   8 KiB
    [167] = 0x0814E000,  // - 0x0814FFFF |   8 KiB
    [168] = 0x08150000,  // - 0x08151FFF |   8 KiB
    [169] = 0x08152000,  // - 0x08153FFF |   8 KiB
    [170] = 0x08154000,  // - 0x08155FFF |   8 KiB
    [171] = 0x08156000,  // - 0x08157FFF |   8 KiB
    [172] = 0x08158000,  // - 0x08159FFF |   8 KiB
    [173] = 0x0815A000,  // - 0x0815BFFF |   8 KiB
    [174] = 0x0815C000,  // - 0x0815DFFF |   8 KiB
    [175] = 0x0815E000,  // - 0x0815FFFF |   8 KiB
    [176] = 0x08160000,  // - 0x08161FFF |   8 KiB
    [177] = 0x08162000,  // - 0x08163FFF |   8 KiB
    [178] = 0x08164000,  // - 0x08165FFF |   8 KiB
    [179] = 0x08166000,  // - 0x08167FFF |   8 KiB
    [180] = 0x08168000,  // - 0x08169FFF |   8 KiB
    [181] = 0x0816A000,  // - 0x0816BFFF |   8 KiB
    [182] = 0x0816C000,  // - 0x0816DFFF |   8 KiB
    [183] = 0x0816E000,  // - 0x0816FFFF |   8 KiB
    [184] = 0x08170000,  // - 0x08171FFF |   8 KiB
    [185] = 0x08172000,  // - 0x08173FFF |   8 KiB
    [186] = 0x08174000,  // - 0x08175FFF |   8 KiB
    [187] = 0x08176000,  // - 0x08177FFF |   8 KiB
    [188] = 0x08178000,  // - 0x08179FFF |   8 KiB
    [189] = 0x0817A000,  // - 0x0817BFFF |   8 KiB
    [190] = 0x0817C000,  // - 0x0817DFFF |   8 KiB
    [191] = 0x0817E000,  // - 0x0817FFFF |   8 KiB
    [192] = 0x08180000,  // - 0x08181FFF |   8 KiB
    [193] = 0x08182000,  // - 0x08183FFF |   8 KiB
    [194] = 0x08184000,  // - 0x08185FFF |   8 KiB
    [195] = 0x08186000,  // - 0x08187FFF |   8 KiB
    [196] = 0x08188000,  // - 0x08189FFF |   8 KiB
    [197] = 0x0818A000,  // - 0x0818BFFF |   8 KiB
    [198] = 0x0818C000,  // - 0x0818DFFF |   8 KiB
    [199] = 0x0818E000,  // - 0x0818FFFF |   8 KiB
    [200] = 0x08190000,  // - 0x08191FFF |   8 KiB
    [201] = 0x08192000,  // - 0x08193FFF |   8 KiB
    [202] = 0x08194000,  // - 0x08195FFF |   8 KiB
    [203] = 0x08196000,  // - 0x08197FFF |   8 KiB
    [204] = 0x08198000,  // - 0x08199FFF |   8 KiB
    [205] = 0x0819A000,  // - 0x0819BFFF |   8 KiB
    [206] = 0x0819C000,  // - 0x0819DFFF |   8 KiB
    [207] = 0x0819E000,  // - 0x0819FFFF |   8 KiB
    [208] = 0x081A0000,  // - 0x081A1FFF |   8 KiB
    [209] = 0x081A2000,  // - 0x081A3FFF |   8 KiB
    [210] = 0x081A4000,  // - 0x081A5FFF |   8 KiB
    [211] = 0x081A6000,  // - 0x081A7FFF |   8 KiB
    [212] = 0x081A8000,  // - 0x081A9FFF |   8 KiB
    [213] = 0x081AA000,  // - 0x081ABFFF |   8 KiB
    [214] = 0x081AC000,  // - 0x081ADFFF |   8 KiB
    [215] = 0x081AE000,  // - 0x081AFFFF |   8 KiB
    [216] = 0x081B0000,  // - 0x081B1FFF |   8 KiB
    [217] = 0x081B2000,  // - 0x081B3FFF |   8 KiB
    [218] = 0x081B4000,  // - 0x081B5FFF |   8 KiB
    [219] = 0x081B6000,  // - 0x081B7FFF |   8 KiB
    [220] = 0x081B8000,  // - 0x081B9FFF |   8 KiB
    [221] = 0x081BA000,  // - 0x081BBFFF |   8 KiB
    [222] = 0x081BC000,  // - 0x081BDFFF |   8 KiB
    [223] = 0x081BE000,  // - 0x081BFFFF |   8 KiB
    [224] = 0x081C0000,  // - 0x081C1FFF |   8 KiB
    [225] = 0x081C2000,  // - 0x081C3FFF |   8 KiB
    [226] = 0x081C4000,  // - 0x081C5FFF |   8 KiB
    [227] = 0x081C6000,  // - 0x081C7FFF |   8 KiB
    [228] = 0x081C8000,  // - 0x081C9FFF |   8 KiB
    [229] = 0x081CA000,  // - 0x081CBFFF |   8 KiB
    [230] = 0x081CC000,  // - 0x081CDFFF |   8 KiB
    [231] = 0x081CE000,  // - 0x081CFFFF |   8 KiB
    [232] = 0x081D0000,  // - 0x081D1FFF |   8 KiB
    [233] = 0x081D2000,  // - 0x081D3FFF |   8 KiB
    [234] = 0x081D4000,  // - 0x081D5FFF |   8 KiB
    [235] = 0x081D6000,  // - 0x081D7FFF |   8 KiB
    [236] = 0x081D8000,  // - 0x081D9FFF |   8 KiB
    [237] = 0x081DA000,  // - 0x081DBFFF |   8 KiB
    [238] = 0x081DC000,  // - 0x081DDFFF |   8 KiB
    [239] = 0x081DE000,  // - 0x081DFFFF |   8 KiB
    [240] = 0x081E0000,  // - 0x081E1FFF |   8 KiB
    [241] = 0x081E2000,  // - 0x081E3FFF |   8 KiB
    [242] = 0x081E4000,  // - 0x081E5FFF |   8 KiB
    [243] = 0x081E6000,  // - 0x081E7FFF |   8 KiB
    [244] = 0x081E8000,  // - 0x081E9FFF |   8 KiB
    [245] = 0x081EA000,  // - 0x081EBFFF |   8 KiB
    [246] = 0x081EC000,  // - 0x081EDFFF |   8 KiB
    [247] = 0x081EE000,  // - 0x081EFFFF |   8 KiB
    [248] = 0x081F0000,  // - 0x081F1FFF |   8 KiB
    [249] = 0x081F2000,  // - 0x081F3FFF |   8 KiB
    [250] = 0x081F4000,  // - 0x081F5FFF |   8 KiB
    [251] = 0x081F6000,  // - 0x081F7FFF |   8 KiB
    [252] = 0x081F8000,  // - 0x081F9FFF |   8 KiB
    [253] = 0x081FA000,  // - 0x081FBFFF |   8 KiB
    [254] = 0x081FC000,  // - 0x081FDFFF |   8 KiB
    [255] = 0x081FE000,  // - 0x081FFFFF |   8 KiB
    [256] = 0x081FFFFF,  // last element - not a valid sector
#else
#error Unknown Trezor model
#endif
};

static uint8_t *FLASH_BUFFER = NULL;
static uint32_t FLASH_SIZE;

static void flash_exit(void) {
  int r = munmap(FLASH_BUFFER, FLASH_SIZE);
  ensure(sectrue * (r == 0), "munmap failed");
}

void flash_init(void) {
  if (FLASH_BUFFER) return;

  FLASH_SIZE = FLASH_SECTOR_TABLE[FLASH_SECTOR_COUNT] - FLASH_SECTOR_TABLE[0];

  // check whether the file exists and it has the correct size
  struct stat sb;
  int r = stat(FLASH_FILE, &sb);

  // (re)create if non existent or wrong size
  if (r != 0 || sb.st_size != FLASH_SIZE) {
    int fd = open(FLASH_FILE, O_RDWR | O_CREAT | O_TRUNC, (mode_t)0600);
    ensure(sectrue * (fd >= 0), "open failed");
    for (int i = 0; i < FLASH_SIZE / 16; i++) {
      ssize_t s = write(
          fd,
          "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF",
          16);
      ensure(sectrue * (s >= 0), "write failed");
    }
    r = close(fd);
    ensure(sectrue * (r == 0), "close failed");
  }

  // mmap file
  int fd = open(FLASH_FILE, O_RDWR);
  ensure(sectrue * (fd >= 0), "open failed");

  void *map = mmap(0, FLASH_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  ensure(sectrue * (map != MAP_FAILED), "mmap failed");

  FLASH_BUFFER = (uint8_t *)map;

  atexit(flash_exit);
}

secbool flash_unlock_write(void) { return sectrue; }

secbool flash_lock_write(void) { return sectrue; }

const void *flash_get_address(uint16_t sector, uint32_t offset, uint32_t size) {
  if (sector >= FLASH_SECTOR_COUNT) {
    return NULL;
  }
  const uint32_t addr = FLASH_SECTOR_TABLE[sector] + offset;
  const uint32_t next = FLASH_SECTOR_TABLE[sector + 1];
  if (addr + size > next) {
    return NULL;
  }
  return FLASH_BUFFER + addr - FLASH_SECTOR_TABLE[0];
}

uint32_t flash_sector_size(uint16_t first_sector, uint16_t sector_count) {
  if (first_sector + sector_count > FLASH_SECTOR_COUNT) {
    return 0;
  }
  return FLASH_SECTOR_TABLE[first_sector + sector_count] -
         FLASH_SECTOR_TABLE[first_sector];
}

uint16_t flash_sector_find(uint16_t first_sector, uint32_t offset) {
  uint16_t sector = first_sector;

  while (sector < FLASH_SECTOR_COUNT) {
    uint32_t sector_size =
        FLASH_SECTOR_TABLE[sector + 1] - FLASH_SECTOR_TABLE[sector];

    if (offset < sector_size) {
      break;
    }
    offset -= sector_size;
    sector++;
  }

  return sector;
}

secbool flash_sector_erase(uint16_t sector) {
  if (sector >= FLASH_SECTOR_COUNT) {
    return secfalse;
  }

  const uint32_t offset = FLASH_SECTOR_TABLE[sector] - FLASH_SECTOR_TABLE[0];

  const uint32_t size =
      FLASH_SECTOR_TABLE[sector + 1] - FLASH_SECTOR_TABLE[sector];

  memset(FLASH_BUFFER + offset, 0xFF, size);

  return sectrue;
}

secbool flash_write_byte(uint16_t sector, uint32_t offset, uint8_t data) {
  uint8_t *flash = (uint8_t *)flash_get_address(sector, offset, 1);
  if (!flash) {
    return secfalse;
  }
  if ((flash[0] & data) != data) {
    return secfalse;  // we cannot change zeroes to ones
  }
  flash[0] = data;
  return sectrue;
}

secbool flash_write_word(uint16_t sector, uint32_t offset, uint32_t data) {
  if (offset % sizeof(uint32_t)) {  // we write only at 4-byte boundary
    return secfalse;
  }
  uint32_t *flash = (uint32_t *)flash_get_address(sector, offset, sizeof(data));
  if (!flash) {
    return secfalse;
  }
  if ((flash[0] & data) != data) {
    return secfalse;  // we cannot change zeroes to ones
  }
  flash[0] = data;
  return sectrue;
}

secbool flash_write_block(uint16_t sector, uint32_t offset,
                          const flash_block_t block) {
  if (offset % (sizeof(uint32_t) *
                FLASH_BLOCK_WORDS)) {  // we write only at block boundary
    return secfalse;
  }

  for (int i = 0; i < FLASH_BLOCK_WORDS; i++) {
    if (!flash_write_word(sector, offset + i * sizeof(uint32_t), block[i])) {
      return secfalse;
    }
  }
  return sectrue;
}
