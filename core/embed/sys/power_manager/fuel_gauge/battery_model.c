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
#ifdef KERNEL_MODE

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

// Calculate OCV for specific parameters and SOC
static float calc_ocv(const float* params, float soc) {
  if (soc < BATTERY_SOC_BREAKPOINT_1) {
    // First segment (rational function): (a1 + b1*x)/(c1 + d1*x)
    float a1 = params[2];
    float b1 = params[3];
    float c1 = params[4];
    float d1 = params[5];
    return (a1 + b1 * soc) / (c1 + d1 * soc);
  } else if (soc <= BATTERY_SOC_BREAKPOINT_2) {
    // Middle segment (linear function): m*x + b
    float m = params[0];
    float b = params[1];
    return m * soc + b;
  } else {
    // Third segment (rational function): (a3 + b3*x)/(c3 + d3*x)
    float a3 = params[6];
    float b3 = params[7];
    float c3 = params[8];
    float d3 = params[9];
    return (a3 + b3 * soc) / (c3 + d3 * soc);
  }
}

// Calculate OCV slope for specific parameters and SOC
static float calc_ocv_slope(const float* params, float soc) {
  if (soc < BATTERY_SOC_BREAKPOINT_1) {
    // First segment (rational function derivative)
    float a1 = params[2];
    float b1 = params[3];
    float c1 = params[4];
    float d1 = params[5];
    float denominator = c1 + d1 * soc;
    return (b1 * c1 - a1 * d1) / (denominator * denominator);
  } else if (soc <= BATTERY_SOC_BREAKPOINT_2) {
    // Middle segment (linear function derivative)
    float m = params[0];
    return m;
  } else {
    // Third segment (rational function derivative)
    float a3 = params[6];
    float b3 = params[7];
    float c3 = params[8];
    float d3 = params[9];
    float denominator = c3 + d3 * soc;
    return (b3 * c3 - a3 * d3) / (denominator * denominator);
  }
}

// Calculate SOC from OCV for specific parameters
static float calc_soc_from_ocv(const float* params, float ocv) {
  // Calculate breakpoint voltages
  float ocv_breakpoint_1 = calc_ocv(params, BATTERY_SOC_BREAKPOINT_1);
  float ocv_breakpoint_2 = calc_ocv(params, BATTERY_SOC_BREAKPOINT_2);

  // Extract parameters
  float m = params[0];
  float b = params[1];
  float a1 = params[2];
  float b1 = params[3];
  float c1 = params[4];
  float d1 = params[5];
  float a3 = params[6];
  float b3 = params[7];
  float c3 = params[8];
  float d3 = params[9];

  if (ocv < ocv_breakpoint_1) {
    // First segment (rational function inverse)
    return (a1 - c1 * ocv) / (d1 * ocv - b1);
  } else if (ocv <= ocv_breakpoint_2) {
    // Middle segment (linear function inverse)
    return (ocv - b) / m;
  } else {
    // Third segment (rational function inverse)
    return (a3 - c3 * ocv) / (d3 * ocv - b3);
  }
}

float battery_rint(float temperature) {
  // Calculate R_int using rational function: (a + b*t)/(c + d*t)
  float a = BATTERY_R_INT_PARAMS[0];
  float b = BATTERY_R_INT_PARAMS[1];
  float c = BATTERY_R_INT_PARAMS[2];
  float d = BATTERY_R_INT_PARAMS[3];

  return (a + b * temperature) / (c + d * temperature);
}

float battery_total_capacity(float temperature, bool discharging_mode) {
  // Select appropriate temperature array based on mode
  const float* temp_points =
      discharging_mode ? BATTERY_TEMP_POINTS_DISCHG : BATTERY_TEMP_POINTS_CHG;

  // Handle out-of-bounds temperatures
  if (temperature <= temp_points[0]) {
    return BATTERY_CAPACITY[0][discharging_mode ? 0 : 1];
  }

  if (temperature >= temp_points[BATTERY_NUM_TEMP_POINTS - 1]) {
    return BATTERY_CAPACITY[BATTERY_NUM_TEMP_POINTS - 1]
                           [discharging_mode ? 0 : 1];
  }

  // Find temperature bracket
  for (int i = 0; i < BATTERY_NUM_TEMP_POINTS - 1; i++) {
    if (temperature < temp_points[i + 1]) {
      return linear_interpolate(
          temperature, temp_points[i],
          BATTERY_CAPACITY[i][discharging_mode ? 0 : 1], temp_points[i + 1],
          BATTERY_CAPACITY[i + 1][discharging_mode ? 0 : 1]);
    }
  }

  // Should never reach here
  return BATTERY_CAPACITY[0][discharging_mode ? 0 : 1];
}

float battery_meas_to_ocv(float voltage_V, float current_mA,
                          float temperature) {
  // Convert mA to A by dividing by 1000
  float current_A = current_mA / 1000.0f;

  // Calculate OCV: V_OC = V_term + I * R_int
  return voltage_V + (current_A * battery_rint(temperature));
}

