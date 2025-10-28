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

#include <math.h>

#include <util/unit_properties.h>

#include "battery_model.h"

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
static float calc_ocv(const battery_model_t* model, const float* params,
                      float soc) {
  if (soc < model->soc_breakpoint_1) {
    // First segment (rational function): (a1 + b1*x)/(c1 + d1*x)
    float a1 = params[2];
    float b1 = params[3];
    float c1 = params[4];
    float d1 = params[5];
    return (a1 + b1 * soc) / (c1 + d1 * soc);
  } else if (soc <= model->soc_breakpoint_2) {
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
static float calc_ocv_slope(const battery_model_t* model, const float* params,
                            float soc) {
  if (soc < model->soc_breakpoint_1) {
    // First segment (rational function derivative)
    float a1 = params[2];
    float b1 = params[3];
    float c1 = params[4];
    float d1 = params[5];
    float denominator = c1 + d1 * soc;
    return (b1 * c1 - a1 * d1) / (denominator * denominator);
  } else if (soc <= model->soc_breakpoint_2) {
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
static float calc_soc_from_ocv(const battery_model_t* model,
                               const float* params, float ocv) {
  // Calculate breakpoint voltages
  float ocv_breakpoint_1 = calc_ocv(model, params, model->soc_breakpoint_1);
  float ocv_breakpoint_2 = calc_ocv(model, params, model->soc_breakpoint_2);

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

float battery_rint(const battery_model_t* model, float temperature) {
  // Calculate R_int using rational function: (a + b*t)/(c + d*t)
  float a = model->r_int_params[0];
  float b = model->r_int_params[1];
  float c = model->r_int_params[2];
  float d = model->r_int_params[3];

  return (a + b * temperature) / (c + d * temperature);
}

float battery_total_capacity(const battery_model_t* model, float temperature,
                             bool discharging_mode) {
  // Select appropriate temperature array based on mode
  const float* temp_points = discharging_mode ? model->temp_points_discharge
                                              : model->temp_points_charge;

  // Handle out-of-bounds temperatures
  if (temperature <= temp_points[0]) {
    return model->capacity[0][discharging_mode ? 0 : 1];
  }

  if (temperature >= temp_points[model->num_temp_points - 1]) {
    return model
        ->capacity[model->num_temp_points - 1][discharging_mode ? 0 : 1];
  }

  // Find temperature bracket
  for (int i = 0; i < model->num_temp_points - 1; i++) {
    if (temperature < temp_points[i + 1]) {
      return linear_interpolate(
          temperature, temp_points[i],
          model->capacity[i][discharging_mode ? 0 : 1], temp_points[i + 1],
          model->capacity[i + 1][discharging_mode ? 0 : 1]);
    }
  }

  // Should never reach here
  return model->capacity[0][discharging_mode ? 0 : 1];
}

float battery_meas_to_ocv(const battery_model_t* model, float voltage_V,
                          float current_mA, float temperature) {
  // Convert mA to A by dividing by 1000
  float current_A = current_mA / 1000.0f;

  // Calculate OCV: V_OC = V_term + I * R_int
  return voltage_V + (current_A * battery_rint(model, temperature));
}

float battery_ocv(const battery_model_t* model, float soc, float temperature,
                  bool discharging_mode) {
  // Clamp SOC to valid range
  soc = (soc < 0.0f) ? 0.0f : ((soc > 1.0f) ? 1.0f : soc);

  // Select appropriate temperature array based on mode
  const float* temp_points = discharging_mode ? model->temp_points_discharge
                                              : model->temp_points_charge;

  // Handle out-of-bounds temperatures
  if (temperature <= temp_points[0]) {
    const float* params = discharging_mode ? model->ocv_discharge_params[0]
                                           : model->ocv_charge_params[0];
    return calc_ocv(model, params, soc);
  }

  if (temperature >= temp_points[model->num_temp_points - 1]) {
    const float* params =
        discharging_mode
            ? model->ocv_discharge_params[model->num_temp_points - 1]
            : model->ocv_charge_params[model->num_temp_points - 1];
    return calc_ocv(model, params, soc);
  }

  // Find temperature bracket and interpolate
  for (int i = 0; i < model->num_temp_points - 1; i++) {
    if (temperature < temp_points[i + 1]) {
      const float* params_low = discharging_mode
                                    ? model->ocv_discharge_params[i]
                                    : model->ocv_charge_params[i];

      const float* params_high = discharging_mode
                                     ? model->ocv_discharge_params[i + 1]
                                     : model->ocv_charge_params[i + 1];

      float ocv_low = calc_ocv(model, params_low, soc);
      float ocv_high = calc_ocv(model, params_high, soc);

      return linear_interpolate(temperature, temp_points[i], ocv_low,
                                temp_points[i + 1], ocv_high);
    }
  }

  // Should never reach here
  const float* params = discharging_mode ? model->ocv_discharge_params[0]
                                         : model->ocv_charge_params[0];
  return calc_ocv(model, params, soc);
}

float battery_ocv_slope(const battery_model_t* model, float soc,
                        float temperature, bool discharging_mode) {
  // Clamp SOC to valid range
  soc = (soc < 0.0f) ? 0.0f : ((soc > 1.0f) ? 1.0f : soc);

  // Select appropriate temperature array based on mode
  const float* temp_points = discharging_mode ? model->temp_points_discharge
                                              : model->temp_points_charge;

  // Handle out-of-bounds temperatures
  if (temperature <= temp_points[0]) {
    const float* params = discharging_mode ? model->ocv_discharge_params[0]
                                           : model->ocv_charge_params[0];
    return calc_ocv_slope(model, params, soc);
  }

  if (temperature >= temp_points[model->num_temp_points - 1]) {
    const float* params =
        discharging_mode
            ? model->ocv_discharge_params[model->num_temp_points - 1]
            : model->ocv_charge_params[model->num_temp_points - 1];
    return calc_ocv_slope(model, params, soc);
  }

  // Find temperature bracket and interpolate
  for (int i = 0; i < model->num_temp_points - 1; i++) {
    if (temperature < temp_points[i + 1]) {
      const float* params_low = discharging_mode
                                    ? model->ocv_discharge_params[i]
                                    : model->ocv_charge_params[i];

      const float* params_high = discharging_mode
                                     ? model->ocv_discharge_params[i + 1]
                                     : model->ocv_charge_params[i + 1];

      float slope_low = calc_ocv_slope(model, params_low, soc);
      float slope_high = calc_ocv_slope(model, params_high, soc);

      return linear_interpolate(temperature, temp_points[i], slope_low,
                                temp_points[i + 1], slope_high);
    }
  }

  // Should never reach here
  const float* params = discharging_mode ? model->ocv_discharge_params[0]
                                         : model->ocv_charge_params[0];
  return calc_ocv_slope(model, params, soc);
}

float battery_soc(const battery_model_t* model, float ocv, float temperature,
                  bool discharging_mode) {
  // Select appropriate temperature array based on mode
  const float* temp_points = discharging_mode ? model->temp_points_discharge
                                              : model->temp_points_charge;

  // Handle out-of-bounds temperatures
  if (temperature <= temp_points[0]) {
    const float* params = discharging_mode ? model->ocv_discharge_params[0]
                                           : model->ocv_charge_params[0];
    return calc_soc_from_ocv(model, params, ocv);
  }

  if (temperature >= temp_points[model->num_temp_points - 1]) {
    const float* params =
        discharging_mode
            ? model->ocv_discharge_params[model->num_temp_points - 1]
            : model->ocv_charge_params[model->num_temp_points - 1];
    return calc_soc_from_ocv(model, params, ocv);
  }

  // Find temperature bracket and interpolate
  for (int i = 0; i < model->num_temp_points - 1; i++) {
    if (temperature < temp_points[i + 1]) {
      const float* params_low = discharging_mode
                                    ? model->ocv_discharge_params[i]
                                    : model->ocv_charge_params[i];

      const float* params_high = discharging_mode
                                     ? model->ocv_discharge_params[i + 1]
                                     : model->ocv_charge_params[i + 1];

      float soc_low = calc_soc_from_ocv(model, params_low, ocv);
      float soc_high = calc_soc_from_ocv(model, params_high, ocv);

      return linear_interpolate(temperature, temp_points[i], soc_low,
                                temp_points[i + 1], soc_high);
    }
  }

  // Should never reach here
  const float* params = discharging_mode ? model->ocv_discharge_params[0]
                                         : model->ocv_charge_params[0];
  return calc_soc_from_ocv(model, params, ocv);
}

void battery_model_init(battery_model_t* model) {
  unit_properties_t props = {0};
  unit_properties_get(&props);

  // todo: this is model specific, should probably be handled somewhere outside
  //  of this module but since we currently only have one model we can live with
  //  this for a while
  switch (props.battery_type) {
    case 0:
    default:
      model->soc_breakpoint_1 = BATTERY_JYHPFL333838_SOC_BREAKPOINT_1;
      model->soc_breakpoint_2 = BATTERY_JYHPFL333838_SOC_BREAKPOINT_2;
      model->num_temp_points = BATTERY_JYHPFL333838_NUM_TEMP_POINTS;
      model->temp_points_charge = BATTERY_JYHPFL333838_TEMP_POINTS_CHG;
      model->temp_points_discharge = BATTERY_JYHPFL333838_TEMP_POINTS_DISCHG;
      model->r_int_params = BATTERY_JYHPFL333838_R_INT_PARAMS;
      model->ocv_charge_params = BATTERY_JYHPFL333838_OCV_CHARGE_PARAMS;
      model->ocv_discharge_params = BATTERY_JYHPFL333838_OCV_DISCHARGE_PARAMS;
      model->capacity = BATTERY_JYHPFL333838_CAPACITY;
      break;
    case 1:
      model->soc_breakpoint_1 = BATTERY_HCF343837NCZ_SOC_BREAKPOINT_1;
      model->soc_breakpoint_2 = BATTERY_HCF343837NCZ_SOC_BREAKPOINT_2;
      model->num_temp_points = BATTERY_HCF343837NCZ_NUM_TEMP_POINTS;
      model->temp_points_charge = BATTERY_HCF343837NCZ_TEMP_POINTS_CHG;
      model->temp_points_discharge = BATTERY_HCF343837NCZ_TEMP_POINTS_DISCHG;
      model->r_int_params = BATTERY_HCF343837NCZ_R_INT_PARAMS;
      model->ocv_charge_params = BATTERY_HCF343837NCZ_OCV_CHARGE_PARAMS;
      model->ocv_discharge_params = BATTERY_HCF343837NCZ_OCV_DISCHARGE_PARAMS;
      model->capacity = BATTERY_HCF343837NCZ_CAPACITY;
      break;
  }
}

#endif
