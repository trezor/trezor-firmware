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

#include "battery_model/soc_ocv.h"
#include "dummy_load.h"
#include "fuel_gauge.h"

//!< Maximum duration of CUR_DUMMY pin is on.
#define BAT_FG_CUR_DUMMY_TIMEOUT_MS 500
//!< Expected battery current during bootloader [mA].
#define BAT_FG_CUR_BOOTLOADER_MA 50.0f
//!< Minimum battery current during bootloader + CUR_DUMMY
#define BAT_FG_CUR_BOOTLOADER_DUMMY_MIN_MA \
  (DUMMY_LOAD_MA + BAT_FG_CUR_BOOTLOADER_MA) * 0.7f
//!< Maximum battery current during bootloader + CUR_DUMMY
#define BAT_FG_CUR_BOOTLOADER_DUMMY_MAX_MA \
  (DUMMY_LOAD_MA + BAT_FG_CUR_BOOTLOADER_MA) * 1.3f

static void fuel_gauge_reset_buffer(fuel_gauge_buffer_t* buffer);
static float fuel_gauge_calculate_esr(fuel_gauge_buffer_t* buffer);
static float fuel_gauge_calculate_nfc_esr(fuel_gauge_buffer_t* buffer);

void fuel_gauge_init(fuel_gauge_state_t* state,
                     fuel_gauge_buffer_t* sample_buf) {
  // Initialize state
  fuel_gauge_reset(state);
  fuel_gauge_reset_buffer(sample_buf);
}

void fuel_gauge_reset(fuel_gauge_state_t* state) {
  state->soc = 0.0f;
  state->soc_latched = 0.0f;
}

void fuel_gauge_set_soc(fuel_gauge_state_t* state, float soc) {
  soc = fmaxf(0.0f, fminf(soc, 1.0f));  // Clamp SOC to [0, 1]

  // Set SOC directly
  state->soc = soc;
  state->soc_latched = soc;
}

float fuel_gauge_rint(float voltage_V_low, float current_mA_low,
                      float voltage_V_high, float current_mA_high) {
  float delta_voltage = voltage_V_low - voltage_V_high;
  float delta_current = (current_mA_high - current_mA_low) / 1000.0f;
  if ((delta_voltage < 0.0f) || (delta_current < 0.0f)) {
    return NAN;
  }
  if (fabsf(delta_current) < 1e-6f) {
    return 0.0f;  // Avoid division by zero
  }
  return delta_voltage / delta_current;
}

float fuel_gauge_meas_to_ocv(float battery_esr, float voltage_V,
                             float current_mA, float temperature) {
  // Convert mA to A by dividing by 1000
  float current_A = current_mA / 1000.0f;

  // Calculate OCV: V_OC = V_term + I * ESR
  return voltage_V + (current_A * battery_esr);
}

void fuel_gauge_initial_guess(fuel_gauge_state_t* state, battery_model_t* model,
                              fuel_gauge_buffer_t* buffer) {
  // Calculate ESR and OCV.
  model->bat_esr_init = fuel_gauge_rint(
      buffer->samples[0].voltage_V, buffer->samples[0].current_mA,
      buffer->samples[1].voltage_V, buffer->samples[1].current_mA);

  // Calculate OCV from terminal voltage and current
  float ocv = fuel_gauge_meas_to_ocv(
      model->bat_esr_init, buffer->samples[1].voltage_V,
      buffer->samples[1].current_mA, buffer->samples[1].temp_C);

  // Extract SoC from battery model
  state->soc = soc_ocv_lut((uint16_t)(ocv * 1000.0f),
                           (int16_t)(buffer->samples[1].temp_C)) /
               1000.0f;
  state->soc = fmaxf(0.0f, fminf(state->soc, 1.0f));  // Clamp SOC to [0, 1]
  state->soc_latched = state->soc;
}

float fuel_gauge_update(fuel_gauge_state_t* state, battery_model_t* model,
                        fuel_gauge_buffer_t* buffer,
                        const fuel_gauge_sample_t* sample) {
  if ((sample->current_mA < 1.0f) || (sample->voltage_V < 0.5f)) {
    // No current flow, return latched SOC without updating
    return state->soc_latched;
  }

  // 1. Fill buffer to calculate ESR
  if (fuel_gauge_feed_buffer(buffer, sample)) {
    // 2. When filled with pre-pulse and pulse => calculate ESR, OCV, SoC
    model->bat_esr_ocv = fuel_gauge_calculate_esr(buffer);

    if (isnan(model->bat_esr_nfc)) {
      model->bat_esr_nfc = fuel_gauge_calculate_nfc_esr(buffer);
    }

    if (!isnan(model->bat_esr_ocv)) {
      // Calculate OCV from terminal voltage and current
      float ocv = fuel_gauge_meas_to_ocv(
          model->bat_esr_ocv, buffer->samples[1].voltage_V,
          buffer->samples[1].current_mA, buffer->samples[1].temp_C);

      // Extract SoC from battery model
      state->soc = soc_ocv_lut((uint16_t)(ocv * 1000.0f),
                               (int16_t)(buffer->samples[1].temp_C)) /
                   1000.0f;
      state->soc = fmaxf(0.0f, fminf(state->soc, 1.0f));  // Clamp SOC to [0, 1]
      state->soc_latched = state->soc;
    }
  }

  // TODO: add filtering of measured SoC

  // Discharging, SOC should move only in negative direction
  // if (state->soc < state->soc_latched) {
  //   state->soc_latched = state->soc;
  // }

  return state->soc_latched;
}

