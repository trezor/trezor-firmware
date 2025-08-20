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
#define BATTERY_NUM_TEMP_POINTS 10

// SOC breakpoints for piecewise functions
#define BATTERY_SOC_BREAKPOINT_1 0.25f
#define BATTERY_SOC_BREAKPOINT_2 0.8f

// Temperature points arrays (in Celsius)
// Discharge temperatures
static const float BATTERY_TEMP_POINTS_DISCHG[BATTERY_NUM_TEMP_POINTS] = {
    0.80f,  5.78f,  10.64f, 15.55f, 20.65f,
    25.42f, 31.41f, 35.41f, 40.39f, 45.29f};

// Charge temperatures
static const float BATTERY_TEMP_POINTS_CHG[BATTERY_NUM_TEMP_POINTS] = {
    2.32f,  7.28f,  12.60f, 17.51f, 22.50f,
    27.46f, 32.31f, 37.36f, 42.34f, 47.35f};

// Internal resistance curve parameters (rational function parameters
// a+b*t)/(c+d*t)
static const float BATTERY_R_INT_PARAMS[4] = {
    // a, b, c, d for rational function (a + b*t)/(c + d*t)
    3.700987f, 0.063115f, 4.059870f, 0.273364f};

// Discharge OCV curve parameters for each temperature
static const float BATTERY_OCV_DISCHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS][10] = {
    // Temperature: 0.80°C (key: 0)
    {
        0.126550f, 3.211777f,  // m, b (linear segment)
        16.395191f, 128.363626f, 5.345433f,
        38.414635f,  // a1, b1, c1, d1 (first rational segment)
        1257.147271f, -1252.056059f, 379.613560f,
        -378.115976f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 5.78°C (key: 5)
    {
        0.118854f, 3.221712f,  // m, b (linear segment)
        510.794524f, 4147.718053f, 167.121531f,
        1235.569720f,  // a1, b1, c1, d1 (first rational segment)
        2461.131197f, -2454.069820f, 742.268667f,
        -740.201672f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 10.64°C (key: 10)
    {
        0.116679f, 3.228096f,  // m, b (linear segment)
        4.902604f, 39.346060f, 1.602605f,
        11.689570f,  // a1, b1, c1, d1 (first rational segment)
        1195.141551f, -1192.318620f, 359.914069f,
        -359.086078f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 15.55°C (key: 15)
    {
        0.114185f, 3.232650f,  // m, b (linear segment)
        53.301731f, 494.341291f, 17.390648f,
        147.397127f,  // a1, b1, c1, d1 (first rational segment)
        3148.601582f, -3139.694761f, 947.559853f,
        -944.961920f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 20.65°C (key: 20)
    {
        0.114688f, 3.233887f,  // m, b (linear segment)
        62.865854f, 711.447068f, 20.495367f,
        213.158188f,  // a1, b1, c1, d1 (first rational segment)
        1180.804882f, -1178.074609f, 355.167808f,
        -354.373464f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 25.42°C (key: 25)
    {
        0.117951f, 3.235429f,  // m, b (linear segment)
        89.871275f, 1253.014022f, 29.329382f,
        376.569165f,  // a1, b1, c1, d1 (first rational segment)
        1131.880318f, -1129.339379f, 340.039336f,
        -339.304723f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 31.41°C (key: 30)
    {
        0.117363f, 3.238875f,  // m, b (linear segment)
        88.813605f, 1434.949559f, 29.026877f,
        431.654409f,  // a1, b1, c1, d1 (first rational segment)
        2953.178047f, -2947.773461f, 886.333650f,
        -884.769279f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 35.41°C (key: 35)
    {
        0.123731f, 3.236223f,  // m, b (linear segment)
        129.239103f, 2182.616715f, 42.262528f,
        657.226142f,  // a1, b1, c1, d1 (first rational segment)
        4774.132278f, -4767.725320f, 1431.719239f,
        -1429.869351f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 40.39°C (key: 40)
    {
        0.123437f, 3.237152f,  // m, b (linear segment)
        203.753833f, 3441.209337f, 66.623422f,
        1035.896296f,  // a1, b1, c1, d1 (first rational segment)
        1068.509706f, -1066.951782f, 320.376374f,
        -319.926907f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 45.29°C (key: 45)
    {
        0.124998f, 3.235772f,  // m, b (linear segment)
        1819.150259f, 31026.915232f, 595.177551f,
        9343.581417f,  // a1, b1, c1, d1 (first rational segment)
        41239.010522f, -41183.173619f, 12365.128437f,
        -12349.005616f  // a3, b3, c3, d3 (third rational segment)
    }};

// Charge OCV curve parameters for each temperature
static const float BATTERY_OCV_CHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS][10] = {
    // Temperature: 2.32°C (key: 0)
    {
        0.133654f, 3.292145f,  // m, b (linear segment)
        2424.212366f, 87282.185143f, 753.227933f,
        26148.817273f,  // a1, b1, c1, d1 (first rational segment)
        -20885.884413f, 19421.324650f, -6263.752097f,
        5862.671202f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 7.28°C (key: 5)
    {
        0.119964f, 3.293413f,  // m, b (linear segment)
        2732.271006f, 75783.249716f, 850.221080f,
        22690.534179f,  // a1, b1, c1, d1 (first rational segment)
        -4317.842520f, 4121.656010f, -1290.625974f,
        1236.917022f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 12.60°C (key: 10)
    {
        0.129891f, 3.273207f,  // m, b (linear segment)
        846.503340f, 15988.928725f, 265.726589f,
        4798.200588f,  // a1, b1, c1, d1 (first rational segment)
        -60068.019107f, 55820.453762f, -18158.693048f,
        16993.928616f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 17.51°C (key: 15)
    {
        0.115653f, 3.274031f,  // m, b (linear segment)
        64.044330f, 529.396718f, 20.054090f,
        157.624172f,  // a1, b1, c1, d1 (first rational segment)
        1058.938754f, -1022.297695f, 317.911706f,
        -307.869074f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 22.50°C (key: 20)
    {
        0.118277f, 3.272331f,  // m, b (linear segment)
        -26.011330f, -198.086479f, -8.180144f,
        -58.781818f,  // a1, b1, c1, d1 (first rational segment)
        983.725464f, -950.493228f, 295.209174f,
        -286.098635f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 27.46°C (key: 25)
    {
        0.108980f, 3.280729f,  // m, b (linear segment)
        13.408572f, 195.788230f, 4.191912f,
        58.632729f,  // a1, b1, c1, d1 (first rational segment)
        1421.480447f, -1387.510482f, 425.138078f,
        -415.819849f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 32.31°C (key: 30)
    {
        0.105879f, 3.276268f,  // m, b (linear segment)
        154.842986f, 1451.215812f, 48.865130f,
        431.470258f,  // a1, b1, c1, d1 (first rational segment)
        -3747.632139f, 3694.953159f, -1119.887101f,
        1105.424025f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 37.36°C (key: 35)
    {
        0.103781f, 3.277949f,  // m, b (linear segment)
        42.648170f, 582.113263f, 13.465663f,
        173.961241f,  // a1, b1, c1, d1 (first rational segment)
        1109.000316f, -1096.490080f, 331.110598f,
        -327.675032f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 42.34°C (key: 40)
    {
        0.105248f, 3.278675f,  // m, b (linear segment)
        86.330934f, 1157.715172f, 27.596520f,
        344.393006f,  // a1, b1, c1, d1 (first rational segment)
        1018.218867f, -1006.960134f, 303.810937f,
        -300.720120f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 47.35°C (key: 45)
    {
        0.096072f, 3.287899f,  // m, b (linear segment)
        19.109756f, 316.572653f, 6.001677f,
        94.659222f,  // a1, b1, c1, d1 (first rational segment)
        1023.376933f, -1010.269846f, 305.114363f,
        -301.461068f  // a3, b3, c3, d3 (third rational segment)
    }};

// Battery capacity data for each temperature
static const float BATTERY_CAPACITY[BATTERY_NUM_TEMP_POINTS][2] = {
    // Temperature: 0.80°C (key: 0)
    {297.56f, 315.21f},
    // Temperature: 5.78°C (key: 5)
    {325.07f, 336.55f},
    // Temperature: 10.64°C (key: 10)
    {343.23f, 366.44f},
    // Temperature: 15.55°C (key: 15)
    {355.86f, 378.79f},
    // Temperature: 20.65°C (key: 20)
    {362.69f, 394.38f},
    // Temperature: 25.42°C (key: 25)
    {358.49f, 352.85f},
    // Temperature: 31.41°C (key: 30)
    {361.17f, 379.75f},
    // Temperature: 35.41°C (key: 35)
    {357.76f, 366.75f},
    // Temperature: 40.39°C (key: 40)
    {358.06f, 383.63f},
    // Temperature: 45.29°C (key: 45)
    {354.19f, 350.75f}};
