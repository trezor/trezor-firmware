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
 * Battery Data: JYHPFL333838
 * Auto-generated from battery characterization data
 * Contains lookup tables and parameters for the specific battery model
 */

#pragma once

#include <trezor_types.h>

/**
 * Battery Specifications:
 * Model: JYHPFL333838
 * Chemistry: LiFePO4
 */

// Configuration
#define BATTERY_JYHPFL333838_NUM_TEMP_POINTS 10

// SOC breakpoints for piecewise functions
#define BATTERY_JYHPFL333838_SOC_BREAKPOINT_1 0.25f
#define BATTERY_JYHPFL333838_SOC_BREAKPOINT_2 0.8f

// Temperature points arrays (in Celsius)
// Discharge temperatures
static const float BATTERY_JYHPFL333838_TEMP_POINTS_DISCHG
    [BATTERY_JYHPFL333838_NUM_TEMP_POINTS] = {1.20f,  6.02f,  10.82f, 15.66f,
                                              20.54f, 25.39f, 30.25f, 35.18f,
                                              40.11f, 45.10f};

// Charge temperatures
static const float
    BATTERY_JYHPFL333838_TEMP_POINTS_CHG[BATTERY_JYHPFL333838_NUM_TEMP_POINTS] =
        {2.84f,  7.65f,  12.96f, 17.80f, 22.67f,
         27.54f, 32.36f, 37.25f, 42.19f, 47.14f};

// Internal resistance curve parameters (rational function parameters
// a+b*t)/(c+d*t)
static const float BATTERY_JYHPFL333838_R_INT_PARAMS[4] = {
    // a, b, c, d for rational function (a + b*t)/(c + d*t)
    610.420875f, 17.843781f, 696.659674f, 63.429549f};