static void fuel_gauge_reset_buffer(fuel_gauge_buffer_t* buffer) {
  memset((void*)&buffer, 0, sizeof(*buffer));
}

bool fuel_gauge_feed_buffer(fuel_gauge_buffer_t* buffer,
                            const fuel_gauge_sample_t* sample) {
  fuel_gauge_buffer_state_e state = buffer->buffer_state;
  bool buffer_ready = false;

  // TODO: Accept only exact order of input samples in order to correctly
  // calculate initial ESR, OCV and SoC.
  switch (state) {
    // TODO: Check how long we stay in bootloader mode with low power
    // consumption.

    // 1. sample - first measurement of V, I and Temp. Expect low current < 50mA
    case FG_SAMPLE_INIT: {
      if (sample->current_mA > BAT_FG_CUR_BOOTLOADER_MA) {
        return buffer_ready;
      }

      dummy_load_on(buffer->pulse_timer, BAT_FG_CUR_DUMMY_TIMEOUT_MS);
      state = FG_SAMPLE_INIT_PULSE;
      break;
    }
    // 2. sample - current pulse measurement of V, I and Temp. Expect DUMMY
    // current between 100 and 200 mA (TBD).
    // dTime >= 100 ms.
    // -> Calculation initial ESR, OCV and SoC.
    case FG_SAMPLE_INIT_PULSE: {
      if (((sample->timestamp_ms - buffer->samples[0].timestamp_ms) < 100) ||
          (sample->current_mA < BAT_FG_CUR_BOOTLOADER_DUMMY_MIN_MA) ||
          (sample->current_mA > BAT_FG_CUR_BOOTLOADER_DUMMY_MAX_MA)) {
        return buffer_ready;
      }

      dummy_load_off();

      memcpy((void*)&buffer->sample_boot, (void*)&buffer->samples[0],
             sizeof(buffer->samples[0]));
      state = FG_SAMPLE_INIT_READY;
      break;
    }
    case FG_SAMPLE_INIT_READY: {
      break;
    }
    // Application sample - measurement of V, I and Temp in Application mode.
    // Expect current > 50 mA.
    // dTime >= 1 second.
    case FG_SAMPLE_APP: {
      if (((sample->timestamp_ms -
            buffer->samples[buffer->head_idx].timestamp_ms) < 1000)
          /*|| (sample->current_mA < BAT_FG_CUR_BOOTLOADER_MA)*/) {
        return buffer_ready;
      }

      if (buffer->head_idx == (BAT_FG_SAMPLE_BUF_SIZE - 2)) {
        dummy_load_on(buffer->pulse_timer, BAT_FG_CUR_DUMMY_TIMEOUT_MS);
        state = FG_SAMPLE_APP_PULSE;
      }
      break;
    }
    case FG_SAMPLE_APP_PULSE: {
      // Application mode + Dummy pulse.
      // -> Calculation more accurate ESR, OCV and SoC.
      dummy_load_off();
      state = FG_SAMPLE_APP;
      buffer_ready = true;
      break;
    }
    default:
      fuel_gauge_reset_buffer(buffer);
      return buffer_ready;
  }

  // Store battery data in the buffer
  memcpy((void*)&buffer->samples[buffer->head_idx], (void*)sample,
         sizeof(*sample));
  buffer->head_idx = (buffer->head_idx + 1) % BAT_FG_SAMPLE_BUF_SIZE;

  // switch (state) {
  //   case FG_SAMPLE_INIT: {
  //     break;
  //   }
  //   case FG_SAMPLE_INIT_PULSE: {
  //     break;
  //   }
  //   case FG_SAMPLE_APP: {
  //     break;
  //   }
  //   case FG_SAMPLE_APP_PULSE: {
  //     break;
  //   }
  //   default:
  //     break;
  // }

  return buffer_ready;
}

static float fuel_gauge_calculate_esr(fuel_gauge_buffer_t* buffer) {
  // calculate average of first 10 samples
  float v_avg = 0;
  float i_avg = 0;
  for (uint8_t i = 0; i < BAT_FG_SAMPLE_BUF_SIZE - 1; i++) {
    v_avg += buffer->samples[i].voltage_V;
    i_avg += buffer->samples[i].current_mA;
  }
  v_avg = v_avg / (BAT_FG_SAMPLE_BUF_SIZE - 1);
  i_avg = i_avg / (BAT_FG_SAMPLE_BUF_SIZE - 1);

  // calculate ESR
  return fuel_gauge_rint(
      v_avg, i_avg, buffer->samples[BAT_FG_SAMPLE_BUF_SIZE - 1].voltage_V,
      buffer->samples[BAT_FG_SAMPLE_BUF_SIZE - 1].current_mA);
}

static float fuel_gauge_calculate_nfc_esr(fuel_gauge_buffer_t* buffer) {
  return fuel_gauge_rint(
      buffer->sample_boot.voltage_V, buffer->sample_boot.current_mA,
      buffer->samples[BAT_FG_SAMPLE_BUF_SIZE - 2].voltage_V,
      buffer->samples[BAT_FG_SAMPLE_BUF_SIZE - 2].current_mA);
}

#endif
