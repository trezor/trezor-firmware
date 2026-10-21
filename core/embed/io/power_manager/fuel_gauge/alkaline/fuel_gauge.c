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

#include "battery_model/soc_ocv.h"
#include "fuel_gauge.h"

void fuel_gauge_init(fuel_gauge_state_t* state) {
  // Initialize state
  fuel_gauge_reset(state);
}

void fuel_gauge_reset(fuel_gauge_state_t* state) {
  state->soc = 0.0f;
  state->soc_latched = 0.0f;
}

void fuel_gauge_set_soc(fuel_gauge_state_t* state, float soc) {
  soc = fmaxf(0.0f, fminf(soc, 1.0f));  // Clamp SOC to [0, 1]

  // Set SOC directly
  state->soc = soc;
  state->soc_latched = soc;
}

float fuel_gauge_rint(float voltage_V_low, float current_mA_low,
                      float voltage_V_high, float current_mA_high) {
  float delta_voltage = voltage_V_low - voltage_V_high;
  float delta_current = current_mA_high - current_mA_low;
  if (fabsf(delta_current) < 1e-6f) {
    return 0.0f;  // Avoid division by zero
  }
  return delta_voltage / (delta_current / 1000.0f);  // Convert mA to A
}

float fuel_gauge_meas_to_ocv(float battery_esr, float voltage_V,
                             float current_mA, float temperature) {
  // Convert mA to A by dividing by 1000
  float current_A = current_mA / 1000.0f;

  // Calculate OCV: V_OC = V_term + I * ESR
  return voltage_V + (current_A * battery_esr);
}

void fuel_gauge_initial_guess(fuel_gauge_state_t* state, battery_model_t* model,
                              float voltage_V, float current_mA,
                              float temperature) {
  // Calculate OCV from terminal voltage and current
  float esr =
      model->bat_esr_ocv > 0.0f ? model->bat_esr_ocv : model->bat_esr_init;
  float ocv = fuel_gauge_meas_to_ocv(esr, voltage_V, current_mA, temperature);

  // Extract SoC from battery model
  state->soc =
      soc_ocv_lut((uint16_t)(ocv * 1000.0f), (int16_t)(temperature)) / 1000.0f;
  state->soc = fmaxf(0.0f, fminf(state->soc, 1.0f));  // Clamp SOC to [0, 1]
  state->soc_latched = state->soc;
}

float fuel_gauge_update(fuel_gauge_state_t* state, battery_model_t* model,
                        float voltage_V, float current_mA, float temperature,
                        uint32_t timestamp) {
  if ((current_mA < 1.0f) || (voltage_V < 0.5f)) {
    // No current flow, return latched SOC without updating
    return state->soc_latched;
  }

  // 1. Fill buffer to calculate ESR

  // 2. When filled with pre-pulse and pulse => calculate ESR, OCV, SoC

  // TODO: add filtering of measured SoC

  // Calculate Kalman gain
  // Calculate predicted terminal voltage
  // State update
  // Error covariance update
  // Enforce SOC boundaries

  // Discharging, SOC should move only in negative direction
  if (state->soc < state->soc_latched) {
    state->soc_latched = state->soc;
  }

  return state->soc_latched;
}

#endif
