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
#define BATTERY_HCF343837NCZ_NUM_TEMP_POINTS 10

// SOC breakpoints for piecewise functions
#define BATTERY_HCF343837NCZ_SOC_BREAKPOINT_1 0.25f
#define BATTERY_HCF343837NCZ_SOC_BREAKPOINT_2 0.8f

// Temperature points arrays (in Celsius)
// Discharge temperatures
static const float BATTERY_HCF343837NCZ_TEMP_POINTS_DISCHG
    [BATTERY_HCF343837NCZ_NUM_TEMP_POINTS] = {1.04f,  5.87f,  10.91f, 15.71f,
                                              20.49f, 25.35f, 30.29f, 35.22f,
                                              40.17f, 45.10f};

// Charge temperatures
static const float
    BATTERY_HCF343837NCZ_TEMP_POINTS_CHG[BATTERY_HCF343837NCZ_NUM_TEMP_POINTS] =
        {2.57f,  7.44f,  13.03f, 17.81f, 22.59f,
         27.44f, 32.36f, 37.29f, 42.21f, 47.06f};

// Internal resistance curve parameters (rational function parameters
// a+b*t)/(c+d*t)
static const float BATTERY_HCF343837NCZ_R_INT_PARAMS[4] = {
    // a, b, c, d for rational function (a + b*t)/(c + d*t)
    1.135695f, 0.031070f, 1.422311f, 0.096649f};

