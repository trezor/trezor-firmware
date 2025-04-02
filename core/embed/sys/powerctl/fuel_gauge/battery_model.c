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

/*
 * Battery Model Implementation
 * Auto-generated from battery characterization data
 */

#include "battery_model.h"
#include <math.h>

// Helper function for linear interpolation
static float linear_interpolate(float x, float x1, float y1, float x2,
                                float y2) {
  // Prevent division by zero
  if (fabsf(x2 - x1) < 1e-6f) {
    return (y1 + y2) / 2.0f;  // Return average if x values are too close
  }
  return y1 + (x - x1) * (y2 - y1) / (x2 - x1);
}

// Helper function to calculate OCV for specific parameters and SOC
static float calc_ocv(const ocv_params_t* params, float soc) {
  if (soc < BATTERY_SOC_BREAKPOINT_1) {
    // First segment (rational)
    return (params->a1 + params->b1 * soc) / (params->c1 + params->d1 * soc);
  } else if (soc <= BATTERY_SOC_BREAKPOINT_2) {
    // Middle segment (linear)
    return params->m * soc + params->b;
  } else {
    // Third segment (rational)
    return (params->a3 + params->b3 * soc) / (params->c3 + params->d3 * soc);
  }
}

// Helper function to calculate OCV slope for specific parameters and SOC
static float calc_ocv_slope(const ocv_params_t* params, float soc) {
  if (soc < BATTERY_SOC_BREAKPOINT_1) {
    // First segment (rational)
    float denominator = params->c1 + params->d1 * soc;
    return (params->b1 * params->c1 - params->a1 * params->d1) /
           (denominator * denominator);
  } else if (soc <= BATTERY_SOC_BREAKPOINT_2) {
    // Middle segment (linear)
    return params->m;
  } else {
    // Third segment (rational)
    float denominator = params->c3 + params->d3 * soc;
    return (params->b3 * params->c3 - params->a3 * params->d3) /
           (denominator * denominator);
  }
}

// Helper function to calculate SOC from OCV for specific parameters
static float calc_soc_from_ocv(const ocv_params_t* params, float ocv) {
  // Calculate breakpoint voltages
  float ocv_breakpoint_1 = calc_ocv(params, BATTERY_SOC_BREAKPOINT_1);
  float ocv_breakpoint_2 = calc_ocv(params, BATTERY_SOC_BREAKPOINT_2);

  if (ocv < ocv_breakpoint_1) {
    // First segment (rational)
    return (params->a1 - params->c1 * ocv) / (params->d1 * ocv - params->b1);
  } else if (ocv <= ocv_breakpoint_2) {
    // Middle segment (linear)
    return (ocv - params->b) / params->m;
  } else {
    // Third segment (rational)
    return (params->a3 - params->c3 * ocv) / (params->d3 * ocv - params->b3);
  }
}

float battery_rint(float temperature) {
  // Calculate R_int using rational function: (a + b*t)/(c + d*t)
  float a = BATTERY_R_INT_PARAMS.a;
  float b = BATTERY_R_INT_PARAMS.b;
  float c = BATTERY_R_INT_PARAMS.c;
  float d = BATTERY_R_INT_PARAMS.d;

  return (a + b * temperature) / (c + d * temperature);
}

float battery_total_capacity(float temperature) {
  // Handle out-of-bounds temperatures
  if (temperature <= BATTERY_TEMP_POINTS[0]) {
    return BATTERY_OCV_PARAMS[0].total_capacity;
  }

  if (temperature >= BATTERY_TEMP_POINTS[BATTERY_NUM_TEMPERATURE_POINTS - 1]) {
    return BATTERY_OCV_PARAMS[BATTERY_NUM_TEMPERATURE_POINTS - 1]
        .total_capacity;
  }

  // Find temperature bracket
  for (int i = 0; i < BATTERY_NUM_TEMPERATURE_POINTS - 1; i++) {
    if (temperature < BATTERY_TEMP_POINTS[i + 1]) {
      return linear_interpolate(temperature, BATTERY_TEMP_POINTS[i],
                                BATTERY_OCV_PARAMS[i].total_capacity,
                                BATTERY_TEMP_POINTS[i + 1],
                                BATTERY_OCV_PARAMS[i + 1].total_capacity);
    }
  }

  // Should never reach here
  return BATTERY_OCV_PARAMS[0].total_capacity;
}

