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

#include <sys/irq.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <trezor_rtl.h>

#include "../battery.h"
#include "dummy_load.h"
#include "fuel_gauge.h"

#define BAT_FG_SAMPLE_BUF_SIZE 3

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

// Alkaline brownout thresholds. Kept with the chemistry, not the policy.
#define BAT_UNDERVOLT_THR_V 0.8f         // set critical below this
#define BAT_CRITICAL_RECOVERY_SOC 0.02f  // clear critical at/above this SoC

typedef struct {
  float voltage_V;
  float current_mA;
  float temp_C;
  uint32_t timestamp_ms;
} bat_sample_t;

typedef struct {
  bat_sample_t samples[BAT_FG_SAMPLE_BUF_SIZE];
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

  systimer_t* pulse_timer;
  // uint32_t timestamp_init;

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

  fuel_gauge_init(&drv->fg_state);

  if (ts_error(dummy_load_init(drv->pulse_timer))) {
    return TS_ENOMEM;
  }

  drv->fg_locked = false;
  drv->initialized = true;

  return TS_OK;
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

  // TODO: Accept only exact order of input samples in order to correctly
  // calculate initial ESR, OCV and SoC.

  if (drv->sample_buf.head_idx == 0) {
    // TODO: consider read more samples and count average of 1st samples if
    // there is enough time for that.
    // TODO: Check how long we stay in bootloader mode with low power
    // consumption.

    // 1. sample - first measurement of V, I and Temp. Expect low current < 50mA
    if (current_mA > BAT_FG_CUR_BOOTLOADER_MA) {
      return TS_EINVAL;
    }
    dummy_load_on(drv->pulse_timer, BAT_FG_CUR_DUMMY_TIMEOUT_MS);
  } else if (drv->sample_buf.head_idx == 1) {
    // 2. sample - current pulse measurement of V, I and Temp. Expect DUMMY
    // current between 100 and 200 mA (TBD).
    // dTime >= 100 ms.
    // -> Calculation initial ESR, OCV and SoC.
    if (((timestamp_ms - drv->sample_buf.samples[0].timestamp_ms) < 100) ||
        (current_mA < BAT_FG_CUR_BOOTLOADER_DUMMY_MIN_MA) ||
        (current_mA > BAT_FG_CUR_BOOTLOADER_DUMMY_MAX_MA)) {
      return TS_EINVAL;
    }
    dummy_load_off();
  } else if (drv->sample_buf.head_idx == 2) {
    // 3. sample - measurement of V, I and Temp in Application mode. Expect
    // current > 100 mA.
    // dTime >= 2 seconds.
    // -> Calculation more accurate ESR, OCV and SoC.
    if ((timestamp_ms - drv->sample_buf.samples[1].timestamp_ms) < 2000)
      return TS_EINVAL;
  }

  // TODO: enable-nfc flag related ESR can be calculated during Application.
  // In bat_fg_update() function.
  // else if (drv->sample_buf.head_idx == 3) {
  //   // 4. sample - measurement of V, I, Temp in Application mode. Expect
  //   low
  //   // current > 100 mA. dTime = 10 seconds.
  //   // -> Calcualtion precise ESR for enable-nfc flag.
  // }

  // Store battery data in the buffer
  drv->sample_buf.samples[drv->sample_buf.head_idx].voltage_V = voltage_V;
  drv->sample_buf.samples[drv->sample_buf.head_idx].current_mA = current_mA;
  drv->sample_buf.samples[drv->sample_buf.head_idx].temp_C = temp_C;
  drv->sample_buf.samples[drv->sample_buf.head_idx].timestamp_ms = timestamp_ms;
  drv->sample_buf.head_idx++;
  irq_unlock(key);

  return TS_OK;
}

ts_t bat_fg_initial_guess() {
  bat_driver_t* drv = &g_bat_driver;

  if (!drv->initialized) {
    return TS_ENOINIT;
  }

  if (drv->sample_buf.head_idx == 0) {
    // Buffer is empty, no data to process
    return TS_EINVAL;
  }

  irq_key_t key = irq_lock();

  // Calculate ESR and OCV.
  drv->battery_model.bat_esr_init =
      fuel_gauge_rint(drv->sample_buf.samples[0].voltage_V,
                      drv->sample_buf.samples[0].current_mA,
                      drv->sample_buf.samples[1].voltage_V,
                      drv->sample_buf.samples[1].current_mA);
  if (drv->sample_buf.head_idx == 2) {
    drv->battery_model.bat_esr_ocv =
        fuel_gauge_rint(drv->sample_buf.samples[0].voltage_V,
                        drv->sample_buf.samples[0].current_mA,
                        drv->sample_buf.samples[2].voltage_V,
                        drv->sample_buf.samples[2].current_mA);
  }

  fuel_gauge_initial_guess(
      &drv->fg_state, &drv->battery_model, drv->sample_buf.samples[2].voltage_V,
      drv->sample_buf.samples[2].current_mA, drv->sample_buf.samples[2].temp_C);

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
  data->P = 0;

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

  fuel_gauge_update(&drv->fg_state, &drv->battery_model, voltage_V, current_mA,
                    temp_C, dt_ms);

  irq_unlock(key);

  return TS_OK;
}

bool bat_eval_critical(bool currently_critical, float voltage_V,
                       float current_mA, float temp_C) {
  bat_driver_t* drv = &g_bat_driver;
  (void)current_mA;
  (void)temp_C;

  // Set on undervoltage. Voltage is a reliable SoC indicator in the critical
  // region (steep curve), so snap the estimate to empty - keeping the
  // covariance - as bat_fg_set_soc() does.
  if (voltage_V < BAT_UNDERVOLT_THR_V && !currently_critical) {
    bat_fg_set_soc(0.0f, 0.0f);
    return true;
  }

  // Recover only on a genuine SoC rise (recharge). Raw voltage rebounds on
  // relaxation without the cell actually recovering, so a voltage-based clear
  // would falsely un-latch at rest; the persisted SoC also guards boot across
  // hibernation.
  if (drv->fg_state.soc_latched >= BAT_CRITICAL_RECOVERY_SOC) {
    return false;
  }

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
