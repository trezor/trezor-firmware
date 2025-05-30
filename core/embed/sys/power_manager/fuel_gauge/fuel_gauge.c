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

#include "fuel_gauge.h"
#include <math.h>
#include "battery_model.h"

void fuel_gauge_init(fuel_gauge_state_t* state, float R, float Q,
                     float R_aggressive, float Q_aggressive, float P_init) {
  state->R = R;
  state->Q = Q;
  state->R_aggressive = R_aggressive;
  state->Q_aggressive = Q_aggressive;

  // Initialize state
  state->soc = 0.0f;
  state->soc_latched = 0.0f;
  state->P = P_init;  // Initial error covariance
}

void fuel_gauge_reset(fuel_gauge_state_t* state) {
  // Reset state but keep filter parameters
  state->soc = 0.0f;
  state->soc_latched = 0.0f;
}

void fuel_gauge_set_soc(fuel_gauge_state_t* state, float soc, float P) {
  // Set SOC directly
  state->soc = soc;
  state->soc_latched = soc;
  state->P = P;  // Set error covariance
}

void fuel_gauge_initial_guess(fuel_gauge_state_t* state, float voltage_V,
                              float current_mA, float temperature) {
  // Determine if we're in discharge mode
  bool discharging_mode = current_mA >= 0.0f;

  // Calculate OCV from terminal voltage and current
  float ocv = battery_meas_to_ocv(voltage_V, current_mA, temperature);

  // Get SOC from OCV using lookup
  state->soc = battery_soc(ocv, temperature, discharging_mode);
  state->soc_latched = state->soc;
}

float fuel_gauge_update(fuel_gauge_state_t* state, uint32_t dt_ms,
                        float voltage_V, float current_mA, float temperature) {
  // Determine if we're in discharge mode
  bool discharging_mode = current_mA >= 0.0f;

  // Choose filter parameters based on temperature and SOC
  float R = state->R;
  float Q = state->Q;

  if (temperature < 10.0f) {
    // Cold temperature - use more conservative values
    R = 10.0f;
    Q = 0.01f;
  } else if (state->soc_latched < 0.2f) {
    // Low SOC - use aggressive values to track more closely
    R = state->R_aggressive;
    Q = state->Q_aggressive;
  }

  // Convert milliseconds to seconds
  float dt_sec = dt_ms / 1000.0f;

  // Get total capacity at current temperature
  float total_capacity = battery_total_capacity(temperature, discharging_mode);

  // State prediction (coulomb counting)
  // SOC_k+1 = SOC_k - (I*dt)/(3600*capacity)
  float x_k1_k =
      state->soc - (current_mA / (3600.0f * total_capacity)) * dt_sec;

  // Calculate Jacobian of measurement function h(x) = dOCV/dSOC
  float h_jacobian = battery_ocv_slope(x_k1_k, temperature, discharging_mode);

  // Error covariance prediction
  float P_k1_k = state->P + Q;

  // Calculate innovation covariance
  float S = h_jacobian * P_k1_k * h_jacobian + R;

  // Calculate Kalman gain
  float K_k1_k = P_k1_k * h_jacobian / S;

  // Calculate predicted terminal voltage
  float v_pred = battery_ocv(x_k1_k, temperature, discharging_mode) -
                 (current_mA / 1000.0f) * battery_rint(temperature);

  // State update
  float x_k1_k1 = x_k1_k + K_k1_k * (voltage_V - v_pred);

  // Error covariance update
  float P_k1_k1 = (1.0f - K_k1_k * h_jacobian) * P_k1_k;

  // Enforce SOC boundaries
  state->soc = (x_k1_k1 < 0.0f) ? 0.0f : ((x_k1_k1 > 1.0f) ? 1.0f : x_k1_k1);
  state->P = P_k1_k1;

  // Update latched SOC based on current direction
  if (current_mA > 0.0f) {
    // Discharging, SOC should move only in negative direction
    if (state->soc < state->soc_latched) {
      state->soc_latched = state->soc;
    }
  } else {
    // Charging, SOC should move only in positive direction
    if (state->soc > state->soc_latched) {
      state->soc_latched = state->soc;
    }
  }

  return state->soc_latched;
}
