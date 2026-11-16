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

#include <sys/systimer.h>
#include <trezor_types.h>

//!< 10 samples of pre-pulse + 1 pulse sample
#define BAT_FG_SAMPLE_BUF_SIZE (10 + 1)

typedef enum {
  FG_SAMPLE_INIT = 0,    //!< Read V, I in bootloader
  FG_SAMPLE_INIT_PULSE,  //!< Read V, I in bootloader + CUR_DUMMY pulse
  FG_SAMPLE_INIT_READY,  //!< Initial phase is ready, bootloader stay here
  FG_SAMPLE_APP,
  FG_SAMPLE_APP_PULSE,
} fuel_gauge_buffer_state_e;

typedef struct {
  float voltage_V;
  float current_mA;
  float temp_C;
  uint32_t timestamp_ms;
} fuel_gauge_sample_t;

typedef struct {
  fuel_gauge_sample_t sample_boot;
  fuel_gauge_sample_t samples[BAT_FG_SAMPLE_BUF_SIZE];
  uint8_t head_idx;
  fuel_gauge_buffer_state_e buffer_state;
  systimer_t* pulse_timer;
} fuel_gauge_buffer_t;

/**
 * @brief Fuel gauge state structure
 *
 * State of a scalar Kalman filter on soc. It does not use the capacity of the
 * cell. P is the variance of the soc error.
 */
typedef struct {
  float soc;          ///< State of charge estimate (0.0 to 1.0)
  float soc_latched;  ///< Latched SOC (the one that gets reported)
  float P;            ///< Error covariance of soc [SoC^2]
} fuel_gauge_state_t;

typedef struct {
  float bat_esr_ocv;  ///< Battery internal resistance of 2 second in
                      ///< Application [Ohm]
  float bat_esr_nfc;  ///< Battery internal resistance for NFC survival [Ohm]
} battery_model_t;

/**
 * @brief Initialize the fuel gauge state
 *
 * @param state Pointer to the fuel gauge state structure to be initialized
 */
void fuel_gauge_init(fuel_gauge_state_t* state,
                     fuel_gauge_buffer_t* sample_buf);

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
float fuel_gauge_rint(const fuel_gauge_sample_t* sample_low,
                      const fuel_gauge_sample_t* sample_high);

/**
 * @brief Measure open circuit voltage (OCV)
 * @param model Pointer to the battery model structure
 * @param voltage_V Terminal voltage (V)
 * @param current_mA Current (mA), positive for discharge
 * @return Measured OCV (V)
 */
float fuel_gauge_meas_to_ocv(float battery_esr,
                             const fuel_gauge_sample_t* sample);
/**
 * @brief Set SOC directly, with the weight of the bootloader pulse
 * @param state Pointer to the fuel gauge state structure
 * @param soc State of charge (0.0 to 1.0)
 */
void fuel_gauge_set_soc(fuel_gauge_state_t* state, float soc);

/**
 * @brief Make initial SOC guess from the bootloader dummy load pulse
 *
 * Sets soc from the OCV of the bootloader sample and the pulse sample, with a
 * small variance: the application pulses weigh less. If the pulse is not
 * usable, soc is 0 with the maximum covariance, so the first application
 * pulse decides.
 *
 * @param state Pointer to the fuel gauge state structure
 * @param model Pointer to the battery model structure
 * @param state Pointer to EKF state structure
 * @param voltage_V Current battery voltage (V)
 * @param current_mA Current battery current (mA), positive for discharge
 * @param temperature Battery temperature (°C)
 */
void fuel_gauge_initial_guess(fuel_gauge_state_t* state, battery_model_t* model,
                              fuel_gauge_buffer_t* buffer);

/**
 * @brief Update the fuel gauge with new measurements
 *
 * Kalman filter step. When the sample completes a dummy load pulse, the
 * covariance grows with the charge drawn since the previous pulse (soc itself
 * is not predicted, the capacity is unknown) and the SoC derived from the
 * pulse OCV corrects soc.
 *
 * @param state Pointer to the fuel gauge state structure
 * @param model Pointer to the battery model structure
 * @param buffer Sample buffer driving the dummy load pulses
 * @param sample Battery measurement, current positive for discharge
 * @return Reported (latched) SOC (0.0 to 1.0)
 */
float fuel_gauge_update(fuel_gauge_state_t* state,
                        battery_model_t* battery_model,
                        fuel_gauge_buffer_t* buffer,
                        const fuel_gauge_sample_t* sample);

bool fuel_gauge_feed_buffer(fuel_gauge_buffer_t* buffer,
                            const fuel_gauge_sample_t* sample);

void fuel_gauge_run_app_sampling(fuel_gauge_buffer_t* buffer);