float battery_meas_to_ocv(float voltage_V, float current_mA,
                          float temperature) {
  // Convert to mA to A by dividing by 1000
  float current_A = current_mA / 1000.0f;

  // Calculate OCV: V_OC = V_term + I * R_int
  return voltage_V + (current_A * battery_rint(temperature));
}

float battery_ocv(float soc, float temperature) {
  // Clamp SOC to valid range
  soc = (soc < 0.0f) ? 0.0f : ((soc > 1.0f) ? 1.0f : soc);

  // Handle out-of-bounds temperatures
  if (temperature <= BATTERY_TEMP_POINTS[0]) {
    return calc_ocv(&BATTERY_OCV_PARAMS[0], soc);
  }

  if (temperature >= BATTERY_TEMP_POINTS[BATTERY_NUM_TEMPERATURE_POINTS - 1]) {
    return calc_ocv(&BATTERY_OCV_PARAMS[BATTERY_NUM_TEMPERATURE_POINTS - 1],
                    soc);
  }

  // Find temperature bracket and interpolate
  for (int i = 0; i < BATTERY_NUM_TEMPERATURE_POINTS - 1; i++) {
    if (temperature < BATTERY_TEMP_POINTS[i + 1]) {
      float ocv_low = calc_ocv(&BATTERY_OCV_PARAMS[i], soc);
      float ocv_high = calc_ocv(&BATTERY_OCV_PARAMS[i + 1], soc);

      return linear_interpolate(temperature, BATTERY_TEMP_POINTS[i], ocv_low,
                                BATTERY_TEMP_POINTS[i + 1], ocv_high);
    }
  }

  // Should never reach here
  return calc_ocv(&BATTERY_OCV_PARAMS[0], soc);
}

float battery_ocv_slope(float soc, float temperature) {
  // Clamp SOC to valid range
  soc = (soc < 0.0f) ? 0.0f : ((soc > 1.0f) ? 1.0f : soc);

  // Handle out-of-bounds temperatures
  if (temperature <= BATTERY_TEMP_POINTS[0]) {
    return calc_ocv_slope(&BATTERY_OCV_PARAMS[0], soc);
  }

  if (temperature >= BATTERY_TEMP_POINTS[BATTERY_NUM_TEMPERATURE_POINTS - 1]) {
    return calc_ocv_slope(
        &BATTERY_OCV_PARAMS[BATTERY_NUM_TEMPERATURE_POINTS - 1], soc);
  }

  // Find temperature bracket and interpolate
  for (int i = 0; i < BATTERY_NUM_TEMPERATURE_POINTS - 1; i++) {
    if (temperature < BATTERY_TEMP_POINTS[i + 1]) {
      float slope_low = calc_ocv_slope(&BATTERY_OCV_PARAMS[i], soc);
      float slope_high = calc_ocv_slope(&BATTERY_OCV_PARAMS[i + 1], soc);

      return linear_interpolate(temperature, BATTERY_TEMP_POINTS[i], slope_low,
                                BATTERY_TEMP_POINTS[i + 1], slope_high);
    }
  }

  // Should never reach here
  return calc_ocv_slope(&BATTERY_OCV_PARAMS[0], soc);
}

float battery_soc(float ocv, float temperature) {
  // Handle out-of-bounds temperatures
  if (temperature <= BATTERY_TEMP_POINTS[0]) {
    return calc_soc_from_ocv(&BATTERY_OCV_PARAMS[0], ocv);
  }

  if (temperature >= BATTERY_TEMP_POINTS[BATTERY_NUM_TEMPERATURE_POINTS - 1]) {
    return calc_soc_from_ocv(
        &BATTERY_OCV_PARAMS[BATTERY_NUM_TEMPERATURE_POINTS - 1], ocv);
  }

  // Find temperature bracket and interpolate
  for (int i = 0; i < BATTERY_NUM_TEMPERATURE_POINTS - 1; i++) {
    if (temperature < BATTERY_TEMP_POINTS[i + 1]) {
      float soc_low = calc_soc_from_ocv(&BATTERY_OCV_PARAMS[i], ocv);
      float soc_high = calc_soc_from_ocv(&BATTERY_OCV_PARAMS[i + 1], ocv);

      return linear_interpolate(temperature, BATTERY_TEMP_POINTS[i], soc_low,
                                BATTERY_TEMP_POINTS[i + 1], soc_high);
    }
  }

  // Should never reach here
  return calc_soc_from_ocv(&BATTERY_OCV_PARAMS[0], ocv);
}
