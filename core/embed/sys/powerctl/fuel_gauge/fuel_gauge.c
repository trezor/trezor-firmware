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
 * Fuel Gauge Algorithm Implementation
 */
#include <trezor_types.h>

#include "fuel_gauge.h"
#include "battery_lookup_tables.h"
#include <math.h>

// Initialize the fuel gauge
void fuel_gauge_init(fuel_gauge_t *fg, float Q, float R, float P_init) {
    fg->state_of_charge = 0.0f;
    fg->error_covariance = P_init;
    fg->process_noise = Q;
    fg->measurement_noise = R;
    fg->initial_covariance = P_init;
}

// Reset the fuel gauge state
void fuel_gauge_reset(fuel_gauge_t *fg) {
    fg->state_of_charge = 0.0f;
    fg->error_covariance = fg->initial_covariance;
}

// Convert measured battery voltage to open-circuit voltage
float fuel_gauge_meas_to_ocv(float V_meas, float I_meas, float T_meas) {
    return V_meas + ((I_meas / 1000.0f) * battery_get_internal_resistance(T_meas));
}

// Use the very first measurement to initialize the state of charge
void fuel_gauge_initial_guess(fuel_gauge_t *fg, float V_meas, float I_meas, float T_meas) {
    float ocv = fuel_gauge_meas_to_ocv(V_meas, I_meas, T_meas);
    fg->state_of_charge = battery_get_soc(ocv, T_meas);
    fg->error_covariance = fg->initial_covariance;
}

// Update the fuel gauge state using Kalman filter
float fuel_gauge_update(fuel_gauge_t *fg, float dt, float V_meas, float I_meas, float T_meas) {
    // dt needs to be in seconds, but is provided in milliseconds
    float dt_seconds = dt / 1000.0f;

    // Get battery capacity at current temperature
    float total_capacity = battery_get_capacity(T_meas);

    // Predict step (time update)
    // State transition: x_k1_k = x_k - (I*dt)/(3600*capacity)
    float x_k1_k = fg->state_of_charge - (I_meas / (3600.0f * total_capacity)) * dt_seconds;

    // Update error covariance: P_k1_k = P_k + Q
    float P_k1_k = fg->error_covariance + fg->process_noise;

    // Get internal resistance at current temperature
    float r_int = battery_get_internal_resistance(T_meas);

    // Get predicted open circuit voltage
    float voc_predicted = battery_get_voc(x_k1_k, T_meas);

    // Predicted terminal voltage: V_pred = VOC - I*R_int
    float v_predicted = voc_predicted - (I_meas / 1000.0f) * r_int;

    // Kalman gain: K = P / (P + R)
    float K_k1_k = P_k1_k / (P_k1_k + fg->measurement_noise);

    // Update state: x = x_pred + K * (V_meas - V_pred)
    float x_k1_k1 = x_k1_k + K_k1_k * (V_meas - v_predicted);

    // Update error covariance: P = (1-K) * P_pred
    float P_k1_k1 = (1.0f - K_k1_k) * P_k1_k;

    // Update state
    fg->state_of_charge = x_k1_k1;
    fg->error_covariance = P_k1_k1;

    return fg->state_of_charge;
}

// Get the current SoC estimate
float fuel_gauge_get_soc(const fuel_gauge_t *fg) {
    return fg->state_of_charge;
}