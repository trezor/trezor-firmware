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
#include <sys/systick.h>

#include "battery_model/include/soc_ocv.h"
#include "dummy_load.h"
#include "fuel_gauge.h"

//!< Maximum duration of CUR_DUMMY pin is on.
#define BAT_FG_CUR_DUMMY_TIMEOUT_MS 500
//!< Expected battery current during bootloader [mA].
#define BAT_FG_CUR_BOOTLOADER_MA (50.0f)
//!< Minimum battery current during bootloader + CUR_DUMMY
#define BAT_FG_CUR_BOOTLOADER_DUMMY_MIN_MA(boot_sample) \
  ((DUMMY_LOAD_MA + boot_sample) * 0.7f)

// Kalman filter on SoC. Every dummy load pulse gives a SoC from the OCV
// lookup table; the pulses are weighted by their variance:
//  - The bootloader pulse comes from a rested cell at a low current, its OCV
//    is the most accurate one: high weight.
//  - The application load polarizes the cell, so the OCVs of the application
//    pulses read low by tens of mV: low weight.
// Between the pulses the SoC estimate stays, only its variance grows with the
// charge drawn. The newer pulses thus gradually take over from the bootloader
// one. No battery capacity is used.
//!< 1-sigma error of the SoC from the bootloader pulse
#define FG_SIGMA_BOOT 0.02f
//!< 1-sigma error of the SoC from an application pulse. The bootloader pulse
//!< weighs (FG_SIGMA_APP / FG_SIGMA_BOOT)^2 = 25 application pulses.
#define FG_SIGMA_APP 0.1f
//!< SoC variance growth per charge drawn [SoC^2 / mAh]. Sets how fast the
//!< application pulses take over: at 150 mA, the bootloader pulse keeps
//!< about half its weight for 2 minutes.
#define FG_Q_SOC_MAH 1e-4f
//!< Time between two application pulses [s]: 9 s pause, 10 base samples
#define FG_PULSE_PERIOD_S 10.0f
//
// Plausibility of a pulse measurement
//!< The dummy load must raise the current by at least this much [mA]
#define FG_PULSE_MIN_DELTA_MA (DUMMY_LOAD_MA * 0.5f)
#define FG_ESR_MIN_OHM 0.02f
#define FG_ESR_MAX_OHM 3.0f
#define FG_OCV_MIN_V 0.8f
#define FG_OCV_MAX_V 1.8f
//
// Covariance range. FG_P_MAX also stands for an unknown SoC (the variance of
// a uniform distribution on [0, 1] is 1/12).
#define FG_P_MIN 1e-6f
#define FG_P_MAX 0.1f
//!< The reported SoC only decreases once the estimate is better than 10 %
#define FG_P_LATCH (0.1f * 0.1f)

static void fuel_gauge_reset_buffer(fuel_gauge_buffer_t* buffer);
static void fuel_gauge_base_sample(const fuel_gauge_buffer_t* buffer,
                                   fuel_gauge_sample_t* base);
static float fuel_gauge_calculate_nfc_esr(fuel_gauge_buffer_t* buffer);
static bool fuel_gauge_measure(const fuel_gauge_sample_t* base,
                               const fuel_gauge_sample_t* pulse, float* esr,
                               float* soc);

static float clampf(float x, float lo, float hi) {
  return fmaxf(lo, fminf(x, hi));
}

void fuel_gauge_init(fuel_gauge_state_t* state,
                     fuel_gauge_buffer_t* sample_buf) {
  // Initialize state
  fuel_gauge_reset(state);
  fuel_gauge_reset_buffer(sample_buf);
  sample_buf->sample_boot.timestamp_ms = systick_ms();
}

void fuel_gauge_reset(fuel_gauge_state_t* state) {
  state->soc = 0.0f;
  state->soc_latched = 0.0f;
  state->P = FG_P_MAX;
}

void fuel_gauge_set_soc(fuel_gauge_state_t* state, float soc) {
  // A SoC set from outside (backup RAM) weighs as the bootloader pulse
  state->soc = clampf(soc, 0.0f, 1.0f);
  state->soc_latched = state->soc;
  state->P = FG_SIGMA_BOOT * FG_SIGMA_BOOT;
}

float fuel_gauge_rint(const fuel_gauge_sample_t* sample_low,
                      const fuel_gauge_sample_t* sample_high) {
  float delta_voltage = sample_low->voltage_V - sample_high->voltage_V;
  float delta_current =
      (sample_high->current_mA - sample_low->current_mA) / 1000.0f;
  if ((delta_voltage < 0.0f) || (delta_current < 0.0f)) {
    return NAN;
  }
  if (fabsf(delta_current) < 1e-6f) {
    return 0.0f;  // Avoid division by zero
  }
  return delta_voltage / delta_current;
}

float fuel_gauge_meas_to_ocv(float battery_esr,
                             const fuel_gauge_sample_t* sample) {
  // Convert mA to A by dividing by 1000
  float current_A = sample->current_mA / 1000.0f;

  // Calculate OCV: V_OC = V_term + I * ESR
  return sample->voltage_V + (current_A * battery_esr);
}

