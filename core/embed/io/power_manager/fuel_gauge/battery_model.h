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

// Include the battery data header - this will be selected at compile time
// based on which battery is being used
#include "battery_data_hcf343837ncz.h"
#include "battery_data_jyhpfl333838.h"

typedef struct {
  uint8_t num_temp_points;
  float soc_breakpoint_1;
  float soc_breakpoint_2;
  const float* temp_points_discharge;
  const float* temp_points_charge;
  const float* r_int_params;
  const float (*ocv_discharge_params)[10];
  const float (*ocv_charge_params)[10];
  const float (*capacity)[2];
} battery_model_t;

/**
 * Calculate internal resistance at the given temperature
 * @param temperature Battery temperature in Celsius
 * @return Internal resistance in ohms
 */
float battery_rint(const battery_model_t* model, float temperature);

/**
 * Get battery total capacity at the given temperature and discharge mode
 * @param temperature Battery temperature in Celsius
 * @param discharging_mode true if discharging, false if charging
 * @return Total capacity in mAh
 */
float battery_total_capacity(const battery_model_t* model, float temperature,
                             bool discharging_mode);

/**
 * Calculate OCV from measured voltage and current
 * @param voltage_V Measured battery voltage in volts
 * @param current_mA Measured battery current in mA (positive for discharge)
 * @param temperature Battery temperature in Celsius
 * @return Open circuit voltage (OCV) in volts
 */
float battery_meas_to_ocv(const battery_model_t* model, float voltage_V,
                          float current_mA, float temperature);

/**
 * Get OCV for given SOC and temperature
 * @param soc State of charge (0.0 to 1.0)
 * @param temperature Battery temperature in Celsius
 * @param discharging_mode true if discharging, false if charging
 * @return Open circuit voltage in volts
 */
float battery_ocv(const battery_model_t* model, float soc, float temperature,
                  bool discharging_mode);

/**
 * Get the slope of the OCV curve at a given SOC and temperature
 * @param soc State of charge (0.0 to 1.0)
 * @param temperature Battery temperature in Celsius
 * @param discharging_mode true if discharging, false if charging
 * @return Slope of OCV curve (dOCV/dSOC) in volts
 */
float battery_ocv_slope(const battery_model_t* model, float soc,
                        float temperature, bool discharging_mode);

/**
 * Get SOC for given OCV and temperature
 * @param ocv Open circuit voltage in volts
 * @param temperature Battery temperature in Celsius
 * @param discharging_mode true if discharging, false if charging
 * @return State of charge (0.0 to 1.0)
 */
float battery_soc(const battery_model_t* model, float ocv, float temperature,
                  bool discharging_mode);

/**
 * @brief Initializes the battery model structure based on used battery type
 *
 * @param model Pointer to the battery model structure to be initialized
 */
void battery_model_init(battery_model_t* model);
