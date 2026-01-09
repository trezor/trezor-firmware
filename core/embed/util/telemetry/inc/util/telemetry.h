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
 * @brief Telemetry data structure.
 */
typedef struct {
  float min_temp_c; /**< Minimum recorded battery temperature in Celsius. */
  float max_temp_c; /**< Maximum recorded battery temperature in Celsius. */
} telemetry_data_t;

/**
 * @brief Record current battery temperature (in Celsius) into telemetry
 * storage.
 *
 * Updates persisted min/max values:
 *  - minimum can only decrease
 *  - maximum can only increase
 *
 * @param temp_c Current battery temperature in Celsius.
 */
void telemetry_update_battery_temp(float temp_c);

/**
 * @brief Retrieve stored min/max battery temperature (in Celsius).
 *
 * @param[out] out Pointer to where the telemetry data will be stored (may be
 * NULL).
 *
 * @return true if values are available (initialized), false otherwise.
 */
bool telemetry_get(telemetry_data_t* out);
