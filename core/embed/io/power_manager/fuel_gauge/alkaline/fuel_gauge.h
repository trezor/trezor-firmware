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

/**
 * @brief Fuel gauge state structure
 */
typedef struct {
  float soc;          ///< State of charge estimate (0.0 to 1.0)
  float soc_latched;  ///< Latched SOC (the one that gets reported)

  
} fuel_gauge_state_t;

typedef struct {
  // TODO: consider to delete bat_esr_init and use only bat_esr_ocv
  float bat_esr_init;  ///< Battery internal resistance of 100ms current pulse
                       ///< [Ohm]
  float bat_esr_ocv;   ///< Battery internal resistance of 2 second load [Ohm]
  float bat_esr_nfc;   ///< Battery internal resistance for NFC survival [Ohm]
} battery_model_t;

/**
 * @brief Initialize the fuel gauge state
 *
 * @param state Pointer to the fuel gauge state structure to be initialized
 */
void fuel_gauge_init(fuel_gauge_state_t* state);

/**
 * @brief Reset the EKF state
 *
 * @param state Pointer to the fuel gauge state structure to be reset
 */
void fuel_gauge_reset(fuel_gauge_state_t* state);

/**
 * @brief Calculate internal resistance (Rint)
 * @param voltage_V_low Low load voltage measurement (V)
 * @param current_mA_low Low load current measurement (mA)
 * @param voltage_V_high High load voltage measurement (V)
 * @param current_mA_high High load current measurement (mA)
 * @return Calculated internal resistance (Ohm)
 */
float fuel_gauge_rint(float voltage_V_low, float current_mA_low,
                      float voltage_V_high, float current_mA_high);

/**
 * @brief Measure open circuit voltage (OCV)
 * @param model Pointer to the battery model structure
 * @param voltage_V Terminal voltage (V)
 * @param current_mA Current (mA), positive for discharge
 * @param temperature Temperature (°C)
 * @return Measured OCV (V)
 */
float fuel_gauge_meas_to_ocv(float battery_esr, float voltage_V,
                             float current_mA, float temperature);
/**
 * @brief Set SOC directly
 * @param state Pointer to the fuel gauge state structure
 * @param soc State of charge (0.0 to 1.0)
 */
void fuel_gauge_set_soc(fuel_gauge_state_t* state, float soc);

/**
 * @brief Make initial SOC guess based on OCV
 *
 * @param model Pointer to the battery model structure
 * @param state Pointer to EKF state structure
 * @param voltage_V Current battery voltage (V)
 * @param current_mA Current battery current (mA), positive for discharge
 * @param temperature Battery temperature (°C)
 */
void fuel_gauge_initial_guess(fuel_gauge_state_t* state, battery_model_t* model,
                              float voltage_V, float current_mA,
                              float temperature);

/**
 * @brief Update the fuel gauge with new measurements
 *
 * @param state Pointer to EKF state structure
 * @param voltage_V Current battery voltage (V)
 * @param current_mA Current battery current (mA), positive for discharge
 * @param temperature Battery temperature (°C)
 * @param timestamp Timestamp in milliseconds
 * @return Updated SOC estimate (0.0 to 1.0)
 */
float fuel_gauge_update(fuel_gauge_state_t* state,
                        battery_model_t* battery_model, float voltage_V,
                        float current_mA, float temperature,
                        uint32_t timestamp);
