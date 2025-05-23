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
#define BATTERY_NUM_TEMP_POINTS 4

// SOC breakpoints for piecewise functions
#define BATTERY_SOC_BREAKPOINT_1 0.25f
#define BATTERY_SOC_BREAKPOINT_2 0.8f

// Temperature points array (in Celsius)
static const float BATTERY_TEMP_POINTS[BATTERY_NUM_TEMP_POINTS] = {
    0.46f, 10.05f, 25.03f, 29.80f};

// Internal resistance curve parameters (rational function parameters
// (a+b*t)/(c+d*t)
static const float BATTERY_R_INT_PARAMS[4] = {
    // a, b, c, d for rational function (a + b*t)/(c + d*t)
    314.561562f, 6.949454f, 329.002634f, 20.119285f};

// Discharge OCV curve parameters for each temperature
static const float BATTERY_OCV_DISCHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS][10] = {
    // Temperature: 0.46°C
    {
        0.130028f, 3.193222f,  // m, b (linear segment)
        325.823911f, 1943.605327f, 106.271504f,
        581.477397f,  // a1, b1, c1, d1 (first rational segment)
        -3083.838407f, 3072.517555f, -935.932995f,
        932.663443f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 10.05°C
    {
        0.124523f, 3.204479f,  // m, b (linear segment)
        50.263715f, 294.491126f, 16.431238f,
        87.428849f,  // a1, b1, c1, d1 (first rational segment)
        1157.754723f, -1154.042231f, 350.693046f,
        -349.642784f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 25.03°C
    {
        0.131226f, 3.228685f,  // m, b (linear segment)
        -2761.545706f, -35244.718985f, -903.249559f,
        -10580.169625f,  // a1, b1, c1, d1 (first rational segment)
        560.960239f, -560.104695f, 168.314326f,
        -168.068451f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 29.80°C
    {
        0.128900f, 3.224999f,  // m, b (linear segment)
        147.603009f, 2106.738218f, 48.371431f,
        634.565986f,  // a1, b1, c1, d1 (first rational segment)
        1088.145798f, -1086.632309f, 327.042181f,
        -326.609182f  // a3, b3, c3, d3 (third rational segment)
    }};

// Charge OCV curve parameters for each temperature
static const float BATTERY_OCV_CHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS][10] = {
    // Temperature: 0.46°C
    {
        0.189010f, 3.186844f,  // m, b (linear segment)
        429.481457f, 18113.325314f, 151.811299f,
        5524.684908f,  // a1, b1, c1, d1 (first rational segment)
        -153.670897f, 124.507975f, -48.860495f,
        40.830081f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 10.05°C
    {
        0.205185f, 3.279822f,  // m, b (linear segment)
        309.660606f, 16075.042838f, 108.161345f,
        4764.914681f,  // a1, b1, c1, d1 (first rational segment)
        -117.943000f, -1804.883579f, -150.332984f,
        -378.962265f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 25.03°C
    {
        0.171150f, 3.255314f,  // m, b (linear segment)
        21.579423f, 949.274458f, 7.473251f,
        284.103459f,  // a1, b1, c1, d1 (first rational segment)
        -2905.691117f, 2320.320088f, -903.787409f,
        743.029277f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 29.80°C
    {
        0.145942f, 3.256710f,  // m, b (linear segment)
        -150.766651f, -6156.646216f, -51.753537f,
        -1845.616021f,  // a1, b1, c1, d1 (first rational segment)
        1326.452225f, -1158.930117f, 407.411820f,
        -361.305515f  // a3, b3, c3, d3 (third rational segment)
    }};

// Battery capacity data for each temperature
static const float BATTERY_CAPACITY[BATTERY_NUM_TEMP_POINTS][2] = {
    // Temperature: 0.46°C
    {260.61f, 375.53f},
    // Temperature: 10.05°C
    {291.40f, 349.77f},
    // Temperature: 25.03°C
    {345.85f, 397.55f},
    // Temperature: 29.80°C
    {343.12f, 390.44f}};