// Discharge OCV curve parameters for each temperature
static const float BATTERY_HCF343837NCZ_OCV_DISCHARGE_PARAMS
    [BATTERY_HCF343837NCZ_NUM_TEMP_POINTS][10] = {
        // Temperature: 1.04°C (key: 0)
        {
            0.125765f, 3.209826f,  // m, b (linear segment)
            -59905.067703f, -611483.353169f, -19591.357538f,
            -184218.136293f,  // a1, b1, c1, d1 (first rational segment)
            1137250.998411f, -1132728.591286f, 343637.826372f,
            -342297.459410f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 5.87°C (key: 5)
        {
            0.114258f, 3.221604f,  // m, b (linear segment)
            -3033.454676f, -24661.299084f, -993.614579f,
            -7346.530414f,  // a1, b1, c1, d1 (first rational segment)
            -7101.744797f, 10421.640424f, -2128.664044f,
            3127.010194f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 10.91°C (key: 10)
        {
            0.113504f, 3.228052f,  // m, b (linear segment)
            -259.482794f, -1633.635362f, -84.783174f,
            -481.265046f,  // a1, b1, c1, d1 (first rational segment)
            4810.019967f, -6205.062721f, 1444.492114f,
            -1863.628440f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 15.71°C (key: 15)
        {
            0.117048f, 3.230906f,  // m, b (linear segment)
            -622.734206f, -3746.528313f, -202.523747f,
            -1103.139479f,  // a1, b1, c1, d1 (first rational segment)
            3838.817792f, -4888.129357f, 1152.614595f,
            -1467.721448f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 20.49°C (key: 20)
        {
            0.121536f, 3.232378f,  // m, b (linear segment)
            -341.964049f, -2334.475028f, -110.768017f,
            -691.650977f,  // a1, b1, c1, d1 (first rational segment)
            616.115591f, -785.848169f, 184.855292f,
            -235.785492f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 25.35°C (key: 25)
        {
            0.126216f, 3.231969f,  // m, b (linear segment)
            -688.418324f, -5675.969832f, -222.638659f,
            -1692.433742f,  // a1, b1, c1, d1 (first rational segment)
            -1414.651014f, 1413.832496f, -424.456797f,
            424.214134f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 30.29°C (key: 30)
        {
            0.130799f, 3.231530f,  // m, b (linear segment)
            105.798537f, 1001.824559f, 34.225220f,
            299.654993f,  // a1, b1, c1, d1 (first rational segment)
            3388.131418f, -4233.444575f, 1015.953881f,
            -1269.426881f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 35.22°C (key: 35)
        {
            0.133811f, 3.231709f,  // m, b (linear segment)
            -958.918317f, -9796.454446f, -310.426022f,
            -2933.319675f,  // a1, b1, c1, d1 (first rational segment)
            9530.236041f, -11909.411769f, 2856.628923f,
            -3569.772818f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 40.17°C (key: 40)
        {
            0.135919f, 3.231701f,  // m, b (linear segment)
            -383.413353f, -4211.609011f, -124.227922f,
            -1262.373069f,  // a1, b1, c1, d1 (first rational segment)
            -104.706961f, 130.851778f, -31.376477f,
            39.211040f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 45.10°C (key: 45)
        {
            0.136175f, 3.232311f,  // m, b (linear segment)
            -850.336236f, -9419.762697f, -275.568895f,
            -2822.928705f,  // a1, b1, c1, d1 (first rational segment)
            -3775.148863f, 4717.956948f, -1131.385831f,
            1413.939246f  // a3, b3, c3, d3 (third rational segment)
        }};

// Charge OCV curve parameters for each temperature
static const float BATTERY_HCF343837NCZ_OCV_CHARGE_PARAMS
    [BATTERY_HCF343837NCZ_NUM_TEMP_POINTS][10] = {
        // Temperature: 2.57°C (key: 0)
        {
            0.100607f, 3.310842f,  // m, b (linear segment)
            -21.437245f, -2134.989999f, -6.617578f,
            -639.220098f,  // a1, b1, c1, d1 (first rational segment)
            -1362.827864f, 1272.428077f, -410.453028f,
            385.945933f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 7.44°C (key: 5)
        {
            0.104629f, 3.299123f,  // m, b (linear segment)
            -196.749871f, -5958.392132f, -60.907052f,
            -1784.889811f,  // a1, b1, c1, d1 (first rational segment)
            -1777.918025f, 1683.869008f, -534.953430f,
            509.496945f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 13.03°C (key: 10)
        {
            0.108389f, 3.283266f,  // m, b (linear segment)
            13.622801f, 200.944317f, 4.246426f,
            60.176684f,  // a1, b1, c1, d1 (first rational segment)
            -1226.355432f, 1120.994967f, -374.342315f,
            345.686898f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 17.81°C (key: 15)
        {
            0.105214f, 3.280009f,  // m, b (linear segment)
            177.367293f, 998.631645f, 55.299024f,
            295.422017f,  // a1, b1, c1, d1 (first rational segment)
            -1365.514862f, 1287.588877f, -413.965664f,
            392.819065f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 22.59°C (key: 20)
        {
            0.104454f, 3.277587f,  // m, b (linear segment)
            74.568726f, 262.251577f, 23.293839f,
            76.490872f,  // a1, b1, c1, d1 (first rational segment)
            -2086.478781f, 1996.825136f, -630.261291f,
            605.962304f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 27.44°C (key: 25)
        {
            0.100807f, 3.275997f,  // m, b (linear segment)
            16.228097f, 64.480062f, 5.093477f,
            18.821688f,  // a1, b1, c1, d1 (first rational segment)
            -1688.976529f, 1642.785513f, -508.239556f,
            495.744767f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 32.36°C (key: 30)
        {
            0.099490f, 3.274824f,  // m, b (linear segment)
            85.961072f, 521.968104f, 27.144697f,
            153.812762f,  // a1, b1, c1, d1 (first rational segment)
            -1683.099906f, 1646.528598f, -505.831305f,
            495.947568f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 37.29°C (key: 35)
        {
            0.099327f, 3.273021f,  // m, b (linear segment)
            -326.984574f, -2718.036483f, -103.864285f,
            -805.329651f,  // a1, b1, c1, d1 (first rational segment)
            -1614.175091f, 1589.918955f, -484.243885f,
            477.697944f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 42.21°C (key: 40)
        {
            0.099425f, 3.272042f,  // m, b (linear segment)
            -356.487016f, -3426.536567f, -113.613211f,
            -1017.380204f,  // a1, b1, c1, d1 (first rational segment)
            -628.804522f, 620.898234f, -188.525975f,
            186.394946f  // a3, b3, c3, d3 (third rational segment)
        },
        // Temperature: 47.06°C (key: 45)
        {
            0.106433f, 3.267737f,  // m, b (linear segment)
            -231.164659f, -4375.066517f, -75.037588f,
            -1308.583546f,  // a1, b1, c1, d1 (first rational segment)
            497.382497f, -490.468395f, 148.991945f,
            -147.091621f  // a3, b3, c3, d3 (third rational segment)
        }};

// Battery capacity data for each temperature
static const float
    BATTERY_HCF343837NCZ_CAPACITY[BATTERY_HCF343837NCZ_NUM_TEMP_POINTS][2] = {
        // Temperature: 1.04°C (key: 0)
        {280.77f, 273.20f},
        // Temperature: 5.87°C (key: 5)
        {309.78f, 304.36f},
        // Temperature: 10.91°C (key: 10)
        {326.08f, 331.68f},
        // Temperature: 15.71°C (key: 15)
        {338.50f, 348.60f},
        // Temperature: 20.49°C (key: 20)
        {347.18f, 361.51f},
        // Temperature: 25.35°C (key: 25)
        {352.30f, 368.37f},
        // Temperature: 30.29°C (key: 30)
        {357.11f, 374.72f},
        // Temperature: 35.22°C (key: 35)
        {360.50f, 378.76f},
        // Temperature: 40.17°C (key: 40)
        {364.10f, 382.45f},
        // Temperature: 45.10°C (key: 45)
        {367.43f, 390.15f}};