float battery_ocv(float soc, float temperature, bool discharging_mode) {
  // Clamp SOC to valid range
  soc = (soc < 0.0f) ? 0.0f : ((soc > 1.0f) ? 1.0f : soc);

  // Select appropriate temperature array based on mode
  const float* temp_points =
      discharging_mode ? BATTERY_TEMP_POINTS_DISCHG : BATTERY_TEMP_POINTS_CHG;

  // Handle out-of-bounds temperatures
  if (temperature <= temp_points[0]) {
    const float* params = discharging_mode ? BATTERY_OCV_DISCHARGE_PARAMS[0]
                                           : BATTERY_OCV_CHARGE_PARAMS[0];
    return calc_ocv(params, soc);
  }

  if (temperature >= temp_points[BATTERY_NUM_TEMP_POINTS - 1]) {
    const float* params =
        discharging_mode
            ? BATTERY_OCV_DISCHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS - 1]
            : BATTERY_OCV_CHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS - 1];
    return calc_ocv(params, soc);
  }

  // Find temperature bracket and interpolate
  for (int i = 0; i < BATTERY_NUM_TEMP_POINTS - 1; i++) {
    if (temperature < temp_points[i + 1]) {
      const float* params_low = discharging_mode
                                    ? BATTERY_OCV_DISCHARGE_PARAMS[i]
                                    : BATTERY_OCV_CHARGE_PARAMS[i];

      const float* params_high = discharging_mode
                                     ? BATTERY_OCV_DISCHARGE_PARAMS[i + 1]
                                     : BATTERY_OCV_CHARGE_PARAMS[i + 1];

      float ocv_low = calc_ocv(params_low, soc);
      float ocv_high = calc_ocv(params_high, soc);

      return linear_interpolate(temperature, temp_points[i], ocv_low,
                                temp_points[i + 1], ocv_high);
    }
  }

  // Should never reach here
  const float* params = discharging_mode ? BATTERY_OCV_DISCHARGE_PARAMS[0]
                                         : BATTERY_OCV_CHARGE_PARAMS[0];
  return calc_ocv(params, soc);
}

float battery_ocv_slope(float soc, float temperature, bool discharging_mode) {
  // Clamp SOC to valid range
  soc = (soc < 0.0f) ? 0.0f : ((soc > 1.0f) ? 1.0f : soc);

  // Select appropriate temperature array based on mode
  const float* temp_points =
      discharging_mode ? BATTERY_TEMP_POINTS_DISCHG : BATTERY_TEMP_POINTS_CHG;

  // Handle out-of-bounds temperatures
  if (temperature <= temp_points[0]) {
    const float* params = discharging_mode ? BATTERY_OCV_DISCHARGE_PARAMS[0]
                                           : BATTERY_OCV_CHARGE_PARAMS[0];
    return calc_ocv_slope(params, soc);
  }

  if (temperature >= temp_points[BATTERY_NUM_TEMP_POINTS - 1]) {
    const float* params =
        discharging_mode
            ? BATTERY_OCV_DISCHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS - 1]
            : BATTERY_OCV_CHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS - 1];
    return calc_ocv_slope(params, soc);
  }

  // Find temperature bracket and interpolate
  for (int i = 0; i < BATTERY_NUM_TEMP_POINTS - 1; i++) {
    if (temperature < temp_points[i + 1]) {
      const float* params_low = discharging_mode
                                    ? BATTERY_OCV_DISCHARGE_PARAMS[i]
                                    : BATTERY_OCV_CHARGE_PARAMS[i];

      const float* params_high = discharging_mode
                                     ? BATTERY_OCV_DISCHARGE_PARAMS[i + 1]
                                     : BATTERY_OCV_CHARGE_PARAMS[i + 1];

      float slope_low = calc_ocv_slope(params_low, soc);
      float slope_high = calc_ocv_slope(params_high, soc);

      return linear_interpolate(temperature, temp_points[i], slope_low,
                                temp_points[i + 1], slope_high);
    }
  }

  // Should never reach here
  const float* params = discharging_mode ? BATTERY_OCV_DISCHARGE_PARAMS[0]
                                         : BATTERY_OCV_CHARGE_PARAMS[0];
  return calc_ocv_slope(params, soc);
}

float battery_soc(float ocv, float temperature, bool discharging_mode) {
  // Select appropriate temperature array based on mode
  const float* temp_points =
      discharging_mode ? BATTERY_TEMP_POINTS_DISCHG : BATTERY_TEMP_POINTS_CHG;

  // Handle out-of-bounds temperatures
  if (temperature <= temp_points[0]) {
    const float* params = discharging_mode ? BATTERY_OCV_DISCHARGE_PARAMS[0]
                                           : BATTERY_OCV_CHARGE_PARAMS[0];
    return calc_soc_from_ocv(params, ocv);
  }

  if (temperature >= temp_points[BATTERY_NUM_TEMP_POINTS - 1]) {
    const float* params =
        discharging_mode
            ? BATTERY_OCV_DISCHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS - 1]
            : BATTERY_OCV_CHARGE_PARAMS[BATTERY_NUM_TEMP_POINTS - 1];
    return calc_soc_from_ocv(params, ocv);
  }

  // Find temperature bracket and interpolate
  for (int i = 0; i < BATTERY_NUM_TEMP_POINTS - 1; i++) {
    if (temperature < temp_points[i + 1]) {
      const float* params_low = discharging_mode
                                    ? BATTERY_OCV_DISCHARGE_PARAMS[i]
                                    : BATTERY_OCV_CHARGE_PARAMS[i];

      const float* params_high = discharging_mode
                                     ? BATTERY_OCV_DISCHARGE_PARAMS[i + 1]
                                     : BATTERY_OCV_CHARGE_PARAMS[i + 1];

      float soc_low = calc_soc_from_ocv(params_low, ocv);
      float soc_high = calc_soc_from_ocv(params_high, ocv);

      return linear_interpolate(temperature, temp_points[i], soc_low,
                                temp_points[i + 1], soc_high);
    }
  }

  // Should never reach here
  const float* params = discharging_mode ? BATTERY_OCV_DISCHARGE_PARAMS[0]
                                         : BATTERY_OCV_CHARGE_PARAMS[0];
  return calc_soc_from_ocv(params, ocv);
}

#endif
