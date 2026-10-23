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

/**
 * Battery Data: HCF343837NCZ
 * Auto-generated from battery characterization data
 * Contains lookup tables and parameters for the specific battery model
 */

#pragma once

#include <trezor_types.h>

/**
 * Battery Specifications:
 * Model: HCF343837NCZ
 * Chemistry: LiFePO4
 */

// Configuration
#define BATTERY_HCF343837NCZ_NUM_TEMP_POINTS 9

// SOC breakpoints for piecewise functions
#define BATTERY_HCF343837NCZ_SOC_BREAKPOINT_1 0.2f
#define BATTERY_HCF343837NCZ_SOC_BREAKPOINT_2 0.7f

// Temperature points arrays (in Celsius)
// Discharge temperatures
static const float BATTERY_HCF343837NCZ_TEMP_POINTS_DISCHG
    [BATTERY_HCF343837NCZ_NUM_TEMP_POINTS] = {
        1.02f, 5.86f, 10.72f, 15.56f, 20.49f, 30.36f, 35.31f, 40.32f, 45.34f};

// Charge temperatures
static const float
    BATTERY_HCF343837NCZ_TEMP_POINTS_CHG[BATTERY_HCF343837NCZ_NUM_TEMP_POINTS] =
        {2.39f, 7.37f, 12.68f, 17.53f, 22.46f, 32.26f, 37.22f, 42.17f, 47.15f};

// Internal resistance curve parameters (rational function parameters
// a+b*t)/(c+d*t)
static const float BATTERY_HCF343837NCZ_R_INT_PARAMS[4] = {
    // a, b, c, d for rational function (a + b*t)/(c + d*t)
    5148.694149f, 126.612310f, 6446.087576f, 437.006759f};

