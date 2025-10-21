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

#pragma once

#include <trezor_types.h>

#include "battery_model.h"

// fuel gauge state structure
typedef struct {
  battery_model_t model;

  // State estimate (SOC)
  float soc;
  // Latched SOC (the one that gets reported)
  float soc_latched;
  // Error covariance
  float P;
  // Filter parameters
  float R;             // Measurement noise variance
  float Q;             // Process noise variance
  float R_aggressive;  // Aggressive measurement noise variance
  float Q_aggressive;  // Aggressive process noise variance
} fuel_gauge_state_t;

/**
 * Initialize the fuel gauge state
 * @param state Pointer to EKF state structure
 * @param R Measurement noise variance
 * @param Q Process noise variance
 * @param R_aggressive Aggressive mode measurement noise variance
 * @param Q_aggressive Aggressive mode process noise variance
 * @param P_init Initial error covariance
 */
void fuel_gauge_init(fuel_gauge_state_t* state, float R, float Q,
                     float R_aggressive, float Q_aggressive, float P_init);

/**
 * Reset the EKF state
 * @param state Pointer to EKF state structure
 */
void fuel_gauge_reset(fuel_gauge_state_t* state);

/**
 * Set SOC directly
 * @param state Pointer to EKF state structure
 * @param soc State of charge (0.0 to 1.0)
 */
void fuel_gauge_set_soc(fuel_gauge_state_t* state, float soc, float P);

/**
 * Make initial SOC guess based on OCV
 * @param state Pointer to EKF state structure
 * @param voltage_V Current battery voltage (V)
 * @param current_mA Current battery current (mA), positive for discharge
 * @param temperature Battery temperature (°C)
 */
void fuel_gauge_initial_guess(fuel_gauge_state_t* state, float voltage_V,
                              float current_mA, float temperature);

/**
 * Update the fuel gauge with new measurements
 * @param state Pointer to EKF state structure
 * @param dt Time step in milliseconds
 * @param voltage_V Current battery voltage (V)
 * @param current_mA Current battery current (mA), positive for discharge
 * @param temperature Battery temperature (°C)
 * @return Updated SOC estimate (0.0 to 1.0)
 */
float fuel_gauge_update(fuel_gauge_state_t* state, uint32_t dt_ms,
                        float voltage_V, float current_mA, float temperature);
