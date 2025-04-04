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
 * Battery Model Lookup Tables
 * Auto-generated from battery characterization data
 */

#ifndef BATTERY_MODEL_H
#define BATTERY_MODEL_H

#include <stdbool.h>
#include <stdint.h>

// Configuration
#define BATTERY_NUM_TEMPERATURE_POINTS 7

// Battery model parameters
// SOC breakpoints for piecewise functions
#define BATTERY_SOC_BREAKPOINT_1 0.25f
#define BATTERY_SOC_BREAKPOINT_2 0.8f

// Temperature points array (in Celsius)
static const float BATTERY_TEMP_POINTS[BATTERY_NUM_TEMPERATURE_POINTS] = {
    -9.02f, -2.30f, 4.57f, 13.04f, 17.51f, 27.17f, 37.03f};

// Internal resistance curve parameters (rational function parameters
// a+b*t)/(c+d*t)
typedef struct {
  float a;
  float b;
  float c;
  float d;
} rint_params_t;

// OCV curve parameters for one temperature
typedef struct {
  // m, b (linear segment)
  float m;
  float b;
  // a1, b1, c1, d1 (first rational segment)
  float a1;
  float b1;
  float c1;
  float d1;
  // a3, b3, c3, d3 (third rational segment)
  float a3;
  float b3;
  float c3;
  float d3;
  // Total capacity at this temperature
  float total_capacity;
} ocv_params_t;

// Internal resistance curve parameters
static const rint_params_t BATTERY_R_INT_PARAMS = {
    .a = -19.914535f, .b = -0.111745f, .c = -17.424596f, .d = -0.664215f};

// OCV curve parameters for each temperature
static const ocv_params_t BATTERY_OCV_PARAMS[BATTERY_NUM_TEMPERATURE_POINTS] = {
    // Temperature: -9.02°C
    {.m = 0.141258f,
     .b = 3.190412f,
     .a1 = 23.713014f,
     .b1 = -30252.014861f,
     .c1 = 6.822542f,
     .d1 = -9376.243132f,
     .a3 = 870.834698f,
     .b3 = -770.217859f,
     .c3 = 268.533412f,
     .d3 = -239.304307f,
     .total_capacity = 12.36f},
    // Temperature: -2.30°C
    {.m = 0.147703f,
     .b = 3.174024f,
     .a1 = -25.237388f,
     .b1 = 24.466968f,
     .c1 = -7.971240f,
     .d1 = 8.065657f,
     .a3 = 1301.931501f,
     .b3 = -1261.841781f,
     .c3 = 398.187039f,
     .d3 = -386.691292f,
     .total_capacity = 66.17f},
    // Temperature: 4.57°C
    {.m = 0.140456f,
     .b = 3.195639f,
     .a1 = 113.417606f,
     .b1 = -92.151449f,
     .c1 = 36.245689f,
     .d1 = -33.083460f,
     .a3 = -3814.963656f,
     .b3 = 3754.803540f,
     .c3 = -1156.843875f,
     .d3 = 1139.555473f,
     .total_capacity = 151.01f},
    // Temperature: 13.04°C
    {.m = 0.137867f,
     .b = 3.231006f,
     .a1 = -149.212187f,
     .b1 = -399.546027f,
     .c1 = -47.886320f,
     .d1 = -113.585027f,
     .a3 = 1094.282489f,
     .b3 = -1087.594536f,
     .c3 = 327.867939f,
     .d3 = -325.957816f,
     .total_capacity = 245.24f},
    // Temperature: 17.51°C
    {.m = 0.128165f,
     .b = 3.231001f,
     .a1 = 10.761174f,
     .b1 = 75.344670f,
     .c1 = 3.480805f,
     .d1 = 22.358681f,
     .a3 = 1120.933145f,
     .b3 = -1116.536363f,
     .c3 = 336.565790f,
     .d3 = -335.323329f,
     .total_capacity = 296.29f},
    // Temperature: 27.17°C
    {.m = 0.111403f,
     .b = 3.245045f,
     .a1 = 167.692298f,
     .b1 = 1476.743067f,
     .c1 = 54.549004f,
     .d1 = 437.954443f,
     .a3 = 1106.075910f,
     .b3 = -1100.920128f,
     .c3 = 332.031558f,
     .d3 = -330.558171f,
     .total_capacity = 331.01f},
    // Temperature: 37.03°C
    {.m = 0.113740f,
     .b = 3.244924f,
     .a1 = -58.731545f,
     .b1 = -483.282822f,
     .c1 = -18.980003f,
     .d1 = -143.490387f,
     .a3 = 1073.157307f,
     .b3 = -1067.171796f,
     .c3 = 322.017999f,
     .d3 = -320.303753f,
     .total_capacity = 344.33f}};

// Function declarations

/**
 * Calculate internal resistance at the given temperature
 * @param temperature Battery temperature in Celsius
 * @return Internal resistance in ohms
 */
float battery_rint(float temperature);

/**
 * Get battery total capacity at the given temperature
 * @param temperature Battery temperature in Celsius
 * @return Total capacity in mAh
 */
float battery_total_capacity(float temperature);

/**
 * Calculate OCV from measured voltage and current
 * @param voltage_V Measured battery voltage in volts
 * @param current_mA Measured battery current in mA (positive for discharge)
 * @param temperature Battery temperature in Celsius
 * @return Open circuit voltage (OCV) in volts
 */
float battery_meas_to_ocv(float voltage_V, float current_mA, float temperature);

/**
 * Get OCV for given SOC and temperature
 * @param soc State of charge (0.0 to 1.0)
 * @param temperature Battery temperature in Celsius
 * @return Open circuit voltage in volts
 */
float battery_ocv(float soc, float temperature);

/**
 * Get the slope of the OCV curve at a given SOC and temperature
 * @param soc State of charge (0.0 to 1.0)
 * @param temperature Battery temperature in Celsius
 * @return Slope of OCV curve (dOCV/dSOC) in volts
 */
float battery_ocv_slope(float soc, float temperature);

/**
 * Get SOC for given OCV and temperature
 * @param ocv Open circuit voltage in volts
 * @param temperature Battery temperature in Celsius
 * @return State of charge (0.0 to 1.0)
 */
float battery_soc(float ocv, float temperature);

#endif  // BATTERY_MODEL_H
