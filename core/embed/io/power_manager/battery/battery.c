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

#include <trezor_rtl.h>

#include "battery.h"
#include "battery_model.h"
#include "fuel_gauge.h"
#include "math.h"

typedef struct {
  float voltage_V;
  float current_mA;
  float temp_C;
} bat_sample_t;

typedef struct {
  bat_sample_t samples[BAT_FG_SAMPLE_BUF_SIZE];
  uint8_t tail_idx;
  uint8_t head_idx;
} bat_sample_buffer_t;

typedef struct {
  bool initialized;

  // Fuel gauge state initialized and locked, could be updated based on battery
  // measurements
  bool fg_locked;

  fuel_gauge_state_t fg_state;
  battery_model_t battery_model;
  bat_sample_buffer_t sample_buf;

  float cycle_counter;

} bat_driver_t;

bat_driver_t g_bat_driver = {
    .initialized = false,
};

void bat_init(void) {
  bat_driver_t* drv = &g_bat_driver;

  if (drv->initialized) {
    return;  // Already initialized
  }
  memset(drv, 0, sizeof(bat_driver_t));

  battery_model_init(&drv->battery_model);
  fuel_gauge_init(&drv->fg_state);

  drv->fg_locked = false;
  drv->initialized = true;
}

ts_t bat_fg_set_soc(float soc, float P) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  fuel_gauge_set_soc(&drv->fg_state, soc, P);

  drv->fg_locked = true;

  return TS_OK;
}

ts_t bat_fg_feed_sample(float voltage_V, float current_mA, float temp_C) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  // Store battery data in the buffer
  drv->sample_buf.samples[drv->sample_buf.head_idx].voltage_V = voltage_V;
  drv->sample_buf.samples[drv->sample_buf.head_idx].current_mA = current_mA;
  drv->sample_buf.samples[drv->sample_buf.head_idx].temp_C = temp_C;

  // Update head index
  drv->sample_buf.head_idx++;
  if (drv->sample_buf.head_idx >= BAT_FG_SAMPLE_BUF_SIZE) {
    drv->sample_buf.head_idx = 0;
  }

  // Check if the buffer is full
  if (drv->sample_buf.head_idx == drv->sample_buf.tail_idx) {
    // Buffer is full, move tail index forward
    drv->sample_buf.tail_idx++;
    if (drv->sample_buf.tail_idx >= BAT_FG_SAMPLE_BUF_SIZE) {
      drv->sample_buf.tail_idx = 0;
    }
  }

  return TS_OK;
}

ts_t bat_fg_initial_guess() {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  if (drv->sample_buf.head_idx == drv->sample_buf.tail_idx) {
    // Buffer is empty, no data to process
    return TS_EINVAL;
  }

  // Calculate average voltage, current and temperature from the sampling
  // buffer and run the fuel gauge initial guess
  uint8_t buf_idx = drv->sample_buf.tail_idx;
  uint8_t samples_cnt = 0;
  float vbat_avg = 0.0f;
  float ibat_avg = 0.0f;
  float ntc_temp_avg = 0.0f;
  while (drv->sample_buf.head_idx != buf_idx) {
    vbat_avg += drv->sample_buf.samples[buf_idx].voltage_V;
    ibat_avg += drv->sample_buf.samples[buf_idx].current_mA;
    ntc_temp_avg += drv->sample_buf.samples[buf_idx].temp_C;
    buf_idx++;
    if (buf_idx >= BAT_FG_SAMPLE_BUF_SIZE) {
      buf_idx = 0;
    }

    samples_cnt++;
  }

  // Calculate average values
  vbat_avg /= samples_cnt;
  ibat_avg /= samples_cnt;
  ntc_temp_avg /= samples_cnt;

  fuel_gauge_initial_guess(&drv->fg_state, &drv->battery_model, vbat_avg,
                           ibat_avg, ntc_temp_avg);

  drv->fg_locked = true;

  return TS_OK;
}

bool bat_fg_is_locked(void) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return false;
  }

  return drv->fg_locked;
}

ts_t bat_fg_get_state(bat_fg_state_t* data) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  if (data == NULL) {
    return TS_EINVAL;
  }

  data->soc = drv->fg_state.soc;
  data->soc_latched = drv->fg_state.soc_latched;
  data->P = drv->fg_state.P;

  return TS_OK;
}

ts_t bat_fg_update(uint32_t dt_ms, float voltage_V, float current_mA,
                   float temp_C) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }
  if (!drv->fg_locked) {
    return TS_EINVAL;
  }

  drv->cycle_counter += (fabsf(current_mA) * ((float)dt_ms / 3600000.0f)) /
                        (2 * battery_total_capacity(&drv->battery_model, 25.0f,
                                                    current_mA >= 0.0f));

  fuel_gauge_update(&drv->fg_state, &drv->battery_model, dt_ms, voltage_V,
                    current_mA, temp_C);

  return TS_OK;
}

ts_t bat_fg_compensate_soc(float* soc, uint32_t elapsed_s,
                           float avg_bat_current_mA, float avg_temp_C) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  if (!drv->fg_locked) {
    return TS_EINVAL;
  }

  float compensation_mah = ((avg_bat_current_mA)*elapsed_s) / 3600.0f;
  bool discharging_mode = avg_bat_current_mA >= 0.0f;
  *soc -=
      (compensation_mah / battery_total_capacity(&drv->battery_model,
                                                 avg_temp_C, discharging_mode));

  return TS_OK;
}

float bat_fetch_cycle_increment(void) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return 0.0f;
  }

  float cycle_increment = (float)((uint16_t)drv->cycle_counter);
  drv->cycle_counter = 0.0f;
  return cycle_increment;
}

float bat_soc_to_ocv(float soc, float temp_C, bool discharging_mode) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return 0.0f;
  }

  return battery_ocv(&drv->battery_model, soc, temp_C, discharging_mode);
}

float bat_meas_to_ocv(float voltage_V, float current_mA, float temp_C) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return 0.0f;
  }

  return battery_meas_to_ocv(&drv->battery_model, voltage_V, current_mA,
                             temp_C);
}

#endif
