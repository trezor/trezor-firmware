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
#define BATTERY_NUM_TEMP_POINTS 8

// SOC breakpoints for piecewise functions
#define BATTERY_SOC_BREAKPOINT_1 0.25f
#define BATTERY_SOC_BREAKPOINT_2 0.8f

// Temperature points arrays (in Celsius)
// Discharge temperatures
static const float BATTERY_TEMP_POINTS_DISCHG[BATTERY_NUM_TEMP_POINTS] = {
    5.78f, 10.64f, 15.55f, 20.65f, 25.46f, 31.41f, 35.41f, 40.39f};

// Charge temperatures
static const float BATTERY_TEMP_POINTS_CHG[BATTERY_NUM_TEMP_POINTS] = {
    7.28f, 12.60f, 17.51f, 22.50f, 27.54f, 32.31f, 37.36f, 42.34f};

// Internal resistance curve parameters (rational function parameters
// a+b*t)/(c+d*t)
static const float BATTERY_R_INT_PARAMS[4] = {
    // a, b, c, d for rational function (a + b*t)/(c + d*t)
    2.454393f, 0.067324f, 2.343462f, 0.253930f};

// Discharge OCV curve parameters for each temperature
static const float BATTERY_OCV_DISCHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS][10] = {
    // Temperature: 5.78°C (key: 5)
    {
        0.118793f, 3.223549f,  // m, b (linear segment)
        -28.710519f, -233.020734f, -9.387607f,
        -69.377452f,  // a1, b1, c1, d1 (first rational segment)
        1186.538824f, -1183.168718f, 357.662778f,
        -356.677000f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 10.64°C (key: 10)
    {
        0.116677f, 3.228169f,  // m, b (linear segment)
        38.712861f, 310.693560f, 12.654472f,
        92.304022f,  // a1, b1, c1, d1 (first rational segment)
        1191.497665f, -1188.685202f, 358.808999f,
        -357.984106f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 15.55°C (key: 15)
    {
        0.114203f, 3.232147f,  // m, b (linear segment)
        46.343674f, 429.794749f, 15.123043f,
        128.169726f,  // a1, b1, c1, d1 (first rational segment)
        2376.881452f, -2370.146392f, 715.418936f,
        -713.454126f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 20.65°C (key: 20)
    {
        0.114704f, 3.233252f,  // m, b (linear segment)
        134.655526f, 1523.391576f, 43.909469f,
        456.507698f,  // a1, b1, c1, d1 (first rational segment)
        1107.209215f, -1104.640469f, 333.093622f,
        -332.346061f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 25.46°C (key: 25)
    {
        0.117246f, 3.235164f,  // m, b (linear segment)
        98.176928f, 1423.543661f, 32.065495f,
        428.106598f,  // a1, b1, c1, d1 (first rational segment)
        2966.477437f, -2956.724203f, 891.503790f,
        -888.671853f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 31.41°C (key: 30)
    {
        0.117384f, 3.238390f,  // m, b (linear segment)
        85.864212f, 1387.277542f, 28.067560f,
        417.373016f,  // a1, b1, c1, d1 (first rational segment)
        1149.478486f, -1147.371472f, 345.039987f,
        -344.429990f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 35.41°C (key: 35)
    {
        0.123742f, 3.235846f,  // m, b (linear segment)
        142.926106f, 2413.781156f, 46.744426f,
        726.914288f,  // a1, b1, c1, d1 (first rational segment)
        4746.864260f, -4740.482325f, 1423.698973f,
        -1421.856011f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 40.39°C (key: 40)
    {
        0.123445f, 3.236911f,  // m, b (linear segment)
        123.143807f, 2079.888064f, 40.268920f,
        626.146547f,  // a1, b1, c1, d1 (first rational segment)
        4400.930811f, -4394.510401f, 1319.644484f,
        -1317.792008f  // a3, b3, c3, d3 (third rational segment)
    }};

// Charge OCV curve parameters for each temperature
static const float BATTERY_OCV_CHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS][10] = {
    // Temperature: 7.28°C (key: 5)
    {
        0.119977f, 3.292032f,  // m, b (linear segment)
        853.906052f, 23690.107718f, 265.829386f,
        7096.080219f,  // a1, b1, c1, d1 (first rational segment)
        -4674.103115f, 4463.128949f, -1397.627984f,
        1339.864213f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 12.60°C (key: 10)
    {
        0.129893f, 3.273841f,  // m, b (linear segment)
        5.758317f, 108.758491f, 1.807241f,
        32.631657f,  // a1, b1, c1, d1 (first rational segment)
        1901.784554f, -1766.844686f, 574.822406f,
        -537.820435f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 17.51°C (key: 15)
    {
        0.115642f, 3.275607f,  // m, b (linear segment)
        37.820015f, 312.545982f, 11.836739f,
        93.014230f,  // a1, b1, c1, d1 (first rational segment)
        1114.586708f, -1075.733214f, 334.472803f,
        -323.824737f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 22.50°C (key: 20)
    {
        0.118272f, 3.274047f,  // m, b (linear segment)
        22.731575f, 173.069914f, 7.144899f,
        51.331716f,  // a1, b1, c1, d1 (first rational segment)
        1152.334851f, -1113.108848f, 345.641805f,
        -334.889218f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 27.54°C (key: 25)
    {
        0.111078f, 3.279982f,  // m, b (linear segment)
        -6.914910f, -92.593412f, -2.171610f,
        -27.668490f,  // a1, b1, c1, d1 (first rational segment)
        1252.901718f, -1213.409067f, 375.520632f,
        -364.700745f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 32.31°C (key: 30)
    {
        0.105869f, 3.277491f,  // m, b (linear segment)
        85.748575f, 803.500844f, 27.050103f,
        238.806153f,  // a1, b1, c1, d1 (first rational segment)
        639.263868f, -630.230568f, 190.960695f,
        -188.480780f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 37.36°C (key: 35)
    {
        0.103776f, 3.278805f,  // m, b (linear segment)
        -64.738447f, -883.533215f, -20.434949f,
        -263.970865f,  // a1, b1, c1, d1 (first rational segment)
        1133.040608f, -1120.212998f, 338.203820f,
        -334.681274f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 42.34°C (key: 40)
    {
        0.105245f, 3.279165f,  // m, b (linear segment)
        107.494439f, 1441.391508f, 34.356316f,
        428.716770f,  // a1, b1, c1, d1 (first rational segment)
        943.609378f, -933.154526f, 281.509060f,
        -278.639013f  // a3, b3, c3, d3 (third rational segment)
    }};

// Battery capacity data for each temperature
static const float BATTERY_CAPACITY[BATTERY_NUM_TEMP_POINTS][2] = {
    // Temperature: 5.78°C (key: 5)
    {325.07f, 336.55f},
    // Temperature: 10.64°C (key: 10)
    {343.23f, 366.44f},
    // Temperature: 15.55°C (key: 15)
    {355.86f, 378.79f},
    // Temperature: 20.65°C (key: 20)
    {362.69f, 394.38f},
    // Temperature: 25.46°C (key: 25)
    {369.62f, 375.32f},
    // Temperature: 31.41°C (key: 30)
    {361.17f, 379.75f},
    // Temperature: 35.41°C (key: 35)
    {357.76f, 366.75f},
    // Temperature: 40.39°C (key: 40)
    {358.06f, 383.63f}};
