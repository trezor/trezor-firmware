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

#pragma once

// I2C address of the DRV2625 on the I2C bus.
#define DRV2625_I2C_ADDRESS 0x5A

// ------------------------------------------------------------
// DRV2625 registers
// ------------------------------------------------------------

#define DRV2625_REG_CHIPID 0x00
#define DRV2625_REG_STATUS 0x01
#define DRV2625_REG_MODE 0x07
#define DRV2625_REG_MODE_RTP 0
#define DRV2625_REG_MODE_WAVEFORM 0x01
#define DRV2625_REG_MODE_DIAG 0x02
#define DRV2625_REG_MODE_AUTOCAL 0x03
#define DRV2625_REG_MODE_TRGFUNC_PULSE 0x00
#define DRV2625_REG_MODE_TRGFUNC_ENABLE 0x04
#define DRV2625_REG_MODE_TRGFUNC_INTERRUPT 0x08

#define DRV2625_REG_LRAERM 0x08
#define DRV2625_REG_LRAERM_LRA 0x80
#define DRV2625_REG_LRAERM_OPENLOOP 0x40
#define DRV2625_REG_LRAERM_AUTO_BRK_OL 0x10
#define DRV2625_REG_LRAERM_AUTO_BRK_STBY 0x08

#define DRV2625_REG_LIBRARY 0x0D  ///< Waveform library selection register
#define DRV2625_REG_LIBRARY_OPENLOOP 0x40
#define DRV2625_REG_LIBRARY_GAIN_100 0x00
#define DRV2625_REG_LIBRARY_GAIN_75 0x01
#define DRV2625_REG_LIBRARY_GAIN_50 0x02
#define DRV2625_REG_LIBRARY_GAIN_25 0x03

#define DRV2625_REG_RTP 0x0E  ///< RTP input register

#define DRV2625_REG_WAVESEQ1 0x0F  ///< Waveform sequence register 1
#define DRV2625_REG_WAVESEQ2 0x10  ///< Waveform sequence register 2
#define DRV2625_REG_WAVESEQ3 0x11  ///< Waveform sequence register 3
#define DRV2625_REG_WAVESEQ4 0x12  ///< Waveform sequence register 4
#define DRV2625_REG_WAVESEQ5 0x13  ///< Waveform sequence register 5
#define DRV2625_REG_WAVESEQ6 0x14  ///< Waveform sequence register 6
#define DRV2625_REG_WAVESEQ7 0x15  ///< Waveform sequence register 7
#define DRV2625_REG_WAVESEQ8 0x16  ///< Waveform sequence register 8

#define DRV2625_REG_GO 0x0C  ///< Go register
#define DRV2625_REG_GO_GO 0x01

#define DRV2625_REG_OD_CLAMP 0x20
#define DRV2625_REG_RATED_VOLTAGE 0x20

#define DRV2625_REG_LRA_WAVE_SHAPE 0x2C
#define DRV2625_REG_LRA_WAVE_SHAPE_SINE 0x01

#define DRV2625_REG_OL_LRA_PERIOD_LO 0x2F
#define DRV2625_REG_OL_LRA_PERIOD_HI 0x2E

// ------------------------------------------------------------
// DRV2625 effect types
// ------------------------------------------------------------

