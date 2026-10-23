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
#include <sys/irq.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <trezor_rtl.h>

#include "../battery.h"
#include "dummy_load.h"
#include "fuel_gauge.h"

#ifndef NAN
#error "Missing definition of NaN !!"
#endif

// Alkaline brownout thresholds. Kept with the chemistry, not the policy.
#define BAT_UNDERVOLT_THR_V 0.8f         // set critical below this
#define BAT_CRITICAL_RECOVERY_SOC 0.02f  // clear critical at/above this SoC

typedef struct {
  bool initialized;

  // Fuel gauge state initialized and locked, could be updated based on battery
  // measurements
  bool fg_locked;

  fuel_gauge_state_t fg_state;
  fuel_gauge_buffer_t sample_buf;
  battery_model_t battery_model;

} bat_driver_t;

bat_driver_t g_bat_driver = {
    .initialized = false,
};

ts_t bat_init(void) {
  bat_driver_t* drv = &g_bat_driver;

  if (drv->initialized) {
    return TS_OK;  // Already initialized
  }
  memset(drv, 0, sizeof(bat_driver_t));

  fuel_gauge_init(&drv->fg_state, &drv->sample_buf);

  if (ts_error(dummy_load_init(drv->sample_buf.pulse_timer))) {
    return TS_ENOMEM;
  }

  drv->battery_model.bat_esr_nfc = NAN;
  drv->fg_locked = false;
  drv->initialized = true;

  return TS_OK;
}

ts_t bat_fg_recovery(float soc, float P, float voltage_V, float current_mA) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  // needed for ESR(nfc) calculation
  drv->sample_buf.sample_boot.voltage_V = voltage_V;
  drv->sample_buf.sample_boot.current_mA = current_mA;
  drv->sample_buf.sample_boot.timestamp_ms = systick_ms();
  drv->sample_buf.buffer_state = FG_SAMPLE_APP;

  return bat_fg_set_soc(soc, P);
}

ts_t bat_fg_set_soc(float soc, float P) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  fuel_gauge_set_soc(&drv->fg_state, soc);

  drv->fg_locked = true;

  return TS_OK;
}

ts_t bat_fg_feed_sample(float voltage_V, float current_mA, float temp_C) {
  bat_driver_t* drv = &g_bat_driver;
  uint32_t timestamp_ms = systick_ms();

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  irq_key_t key = irq_lock();

  if (drv->sample_buf.head_idx >= BAT_FG_SAMPLE_BUF_SIZE) {
    return TS_ENOMEM;  // Buffer is full, cannot feed more samples
  }

  const fuel_gauge_sample_t sample = {.current_mA = current_mA,
                                      .voltage_V = voltage_V,
                                      .temp_C = temp_C,
                                      .timestamp_ms = timestamp_ms};
  fuel_gauge_feed_buffer(&drv->sample_buf, &sample);

  irq_unlock(key);

  return TS_OK;
}

ts_t bat_fg_initial_guess() {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  if (drv->sample_buf.buffer_state >= FG_SAMPLE_INIT_READY) {
    // Buffer is not ready, no data to process
    return TS_EINVAL;
  }

  irq_key_t key = irq_lock();

  fuel_gauge_initial_guess(&drv->fg_state, &drv->battery_model,
                           &drv->sample_buf);
  drv->sample_buf.buffer_state = FG_SAMPLE_APP;

  irq_unlock(key);

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
  data->P = 0.0f;
  data->voltage_V = drv->sample_buf.sample_boot.voltage_V;
  data->current_mA = drv->sample_buf.sample_boot.current_mA;

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

  irq_key_t key = irq_lock();

  const fuel_gauge_sample_t sample = {.current_mA = current_mA,
                                      .voltage_V = voltage_V,
                                      .temp_C = temp_C,
                                      .timestamp_ms = systick_ms()};
  fuel_gauge_update(&drv->fg_state, &drv->battery_model, &drv->sample_buf,
                    &sample);

  irq_unlock(key);

  return TS_OK;
}

bool bat_eval_critical(bool currently_critical, float voltage_V,
                       float current_mA, float temp_C) {
  (void)voltage_V;
  (void)current_mA;
  (void)temp_C;
  // TODO: implement this function

  return currently_critical;
}

float bat_meas_to_ocv(float voltage_V, float current_mA, float temp_C) {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return 0.0f;
  }

  return fuel_gauge_meas_to_ocv(drv->battery_model.bat_esr_ocv, voltage_V,
                                current_mA, temp_C);
}

ts_t bat_fg_compensate_soc(float* soc, uint32_t elapsed_s,
                           float avg_bat_current_mA, float avg_temp_C) {
  // Function not implemented for alkaline battery model, return TS_ENOEN
  (void)soc;
  (void)elapsed_s;
  (void)avg_bat_current_mA;
  (void)avg_temp_C;
  return TS_ENOEN;
}

float bat_fetch_cycle_increment(void) {
  // Function not implemented for alkaline battery model, return 0.0f
  return 0.0f;
}

float bat_soc_to_ocv(float soc, float temp_C, bool discharging_mode) {
  // Funtion not implemented for alkaline battery model, return 0.0f
  (void)soc;
  (void)temp_C;
  (void)discharging_mode;
  return 0.0f;
}

#endif