// Discharge OCV curve parameters for each temperature
static const float BATTERY_HCF343837NCZ_OCV_DISCHARGE_PARAMS
    [BATTERY_HCF343837NCZ_NUM_TEMP_POINTS][10] = {
        // Temperature: 1.02°C (key: 0)
        {
            0.132744f, 3.209158f,  // m, b (linear segment)
            -377.860239f, -5173.820403f, -123.475291f,
            -1567.959576f,  // a1, b1, c1, d1 (first rational segment)
            6416.385096f, -6367.610930f, 1943.981986f,
            -1931.427092f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 5.86°C (key: 5)
        {
            0.126718f, 3.219663f,  // m, b (linear segment)
            -658.352709f, -9465.436646f, -215.671511f,
            -2858.499585f,  // a1, b1, c1, d1 (first rational segment)
            1103.603880f, -1089.643805f, 333.742552f,
            -329.897901f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 10.72°C (key: 10)
        {
            0.108352f, 3.229992f,  // m, b (linear segment)
            -2493.910531f, -28133.328290f, -817.138793f,
            -8431.792420f,  // a1, b1, c1, d1 (first rational segment)
            1615.858515f, -4201.535059f, 475.291094f,
            -1251.915058f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 15.56°C (key: 15)
        {
            0.111289f, 3.231867f,  // m, b (linear segment)
            -4966.693381f, -49873.913621f, -1623.977390f,
            -14898.978255f,  // a1, b1, c1, d1 (first rational segment)
            1012.376908f, -1993.599184f, 301.394188f,
            -595.999103f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 20.49°C (key: 20)
        {
            0.120106f, 3.229563f,  // m, b (linear segment)
            268.096564f, 2874.958069f, 87.433893f,
            861.258620f,  // a1, b1, c1, d1 (first rational segment)
            -1770.509656f, 3559.122578f, -527.259884f,
            1063.803643f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 30.36°C (key: 30)
        {
            0.137237f, 3.223399f,  // m, b (linear segment)
            1038.166704f, 18767.842731f, 339.512092f,
            5677.727929f,  // a1, b1, c1, d1 (first rational segment)
            -1351.860989f, 2612.204208f, -403.454434f,
            781.043397f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 35.31°C (key: 35)
        {
            0.143897f, 3.223448f,  // m, b (linear segment)
            13894.623462f, 290634.247388f, 4549.590583f,
            88020.681469f,  // a1, b1, c1, d1 (first rational segment)
            -2937.654993f, 148.254576f, -891.816102f,
            59.282724f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 40.32°C (key: 40)
        {
            0.156721f, 3.219657f,  // m, b (linear segment)
            486.002705f, 11027.269400f, 159.266245f,
            3343.274892f,  // a1, b1, c1, d1 (first rational segment)
            -362.733040f, 361.915501f, -108.955783f,
            108.840505f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 45.34°C (key: 45)
        {
            0.156192f, 3.221027f,  // m, b (linear segment)
            477.405525f, 10988.255232f, 156.524863f,
            3330.213529f,  // a1, b1, c1, d1 (first rational segment)
            496.936214f, -496.194305f, 149.219279f,
            -149.173026f  // a3, b3, c3, d3 (third rational segment)
        }};

// Charge OCV curve parameters for each temperature
static const float BATTERY_HCF343837NCZ_OCV_CHARGE_PARAMS
    [BATTERY_HCF343837NCZ_NUM_TEMP_POINTS][10] = {
        // Temperature: 2.39°C (key: 0)
        {
            0.087208f, 3.332748f,  // m, b (linear segment)
            262.388264f, 33277.522403f, 82.663155f,
            9902.336513f,  // a1, b1, c1, d1 (first rational segment)
            350.518328f, -324.259695f, 104.652569f,
            -97.343933f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 7.37°C (key: 5)
        {
            0.137945f, 3.291426f,  // m, b (linear segment)
            244.061830f, 14327.472407f, 78.683519f,
            4286.625957f,  // a1, b1, c1, d1 (first rational segment)
            120.553563f, -109.825804f, 36.170685f,
            -33.200196f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 12.68°C (key: 10)
        {
            0.145137f, 3.277093f,  // m, b (linear segment)
            63.104078f, 2993.710560f, 20.495998f,
            897.719518f,  // a1, b1, c1, d1 (first rational segment)
            648.380265f, -559.549859f, 196.709317f,
            -171.937183f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 17.53°C (key: 15)
        {
            0.136263f, 3.272912f,  // m, b (linear segment)
            410.756037f, 20687.122117f, 133.039482f,
            6220.274827f,  // a1, b1, c1, d1 (first rational segment)
            354.112527f, -327.223549f, 106.665466f,
            -99.204169f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 22.46°C (key: 20)
        {
            0.134281f, 3.270871f,  // m, b (linear segment)
            518.429721f, 24701.422489f, 168.372867f,
            7429.281380f,  // a1, b1, c1, d1 (first rational segment)
            253.931799f, -239.537581f, 76.297951f,
            -72.320239f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 32.26°C (key: 30)
        {
            0.127118f, 3.265582f,  // m, b (linear segment)
            266.663194f, 9172.306429f, 86.480023f,
            2759.277240f,  // a1, b1, c1, d1 (first rational segment)
            161.967344f, -159.021597f, 48.451837f,
            -47.664881f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 37.22°C (key: 35)
        {
            0.120619f, 3.268397f,  // m, b (linear segment)
            173.617347f, 5728.679569f, 56.323639f,
            1721.968776f,  // a1, b1, c1, d1 (first rational segment)
            80.505082f, -79.040169f, 24.096966f,
            -23.704603f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 42.17°C (key: 40)
        {
            0.092222f, 3.287151f,  // m, b (linear segment)
            -57.313130f, -822.995842f, -17.883998f,
            -246.343999f,  // a1, b1, c1, d1 (first rational segment)
            440.636027f, -435.083990f, 131.783395f,
            -130.300948f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 47.15°C (key: 45)
        {
            0.128932f, 3.261763f,  // m, b (linear segment)
            120.858087f, 3927.216714f, 39.505813f,
            1180.973085f,  // a1, b1, c1, d1 (first rational segment)
            447.508970f, -441.668629f, 133.782446f,
            -132.244176f  // a3, b3, c3, d3 (third rational segment)
        }};

// Battery capacity data for each temperature
static const float
    BATTERY_HCF343837NCZ_CAPACITY[BATTERY_HCF343837NCZ_NUM_TEMP_POINTS][2] = {
        // Temperature: 1.02°C (key: 0)
        {274.60f, 301.37f},
        // Temperature: 5.86°C (key: 5)
        {305.00f, 362.34f},
        // Temperature: 10.72°C (key: 10)
        {327.00f, 382.02f},
        // Temperature: 15.56°C (key: 15)
        {338.20f, 384.26f},
        // Temperature: 20.49°C (key: 20)
        {354.99f, 389.48f},
        // Temperature: 30.36°C (key: 30)
        {362.31f, 389.79f},
        // Temperature: 35.31°C (key: 35)
        {364.07f, 389.98f},
        // Temperature: 40.32°C (key: 40)
        {363.84f, 353.93f},
        // Temperature: 45.34°C (key: 45)
        {364.62f, 391.60f}};