void fuel_gauge_initial_guess(fuel_gauge_state_t* state, battery_model_t* model,
                              fuel_gauge_buffer_t* buffer) {
  float esr;
  float soc;

  if (fuel_gauge_measure(&buffer->sample_boot, &buffer->samples[1], &esr,
                         &soc)) {
    model->bat_esr_ocv = esr;
    fuel_gauge_set_soc(state, soc);
  } else {
    // Unknown SoC, the first application pulse decides
    model->bat_esr_ocv = NAN;
    fuel_gauge_reset(state);
  }
}

float fuel_gauge_update(fuel_gauge_state_t* state, battery_model_t* model,
                        fuel_gauge_buffer_t* buffer,
                        const fuel_gauge_sample_t* sample) {
  if ((sample->current_mA < 1.0f) || (sample->voltage_V < 0.5f)) {
    // No current flow, return latched SOC without updating
    return state->soc_latched;
  }

  if (fuel_gauge_feed_buffer(buffer, sample)) {
    if (isnan(model->bat_esr_nfc)) {
      model->bat_esr_nfc = fuel_gauge_calculate_nfc_esr(buffer);
    }

    fuel_gauge_sample_t base;
    fuel_gauge_base_sample(buffer, &base);

    // Predict: the SoC stays, its variance grows with the charge drawn since
    // the previous pulse
    state->P += FG_Q_SOC_MAH * base.current_mA * FG_PULSE_PERIOD_S / 3600.0f;

    // Correct with the SoC from the pulse OCV
    float esr;
    float soc;
    if (fuel_gauge_measure(&base, &buffer->samples[BAT_FG_SAMPLE_BUF_SIZE - 1],
                           &esr, &soc)) {
      model->bat_esr_ocv = esr;
      float K = state->P / (state->P + FG_SIGMA_APP * FG_SIGMA_APP);
      state->soc += K * (soc - state->soc);
      state->P = (1.0f - K) * state->P;
    }
  }

  state->soc = clampf(state->soc, 0.0f, 1.0f);
  state->P = clampf(state->P, FG_P_MIN, FG_P_MAX);

  // A primary cell only discharges: once the estimate is confident, the
  // reported SoC only moves down. An alkaline cell recovers voltage at rest,
  // which must not show as a rising SoC.
  if ((state->P > FG_P_LATCH) || (state->soc < state->soc_latched)) {
    state->soc_latched = state->soc;
  }

  return state->soc_latched;
}

// SoC of the given OCV from the lookup table (0.0 to 1.0)
static float fuel_gauge_ocv_to_soc(float ocv_V, float temp_C) {
  // Clamped to keep the integer conversions defined
  uint16_t ocv_mV = (uint16_t)(clampf(ocv_V, 0.0f, 5.0f) * 1000.0f + 0.5f);
  int16_t temp_dC = (int16_t)(clampf(temp_C, -100.0f, 200.0f) * 10.0f);
  return soc_ocv_lut(ocv_mV, temp_dC) / (float)SOC_OCV_FULL;
}

// Derives the ESR and the SoC from a dummy load pulse. base is the sample
// before the pulse, pulse the sample with the dummy load on. Returns false if
// the pulse is not usable.
static bool fuel_gauge_measure(const fuel_gauge_sample_t* base,
                               const fuel_gauge_sample_t* pulse, float* esr,
                               float* soc) {
  // The dummy load may have been off already, e.g. the sample came after the
  // pulse timer expired
  if (pulse->current_mA - base->current_mA < FG_PULSE_MIN_DELTA_MA) {
    return false;
  }

  float r = fuel_gauge_rint(base, pulse);
  if (!(r >= FG_ESR_MIN_OHM && r <= FG_ESR_MAX_OHM)) {  // false for NaN
    return false;
  }

  float ocv = fuel_gauge_meas_to_ocv(r, pulse);
  if (ocv < FG_OCV_MIN_V || ocv > FG_OCV_MAX_V) {
    return false;
  }

  *esr = r;
  *soc = fuel_gauge_ocv_to_soc(ocv, pulse->temp_C);
  return true;
}

static void fuel_gauge_reset_buffer(fuel_gauge_buffer_t* buffer) {
  memset((void*)buffer, 0, sizeof(*buffer));
}

void fuel_gauge_run_app_sampling(fuel_gauge_buffer_t* buffer) {
  memset((void*)&buffer->samples, 0, sizeof(buffer->samples));
  // to ensure we wait 9 seconds before the next dummy load pulse
  buffer->samples[BAT_FG_SAMPLE_BUF_SIZE - 1].timestamp_ms = systick_ms();
  buffer->head_idx = 0;
  buffer->buffer_state = FG_SAMPLE_APP;
}