typedef enum {
  STRONG_CLICK_100 = 1,
  STRONG_CLICK_60 = 2,
  STRONG_CLICK_30 = 3,
  SHARP_CLICK_100 = 4,
  SHARP_CLICK_60 = 5,
  SHARP_CLICK_30 = 6,
  SOFT_BUMP_100 = 7,
  SOFT_BUMP_60 = 8,
  SOFT_BUMP_30 = 9,
  DOUBLE_CLICK_100 = 10,
  DOUBLE_CLICK_60 = 11,
  TRIPLE_CLICK_100 = 12,
  SOFT_FUZZ_60 = 13,
  STRONG_BUZZ_100 = 14,
  ALERT_750MS_100 = 15,
  ALERT_1000MS_100 = 16,
  STRONG_CLICK_1_100 = 17,
  STRONG_CLICK_2_80 = 18,
  STRONG_CLICK_3_60 = 19,
  STRONG_CLICK_4_30 = 20,
  MEDIUM_CLICK_1_100 = 21,
  MEDIUM_CLICK_2_80 = 22,
  MEDIUM_CLICK_3_60 = 23,
  SHARP_TICK_1_100 = 24,
  SHARP_TICK_2_80 = 25,
  SHARP_TICK_3_60 = 26,
  SHORT_DOUBLE_CLICK_STRONG_1_100 = 27,
  SHORT_DOUBLE_CLICK_STRONG_2_80 = 28,
  SHORT_DOUBLE_CLICK_STRONG_3_60 = 29,
  SHORT_DOUBLE_CLICK_STRONG_4_30 = 30,
  SHORT_DOUBLE_CLICK_MEDIUM_1_100 = 31,
  SHORT_DOUBLE_CLICK_MEDIUM_2_80 = 32,
  SHORT_DOUBLE_CLICK_MEDIUM_3_60 = 33,
  SHORT_DOUBLE_SHARP_TICK_1_100 = 34,
  SHORT_DOUBLE_SHARP_TICK_2_80 = 35,
  SHORT_DOUBLE_SHARP_TICK_3_60 = 36,
  LONG_DOUBLE_SHARP_TICK_STRONG_1_100 = 37,
  LONG_DOUBLE_SHARP_TICK_STRONG_2_80 = 38,
  LONG_DOUBLE_SHARP_TICK_STRONG_3_60 = 39,
  LONG_DOUBLE_SHARP_TICK_STRONG_4_30 = 40,
  LONG_DOUBLE_SHARP_TICK_MEDIUM_1_100 = 41,
  LONG_DOUBLE_SHARP_TICK_MEDIUM_2_80 = 42,
  LONG_DOUBLE_SHARP_TICK_MEDIUM_3_60 = 43,
  LONG_DOUBLE_SHARP_TICK_1_100 = 44,
  LONG_DOUBLE_SHARP_TICK_2_80 = 45,
  LONG_DOUBLE_SHARP_TICK_3_60 = 46,
  BUZZ_1_100 = 47,
  BUZZ_2_80 = 48,
  BUZZ_3_60 = 49,
  BUZZ_4_40 = 50,
  BUZZ_5_20 = 51,
  PULSING_STRONG_1_100 = 52,
  PULSING_STRONG_2_60 = 53,
  PULSING_MEDIUM_1_100 = 54,
  PULSING_MEDIUM_2_60 = 55,
  PULSING_SHARP_1_100 = 56,
  PULSING_SHARP_2_60 = 57,
  TRANSITION_CLICK_1_100 = 58,
  TRANSITION_CLICK_2_80 = 59,
  TRANSITION_CLICK_3_60 = 60,
  TRANSITION_CLICK_4_40 = 61,
  TRANSITION_CLICK_5_20 = 62,
  TRANSITION_CLICK_6_10 = 63,
  TRANSITION_HUM_1_100 = 64,
  TRANSITION_HUM_2_80 = 65,
  TRANSITION_HUM_3_60 = 66,
  TRANSITION_HUM_4_40 = 67,
  TRANSITION_HUM_5_20 = 68,
  TRANSITION_HUM_6_10 = 69,
  TRANSITION_RAMP_DOWN_LONG_SMOOTH_1 = 70,
  TRANSITION_RAMP_DOWN_LONG_SMOOTH_2 = 71,
  TRANSITION_RAMP_DOWN_MEDIUM_SMOOTH_1 = 72,
  TRANSITION_RAMP_DOWN_MEDIUM_SMOOTH_2 = 73,
  TRANSITION_RAMP_DOWN_SHORT_SMOOTH_1 = 74,
  TRANSITION_RAMP_DOWN_SHORT_SMOOTH_2 = 75,
  TRANSITION_RAMP_DOWN_LONG_SHARP_1 = 76,
  TRANSITION_RAMP_DOWN_LONG_SHARP_2 = 77,
  TRANSITION_RAMP_DOWN_MEDIUM_SHARP_1 = 78,
  TRANSITION_RAMP_DOWN_MEDIUM_SHARP_2 = 79,
  TRANSITION_RAMP_DOWN_SHORT_SHARP_1 = 80,
  TRANSITION_RAMP_DOWN_SHORT_SHARP_2 = 81,
  TRANSITION_RAMP_UP_LONG_SMOOTH_1 = 82,
  TRANSITION_RAMP_UP_LONG_SMOOTH_2 = 83,
  TRANSITION_RAMP_UP_MEDIUM_SMOOTH_1 = 84,
  TRANSITION_RAMP_UP_MEDIUM_SMOOTH_2 = 85,
  TRANSITION_RAMP_UP_SHORT_SMOOTH_1 = 86,
  TRANSITION_RAMP_UP_SHORT_SMOOTH_2 = 87,
  TRANSITION_RAMP_UP_LONG_SHARP_1 = 88,
  TRANSITION_RAMP_UP_LONG_SHARP_2 = 89,
  TRANSITION_RAMP_UP_MEDIUM_SHARP_1 = 90,
  TRANSITION_RAMP_UP_MEDIUM_SHARP_2 = 91,
  TRANSITION_RAMP_UP_SHORT_SHARP_1 = 92,
  TRANSITION_RAMP_UP_SHORT_SHARP_2 = 93,
  TRANSITION_RAMP_DOWN_LONG_SMOOTH_1_50 = 94,
  TRANSITION_RAMP_DOWN_LONG_SMOOTH_2_50 = 95,
  TRANSITION_RAMP_DOWN_MEDIUM_SMOOTH_1_50 = 96,
  TRANSITION_RAMP_DOWN_MEDIUM_SMOOTH_2_50 = 97,
  TRANSITION_RAMP_DOWN_SHORT_SMOOTH_1_50 = 98,
  TRANSITION_RAMP_DOWN_SHORT_SMOOTH_2_50 = 99,
  TRANSITION_RAMP_DOWN_LONG_SHARP_1_50 = 100,
  TRANSITION_RAMP_DOWN_LONG_SHARP_2_50 = 101,
  TRANSITION_RAMP_DOWN_MEDIUM_SHARP_1_50 = 102,
  TRANSITION_RAMP_DOWN_MEDIUM_SHARP_2_50 = 103,
  TRANSITION_RAMP_DOWN_SHORT_SHARP_1_50 = 104,
  TRANSITION_RAMP_DOWN_SHORT_SHARP_2_50 = 105,
  TRANSITION_RAMP_UP_LONG_SMOOTH_1_50 = 106,
  TRANSITION_RAMP_UP_LONG_SMOOTH_2_50 = 107,
  TRANSITION_RAMP_UP_MEDIUM_SMOOTH_1_50 = 108,
  TRANSITION_RAMP_UP_MEDIUM_SMOOTH_2_50 = 109,
  TRANSITION_RAMP_UP_SHORT_SMOOTH_1_50 = 110,
  TRANSITION_RAMP_UP_SHORT_SMOOTH_2_50 = 111,
  TRANSITION_RAMP_UP_LONG_SHARP_1_50 = 112,
  TRANSITION_RAMP_UP_LONG_SHARP_2_50 = 113,
  TRANSITION_RAMP_UP_MEDIUM_SHARP_1_50 = 114,
  TRANSITION_RAMP_UP_MEDIUM_SHARP_2_50 = 115,
  TRANSITION_RAMP_UP_SHORT_SHARP_1_50 = 116,
  TRANSITION_RAMP_UP_SHORT_SHARP_2_50 = 117,
  LONG_BUZZ_FROM_PROGRAMMATIC_STOPPING = 118,
  SMOOTH_HUM_1_100 = 119,
  SMOOTH_HUM_2_80 = 120,
  SMOOTH_HUM_3_60 = 121,
  SMOOTH_HUM_4_40 = 122,
  SMOOTH_HUM_5_20 = 123,
} drv2625_lib_effect_t;