// Discharge OCV curve parameters for each temperature
static const float BATTERY_JYHPFL333838_OCV_DISCHARGE_PARAMS
    [BATTERY_JYHPFL333838_NUM_TEMP_POINTS][10] = {
        // Temperature: 1.20°C (key: 0)
        {
            0.126702f, 3.203315f,  // m, b (linear segment)
            11.023599f, 106.085148f, 3.598773f,
            32.028392f,  // a1, b1, c1, d1 (first rational segment)
            1277.990728f, -1271.445603f, 386.919821f,
            -384.988749f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 6.02°C (key: 5)
        {
            0.131380f, 3.207245f,  // m, b (linear segment)
            72.815639f, 666.592195f, 23.819540f,
            200.347822f,  // a1, b1, c1, d1 (first rational segment)
            1188.462373f, -1183.410865f, 358.920808f,
            -357.426584f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 10.82°C (key: 10)
        {
            0.134383f, 3.211193f,  // m, b (linear segment)
            694.784001f, 5880.951793f, 226.842317f,
            1761.552942f,  // a1, b1, c1, d1 (first rational segment)
            -2439.402815f, 2426.704902f, -735.278568f,
            731.510052f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 15.66°C (key: 15)
        {
            0.138715f, 3.214329f,  // m, b (linear segment)
            159.052685f, 1690.401977f, 51.878081f,
            508.587170f,  // a1, b1, c1, d1 (first rational segment)
            1084.691155f, -1082.324350f, 326.236079f,
            -325.534997f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 20.54°C (key: 20)
        {
            0.141409f, 3.216984f,  // m, b (linear segment)
            43.200571f, 606.882819f, 14.109561f,
            183.292567f,  // a1, b1, c1, d1 (first rational segment)
            2453.465092f, -2450.207975f, 736.801949f,
            -735.836397f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 25.39°C (key: 25)
        {
            0.142277f, 3.219692f,  // m, b (linear segment)
            825.309207f, 14179.043553f, 270.130480f,
            4289.332517f,  // a1, b1, c1, d1 (first rational segment)
            3633.932971f, -3631.845578f, 1090.147677f,
            -1089.528218f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 30.25°C (key: 30)
        {
            0.142527f, 3.221902f,  // m, b (linear segment)
            267.194722f, 4775.525707f, 87.476021f,
            1444.184771f,  // a1, b1, c1, d1 (first rational segment)
            -8213.747803f, 8212.751696f, -2462.224052f,
            2461.928626f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 35.18°C (key: 35)
        {
            0.142494f, 3.223499f,  // m, b (linear segment)
            894.361314f, 16712.949502f, 293.056689f,
            5053.496993f,  // a1, b1, c1, d1 (first rational segment)
            7370.015442f, -7370.625470f, 2208.241069f,
            -2208.422024f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 40.11°C (key: 40)
        {
            0.141720f, 3.224820f,  // m, b (linear segment)
            417.203118f, 7836.144780f, 136.768407f,
            2368.333770f,  // a1, b1, c1, d1 (first rational segment)
            6428.631685f, -6430.699149f, 1925.756247f,
            -1926.369615f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 45.10°C (key: 45)
        {
            0.140212f, 3.226317f,  // m, b (linear segment)
            550.627184f, 10296.917878f, 180.517837f,
            3110.498427f,  // a1, b1, c1, d1 (first rational segment)
            -3345.517720f, 3346.787783f, -1002.091702f,
            1002.468503f  // a3, b3, c3, d3 (third rational segment)
        }};

// Charge OCV curve parameters for each temperature
static const float BATTERY_JYHPFL333838_OCV_CHARGE_PARAMS
    [BATTERY_JYHPFL333838_NUM_TEMP_POINTS][10] = {
        // Temperature: 2.84°C (key: 0)
        {
            0.106475f, 3.318151f,  // m, b (linear segment)
            -14.045089f, -1226.311963f, -4.347672f,
            -366.041525f,  // a1, b1, c1, d1 (first rational segment)
            1070.558858f, -1037.613037f, 317.191883f,
            -308.168858f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 7.65°C (key: 5)
        {
            0.102477f, 3.308675f,  // m, b (linear segment)
            -0.878797f, -34.044968f, -0.273191f,
            -10.172039f,  // a1, b1, c1, d1 (first rational segment)
            1170.137272f, -1142.421322f, 347.439588f,
            -339.848657f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 12.96°C (key: 10)
        {
            0.110985f, 3.288082f,  // m, b (linear segment)
            -95.542322f, -1913.725451f, -29.960661f,
            -572.562062f,  // a1, b1, c1, d1 (first rational segment)
            1241.862566f, -1196.979674f, 371.790254f,
            -359.507652f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 17.80°C (key: 15)
        {
            0.108478f, 3.281443f,  // m, b (linear segment)
            0.157392f, 1.712027f, 0.049492f,
            0.509770f,  // a1, b1, c1, d1 (first rational segment)
            1192.978731f, -1161.538226f, 357.109128f,
            -348.505427f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 22.67°C (key: 20)
        {
            0.108073f, 3.276199f,  // m, b (linear segment)
            72.636119f, 644.341350f, 22.910105f,
            191.382416f,  // a1, b1, c1, d1 (first rational segment)
            972.064158f, -956.738429f, 290.499768f,
            -286.298033f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 27.54°C (key: 25)
        {
            0.115319f, 3.269345f,  // m, b (linear segment)
            16.396740f, 311.905967f, 5.271973f,
            93.367211f,  // a1, b1, c1, d1 (first rational segment)
            1111.550297f, -1097.707047f, 331.943219f,
            -328.145698f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 32.36°C (key: 30)
        {
            0.116052f, 3.267403f,  // m, b (linear segment)
            41.221264f, 817.918853f, 13.276687f,
            245.036453f,  // a1, b1, c1, d1 (first rational segment)
            1085.264164f, -1077.073143f, 323.725175f,
            -321.475891f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 37.25°C (key: 35)
        {
            0.115131f, 3.267480f,  // m, b (linear segment)
            17.359462f, 345.261707f, 5.603591f,
            103.394636f,  // a1, b1, c1, d1 (first rational segment)
            1130.349129f, -1123.746416f, 337.060838f,
            -335.246964f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 42.19°C (key: 40)
        {
            0.114044f, 3.267777f,  // m, b (linear segment)
            57.975538f, 1174.969083f, 18.756850f,
            351.777353f,  // a1, b1, c1, d1 (first rational segment)
            1022.343802f, -1017.883339f, 304.768153f,
            -303.542651f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 47.14°C (key: 45)
        {
            0.112035f, 3.269741f,  // m, b (linear segment)
            28.634200f, 559.963514f, 9.277864f,
            167.422055f,  // a1, b1, c1, d1 (first rational segment)
            1114.364131f, -1108.686878f, 332.145661f,
            -330.562526f  // a3, b3, c3, d3 (third rational segment)
        }};

// Battery capacity data for each temperature
static const float
    BATTERY_JYHPFL333838_CAPACITY[BATTERY_JYHPFL333838_NUM_TEMP_POINTS][2] = {
        // Temperature: 1.20°C (key: 0)
        {282.28f, 272.69f},
        // Temperature: 6.02°C (key: 5)
        {313.09f, 303.77f},
        // Temperature: 10.82°C (key: 10)
        {331.90f, 338.43f},
        // Temperature: 15.66°C (key: 15)
        {345.53f, 357.56f},
        // Temperature: 20.54°C (key: 20)
        {353.35f, 367.91f},
        // Temperature: 25.39°C (key: 25)
        {359.08f, 377.93f},
        // Temperature: 30.25°C (key: 30)
        {364.63f, 383.03f},
        // Temperature: 35.18°C (key: 35)
        {368.55f, 387.07f},
        // Temperature: 40.11°C (key: 40)
        {370.95f, 389.48f},
        // Temperature: 45.10°C (key: 45)
        {374.49f, 393.99f}};
