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
 * Fuel Gauge Algorithm for LiFePO4 Batteries
 *
 * C implementation of battery state of charge estimation algorithm
 * using Kalman filtering and temperature-dependent battery models.
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>

// Fuel gauge structure to track state
typedef struct {
    float state_of_charge;     // SoC (x in Python)
    float error_covariance;    // Estimation error covariance (P in Python)
    float process_noise;       // Process noise covariance (Q in Python)
    float measurement_noise;   // Measurement noise covariance (R in Python)
    float initial_covariance;  // Initial error covariance (P_init in Python)
} fuel_gauge_t;

/**
 * Initialize the fuel gauge with Kalman filter parameters
 *
 * @param fg Pointer to fuel gauge structure
 * @param Q Process noise covariance (how much you trust the model)
 * @param R Measurement noise covariance (how much you trust the sensors)
 * @param P_init Initial error covariance (confidence in initial guess)
 */
void fuel_gauge_init(fuel_gauge_t *fg, float Q, float R, float P_init);

/**
 * Reset the fuel gauge state
 *
 * @param fg Pointer to fuel gauge structure
 */
void fuel_gauge_reset(fuel_gauge_t *fg);

/**
 * Use the first measurement to initialize the state of charge
 *
 * @param fg Pointer to fuel gauge structure
 * @param V_meas Measured battery voltage (V)
 * @param I_meas Measured battery current (mA, positive = discharge)
 * @param T_meas Measured battery temperature (°C)
 */
void fuel_gauge_initial_guess(fuel_gauge_t *fg, float V_meas, float I_meas, float T_meas);

/**
 * Update the fuel gauge state using Kalman filter
 *
 * @param fg Pointer to fuel gauge structure
 * @param dt Time since last update (milliseconds)
 * @param V_meas Measured battery voltage (V)
 * @param I_meas Measured battery current (mA, positive = discharge)
 * @param T_meas Measured battery temperature (°C)
 * @return Updated state of charge estimate (0.0 to 1.0)
 */
float fuel_gauge_update(fuel_gauge_t *fg, float dt, float V_meas, float I_meas, float T_meas);

/**
 * Get the current SoC estimate
 *
 * @param fg Pointer to fuel gauge structure
 * @return Current state of charge estimate (0.0 to 1.0)
 */
float fuel_gauge_get_soc(const fuel_gauge_t *fg);

/**
 * Convert measured battery voltage to open-circuit voltage
 * by compensating for IR drop
 *
 * @param V_meas Measured battery voltage (V)
 * @param I_meas Measured battery current (mA, positive = discharge)
 * @param T_meas Measured battery temperature (°C)
 * @return Calculated open circuit voltage (V)
 */
float fuel_gauge_meas_to_ocv(float V_meas, float I_meas, float T_meas);
