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
 * @file battery.h
 * @brief Battery management driver with Extended Kalman Filter fuel gauge
 *
 * This driver provides battery state estimation using an Extended Kalman Filter
 * (EKF) based fuel gauge algorithm. It estimates the State of Charge (SOC) by
 * processing battery voltage, current, and temperature measurements along with
 * a battery model.
 *
 * ## Usage:
 * 1. Initialize the driver with `bat_init()`
 * 2. Set the initial fuel gauge state using one of two approaches:
 *    - **If SOC is already known** (e.g., from persistent storage): Use
 * `bat_fg_set_soc()` to directly set the fuel gauge state and lock it for
 * operation
 *    - **If SOC is unknown**: Feed several measurement samples using
 * `bat_fg_feed_sample()`, then call `bat_fg_initial_guess()` to estimate the
 * initial SOC based on the collected voltage, current, and temperature data
 * 3. Continuously update the fuel gauge with new measurements using
 * `bat_fg_update()`
 * 4. Retrieve the current SOC estimate using `bat_fg_get_state()`
 *
 * The driver maintains an internal battery model for voltage-to-SOC conversion
 * and uses temperature compensation for improved accuracy across operating
 * conditions.
 */

#pragma once

#include <trezor_rtl.h>

#define BAT_FG_SAMPLE_BUF_SIZE 10

/** @brief Bat fuel gauge state structure */
typedef struct {
  float soc;          ///< State of charge estimate (0.0 to 1.0)
  float soc_latched;  ///< Latched SOC (the one that gets reported)
  float P;            ///< Error covariance
} bat_fg_state_t;

/**
 * @brief Initialize the battery module
 */
void bat_init(void);

/**
 * @brief Set the fuel gauge state to given SOC value
 *
 * This function will force set the fuel gauge SoC to given value and lock it.
 * May be used even if the fuel gauge was already locked.
 *
 **/
ts_t bat_fg_set_soc(float soc, float P);

/**
 * @brief Feed a new measurement sample to the unlocked fuel gauge.
 *
 * This function is used in case the fuel gauge was not yet initialized and
 * its state is unknown. To improve the state initial guess, user may use
 * this function to feed several samples first into the buffer, and then call
 * `bat_fg_initial_guess()` to compute the inital guess of the fuel gauge
 * state on larger set of samples.
 *
 * sampling buffer has size of `BAT_FG_SAMPLE_BUF_SIZE` and is build as circular
 * buffer, so after feeding more samples than the buffer size, only the most
 * recent samples are used for the initial guess estimation.
 *
 * @param voltage_V Measured battery voltage in volts
 * @param current_mA Measured battery current in mA (positive for discharge)
 * @param temp_C Battery temperature in Celsius
 * @return TS_OK on success, error code otherwise
 */
ts_t bat_fg_feed_sample(float voltage_V, float current_mA, float temp_C);

/**
 * @brief Make fuel gauge initial SOC guess based on the buffered samples.
 *
 * calling this funtion will process all the samples fed into the sampling
 * buffer with `bat_fg_feed_sample()` and compute the initial SOC guess
 * estimate. the fuel gauge state will be marked as locked after this call
 * and may be updated with `bat_fg_update()`.
 *
 */
ts_t bat_fg_initial_guess();

/**
 * @brief Check if the fuel gauge state is initialized and locked
 *
 * locked fuel gauge represents that fuel gauge state was correctly initialized
 * and may be updated based on the battery measuremets with `bat_fg_update()`.
 *
 * @return true if locked, false otherwise
 */
bool bat_fg_is_locked(void);

/**
 * @brief Get the current fuel gauge state
 *
 * @param data Pointer to the fuel gauge state structure to be filled.
 * @return TS_OK on success, error code otherwise
 */
ts_t bat_fg_get_state(bat_fg_state_t* data);

/**
 * @brief Update the fuel gauge EKD with the new measurement
 *
 * @param dt_ms Time delta since last update in milliseconds
 * @param voltage_V Measured battery voltage in volts
 * @param current_mA Measured battery current in mA (positive for discharge)
 * @param temp_C Battery temperature in Celsius
 * @return TS_OK on success, error code otherwise
 */
ts_t bat_fg_update(uint32_t dt_ms, float voltage_V, float current_mA,
                   float temp_C);

/**
 * @brief Compensate the fuel gauge SoC for constant charge/discharge over the
 * elapsed time period.
 *
 * This function adjust and returns the fuel gauge state of charge (SOC)
 * estimate with respect to the average battery current over a specified
 * elapsed time. Compenstation is useful if the battery has been
 * charging/discharging under static conditions without ability to update the
 * fuel gauge normally. (e.g., during system suspend or hibernation).
 *
 * @param soc Pointer to the fuel gauge state of charge (0.0 to 1.0) to be
 * compensated
 * @param elapsed_s Elapsed time period in seconds
 * @param avg_bat_current_mA Average battery current in mA (positive for
 * discharge)
 * @param avg_temp_C Average battery temperature in Celsius
 * @return TS_OK on success, error code otherwise
 */
ts_t bat_fg_compensate_soc(float* soc, uint32_t elapsed_s,
                           float avg_bat_current_mA, float avg_temp_C);

/**
 * @brief Convert battery SOC to OCV according to the battery model at given
 * temperature point.
 *
 * @param soc State of charge (0.0 to 1.0)
 * @param temp_C Temperature in Celsius
 * @param discharging_mode true if discharging, false if charging
 * @return Open circuit voltage in volts
 */
float bat_soc_to_ocv(float soc, float temp_C, bool discharging_mode);

/**
 * @brief Convert measured battery voltage and current to OCV according to the
 * battery model at given temperature point.
 *
 * @param voltage_V Measured battery voltage in volts
 * @param current_mA Measured battery current in mA (positive for discharge)
 * @param temp_C Battery temperature in Celsius
 * @return Open circuit voltage in volts
 *
 */
float bat_meas_to_ocv(float voltage_V, float current_mA, float temp_C);
