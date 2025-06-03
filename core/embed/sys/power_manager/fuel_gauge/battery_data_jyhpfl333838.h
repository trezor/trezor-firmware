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
    14.99f, 19.83f, 24.88f, 29.87f};

// Internal resistance curve parameters (rational function parameters
// (a+b*t)/(c+d*t)
static const float BATTERY_R_INT_PARAMS[4] = {
    // a, b, c, d for rational function (a + b*t)/(c + d*t)
    16.085563f, -0.125445f, 19.792552f, 0.145223f};

// Discharge OCV curve parameters for each temperature
static const float BATTERY_OCV_DISCHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS][10] = {
    // Temperature: 14.99°C
    {
        0.106732f, 3.237046f,  // m, b (linear segment)
        150.195726f, 1408.772874f, 49.011575f,
        419.677576f,  // a1, b1, c1, d1 (first rational segment)
        1095.896717f, -1094.237972f, 329.945276f,
        -329.470389f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 19.83°C
    {
        0.128675f, 3.229591f,  // m, b (linear segment)
        40.245534f, 455.485581f, 13.138466f,
        136.444634f,  // a1, b1, c1, d1 (first rational segment)
        1639.259211f, -1636.939286f, 492.018097f,
        -491.352439f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 24.88°C
    {
        0.121191f, 3.232382f,  // m, b (linear segment)
        -82.844039f, -1002.077813f, -27.091776f,
        -300.331893f,  // a1, b1, c1, d1 (first rational segment)
        1123.577420f, -1122.115068f, 337.570875f,
        -337.154857f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 29.87°C
    {
        0.124779f, 3.231043f,  // m, b (linear segment)
        -105.157412f, -1529.966103f, -34.445200f,
        -460.150974f,  // a1, b1, c1, d1 (first rational segment)
        2810.755069f, -2807.662591f, 844.042035f,
        -843.161340f  // a3, b3, c3, d3 (third rational segment)
    }};

// Charge OCV curve parameters for each temperature
static const float BATTERY_OCV_CHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS][10] = {
    // Temperature: 14.99°C
    {
        0.155811f, 3.250616f,  // m, b (linear segment)
        882.012695f, 40175.064826f, 303.995510f,
        12069.381036f,  // a1, b1, c1, d1 (first rational segment)
        -4395.474187f, 3903.326115f, -1345.816241f,
        1210.894940f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 19.83°C
    {
        0.150987f, 3.250656f,  // m, b (linear segment)
        1253.813370f, 53662.474550f, 433.721486f,
        16108.954614f,  // a1, b1, c1, d1 (first rational segment)
        -672.584219f, 615.456869f, -204.657772f,
        189.004166f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 24.88°C
    {
        0.137795f, 3.255241f,  // m, b (linear segment)
        11079.770525f, 467803.865900f, 3799.664030f,
        140476.474886f,  // a1, b1, c1, d1 (first rational segment)
        23060.170644f, -21499.043288f, 6996.033171f,
        -6568.182436f  // a3, b3, c3, d3 (third rational segment)
    },
    // Temperature: 29.87°C
    {
        0.133387f, 3.257527f,  // m, b (linear segment)
        -51.838664f, -2099.240917f, -17.726544f,
        -630.000601f,  // a1, b1, c1, d1 (first rational segment)
        1610.609673f, -1520.476008f, 486.934271f,
        -462.190000f  // a3, b3, c3, d3 (third rational segment)
    }};

// Battery capacity data for each temperature
static const float BATTERY_CAPACITY[BATTERY_NUM_TEMP_POINTS][2] = {
    // Temperature: 14.99°C
    {341.15f, 398.60f},
    // Temperature: 19.83°C
    {344.52f, 409.01f},
    // Temperature: 24.88°C
    {350.78f, 401.40f},
    // Temperature: 29.87°C
    {354.19f, 405.16f}};