bool fuel_gauge_feed_buffer(fuel_gauge_buffer_t* buffer,
                            const fuel_gauge_sample_t* sample) {
  fuel_gauge_buffer_state_e* state = &buffer->buffer_state;
  bool buffer_ready = false;

  // Accept only exact order of input samples in order to correctly
  // calculate initial ESR, OCV and SoC.
  switch (*state) {
    // TODO: Check how long we stay in bootloader mode with low power
    // consumption.

    // Bootloader mode - first measurement of V, I and Temp.
    // dTime >= 100 ms.
    // Expect low current < 50mA
    case FG_SAMPLE_INIT: {
      if ((sample->current_mA < (BAT_FG_CUR_BOOTLOADER_MA * 0.5f)) ||
          (sample->current_mA > BAT_FG_CUR_BOOTLOADER_MA) ||
          ((sample->timestamp_ms - buffer->sample_boot.timestamp_ms) < 100)) {
        return buffer_ready;
      }

      memcpy((void*)&buffer->sample_boot, (void*)sample, sizeof(*sample));
      dummy_load_on(buffer->pulse_timer, BAT_FG_CUR_DUMMY_TIMEOUT_MS);
      *state = FG_SAMPLE_INIT_PULSE;
      break;
    }
    // Bootloader + Dummy Load measurement.
    // Expect DUMMY current between 100 and 200 mA (TBD).
    // dTime >= 100 ms.
    // -> Calculation initial ESR, OCV and SoC.
    case FG_SAMPLE_INIT_PULSE: {
      // In case that the INIT_PULSE is not properly catched, restart the boot
      // sampling.
      if ((sample->timestamp_ms - buffer->sample_boot.timestamp_ms) >
          BAT_FG_CUR_DUMMY_TIMEOUT_MS) {
        buffer->head_idx = 0;
        *state = FG_SAMPLE_INIT;
        return buffer_ready;
      }

      if (((sample->timestamp_ms - buffer->sample_boot.timestamp_ms) < 100) ||
          (sample->current_mA < BAT_FG_CUR_BOOTLOADER_DUMMY_MIN_MA(
                                    buffer->sample_boot.current_mA))) {
        return buffer_ready;
      }

      dummy_load_off();
      *state = FG_SAMPLE_INIT_READY;
      break;
    }
    case FG_SAMPLE_INIT_READY: {
      return buffer_ready;
      break;
    }
    case FG_SAMPLE_APP: {
      // Application sample - measurement of V, I and Temp in Application mode.
      // dTime >= 1 second.
      uint8_t prev_idx = buffer->head_idx > 0 ? buffer->head_idx - 1
                                              : BAT_FG_SAMPLE_BUF_SIZE - 1;
      // accept only samples with time delta >= 100 ms from previous sample
      // and time delta >= 9 seconds from the last dummy pulse sample
      if (((sample->timestamp_ms - buffer->samples[prev_idx].timestamp_ms) <
           100) ||
          ((sample->timestamp_ms -
            buffer->samples[BAT_FG_SAMPLE_BUF_SIZE - 1].timestamp_ms) < 9000)) {
        return buffer_ready;
      }

      if (buffer->head_idx == (BAT_FG_SAMPLE_BUF_SIZE - 2)) {
        dummy_load_on(buffer->pulse_timer, BAT_FG_CUR_DUMMY_TIMEOUT_MS);
        *state = FG_SAMPLE_APP_PULSE;
      }
      break;
    }
    case FG_SAMPLE_APP_PULSE: {
      // Application mode + Dummy pulse.
      // dTime >= 100 ms.
      // -> Calculation more accurate ESR, OCV and SoC.
      if (((sample->timestamp_ms -
            buffer->samples[buffer->head_idx - 1].timestamp_ms) < 100)) {
        return buffer_ready;
      }

      dummy_load_off();
      *state = FG_SAMPLE_APP;
      buffer_ready = true;
      break;
    }
    default:
      fuel_gauge_run_app_sampling(buffer);
      return buffer_ready;
  }

  // Store battery data in the buffer
  memcpy((void*)&buffer->samples[buffer->head_idx], (void*)sample,
         sizeof(*sample));
  buffer->head_idx = (buffer->head_idx + 1) % BAT_FG_SAMPLE_BUF_SIZE;

  return buffer_ready;
}

// Average of the pre-pulse samples
static void fuel_gauge_base_sample(const fuel_gauge_buffer_t* buffer,
                                   fuel_gauge_sample_t* base) {
  float v_avg = 0;
  float i_avg = 0;
  for (uint8_t i = 0; i < BAT_FG_SAMPLE_BUF_SIZE - 1; i++) {
    v_avg += buffer->samples[i].voltage_V;
    i_avg += buffer->samples[i].current_mA;
  }

  memset(base, 0, sizeof(*base));
  base->voltage_V = v_avg / (BAT_FG_SAMPLE_BUF_SIZE - 1);
  base->current_mA = i_avg / (BAT_FG_SAMPLE_BUF_SIZE - 1);
}

static float fuel_gauge_calculate_nfc_esr(fuel_gauge_buffer_t* buffer) {
  return fuel_gauge_rint(&buffer->sample_boot,
                         &buffer->samples[BAT_FG_SAMPLE_BUF_SIZE - 2]);
}

#endif
