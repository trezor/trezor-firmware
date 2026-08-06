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

#include "battery_model.h"
#include "fuel_gauge.h"

// Fuel gauge extended kalman filter parameters
#define FUEL_GAUGE_R 3500.0f
#define FUEL_GAUGE_Q 0.0001f
#define FUEL_GAUGE_R_AGGRESSIVE 3000.0f
#define FUEL_GAUGE_Q_AGGRESSIVE 0.0002f
#define FUEL_GAUGE_P_INIT 0.1f

void fuel_gauge_init(fuel_gauge_state_t* state) {
  // Initialize state
  fuel_gauge_reset(state);
  state->P = FUEL_GAUGE_P_INIT;  // Initial error covariance
}

void fuel_gauge_reset(fuel_gauge_state_t* state) {
  state->soc = 0.0f;
  state->soc_latched = 0.0f;
}

void fuel_gauge_set_soc(fuel_gauge_state_t* state, float soc, float P) {
  soc = fmaxf(0.0f, fminf(soc, 1.0f));  // Clamp SOC to [0, 1]

  // Set SOC directly
  state->soc = soc;
  state->soc_latched = soc;
  state->P = P;  // Set error covariance
}

void fuel_gauge_initial_guess(fuel_gauge_state_t* state, battery_model_t* model,
                              float voltage_V, float current_mA,
                              float temperature) {
  // Determine if we're in discharge mode
  bool discharging_mode = current_mA >= 0.0f;

  // Calculate OCV from terminal voltage and current
  float ocv = battery_meas_to_ocv(model, voltage_V, current_mA, temperature);

  // Extract SoC from battery model
  state->soc = battery_soc(model, ocv, temperature, discharging_mode);
  state->soc = fmaxf(0.0f, fminf(state->soc, 1.0f));  // Clamp SOC to [0, 1]
  state->soc_latched = state->soc;
}

float fuel_gauge_update(fuel_gauge_state_t* state, battery_model_t* model,
                        uint32_t dt_ms, float voltage_V, float current_mA,
                        float temperature) {
  if (current_mA == 0.0f) {
    // No current flow, return latched SOC without updating
    return state->soc_latched;
  }

  // Determine if we're in discharge mode
  bool discharging_mode = current_mA >= 0.0f;

  // Choose filter parameters based on temperature and SOC
  float R = FUEL_GAUGE_R;
  float Q = FUEL_GAUGE_Q;

  // When in low temperature or at the edge of the charging/dischargins
  // profile, use more agressive EKF settings to rely more on the ocv
  // curves rather then on current model
  if (temperature < 10.0f) {
    R = FUEL_GAUGE_R_AGGRESSIVE;
    Q = FUEL_GAUGE_Q_AGGRESSIVE;
  } else {
    if (discharging_mode && state->soc_latched < 0.2f) {
      R = FUEL_GAUGE_R_AGGRESSIVE;
      Q = FUEL_GAUGE_Q_AGGRESSIVE;
    } else if (!discharging_mode && state->soc_latched > 0.8f) {
      R = FUEL_GAUGE_R_AGGRESSIVE;
      Q = FUEL_GAUGE_Q_AGGRESSIVE;
    }
  }

  // Convert milliseconds to seconds
  float dt_sec = dt_ms / 1000.0f;

  // Get total capacity at current temperature
  float total_capacity =
      battery_total_capacity(model, temperature, discharging_mode);

  // State prediction (coulomb counting)
  // SOC_k+1 = SOC_k - (I*dt)/(3600*capacity)
  float x_k1_k =
      state->soc - (current_mA / (3600.0f * total_capacity)) * dt_sec;

  // Calculate Jacobian of measurement function h(x) = dOCV/dSOC
  float h_jacobian =
      battery_ocv_slope(model, x_k1_k, temperature, discharging_mode);

  // Error covariance prediction
  float P_k1_k = state->P + Q;

  // Calculate innovation covariance
  float S = h_jacobian * P_k1_k * h_jacobian + R;

  // Calculate Kalman gain
  float K_k1_k = P_k1_k * h_jacobian / S;

  // Calculate predicted terminal voltage
  float v_pred = battery_ocv(model, x_k1_k, temperature, discharging_mode) -
                 (current_mA / 1000.0f) * battery_rint(model, temperature);

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

#endif
