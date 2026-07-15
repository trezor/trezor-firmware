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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/pmic.h>
#include <sys/mpu.h>
#include <sys/systick.h>

#ifdef KERNEL_MODE

// Minimal PMIC driver for boards whose only power-management hardware is a
// GPIO power latch (soft power switch) on the PWR_ON pin, plus a single-cell
// battery voltage measurement on an ADC input.
//
// On boot the device is powered only while the user holds the power button;
// pmic_init() drives PWR_ON high to keep the supply enabled after the button
// is released. pmic_enter_shipmode() releases PWR_ON, cutting the supply and
// turning the device off - the latch's equivalent of ship mode.
//
// pmic_measure*() reads the battery cell voltage on BATTERY_MEAS (ADC). The
// measurement enable (BATTERY_MEAS_ENABLE) is asserted once in init and left on
// for the whole run, because pmic_measure_sync() is called from the systick
// handler (via the scheduler) where we can't gate-and-settle with a delay.
// There is no charger, fuel gauge or temperature sensor, so those report
// fields stay zero.

static ADC_HandleTypeDef g_battery_adc = {0};
static bool g_battery_adc_ready = false;
// Factory VREFINT calibration value, cached from the OTP/system-memory region
// at init (that region isn't mapped by the MPU mode active during measurement).
static uint16_t g_vrefint_cal = 0;

// Measurement-enable (EN1) polarity. Define BATTERY_MEAS_ENABLE_ACTIVE_LOW in
// the board header when the switch (Q1) is a P-channel / active-low device.
#ifdef BATTERY_MEAS_ENABLE_ACTIVE_LOW
#define BATTERY_MEAS_ENABLE_ON GPIO_PIN_RESET
#define BATTERY_MEAS_ENABLE_OFF GPIO_PIN_SET
#else
#define BATTERY_MEAS_ENABLE_ON GPIO_PIN_SET
#define BATTERY_MEAS_ENABLE_OFF GPIO_PIN_RESET
#endif

static bool battery_meas_init(void) {
  // Validate the VDDA independent analog supply (ASV) so the ADC analog core
  // works (otherwise ADRDY never asserts and calibration fails with an internal
  // error). The PWR clock must be enabled for the SVMCR write to take effect.
  // NOTE: PWR_SVMCR is a secure register, so this only works while this driver
  // runs in the secure world (e.g. prodtest). In the non-secure firmware/kernel
  // split it must instead be done in secure code - to be revisited.
  __HAL_RCC_PWR_CLK_ENABLE();
  PWR->SVMCR |= PWR_SVMCR_ASV;

  // Select the ADC/DAC kernel clock source = HSI (16 MHz, always enabled from
  // startup, safely within the ADC input-clock range). Done with a direct
  // register write to avoid depending on HAL_RCCEx_* (rcc_ex.c is only
  // compiled in secure_mode).
  MODIFY_REG(RCC->CCIPR3, RCC_CCIPR3_ADCDACSEL, RCC_ADCDACCLKSOURCE_HSI);

  BATTERY_MEAS_ADC_CLK_EN();

  // Measurement enable pin (EN1): push-pull output, default low (path gated
  // off so the divider draws no current until we measure).
  BATTERY_MEAS_ENABLE_CLK_EN();
  HAL_GPIO_WritePin(BATTERY_MEAS_ENABLE_PORT, BATTERY_MEAS_ENABLE_PIN,
                    BATTERY_MEAS_ENABLE_OFF);
  GPIO_InitTypeDef gpio = {0};
  gpio.Mode = GPIO_MODE_OUTPUT_PP;
  gpio.Pull = GPIO_NOPULL;
  gpio.Speed = GPIO_SPEED_FREQ_LOW;
  gpio.Pin = BATTERY_MEAS_ENABLE_PIN;
  HAL_GPIO_Init(BATTERY_MEAS_ENABLE_PORT, &gpio);

  // Measurement input (MEAS1): analog.
  BATTERY_MEAS_CLK_EN();
  gpio.Mode = GPIO_MODE_ANALOG;
  gpio.Pull = GPIO_NOPULL;
  gpio.Pin = BATTERY_MEAS_PIN;
  HAL_GPIO_Init(BATTERY_MEAS_PORT, &gpio);

  g_battery_adc.Instance = BATTERY_MEAS_ADC;
  g_battery_adc.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV1;
  // 14-bit: the STM32U5 ADC is natively 14-bit and the factory VREFINT_CAL is
  // stored at 14-bit, so matching resolution keeps the VDDA calculation
  // correct.
  g_battery_adc.Init.Resolution = ADC_RESOLUTION_14B;
  g_battery_adc.Init.ScanConvMode = ADC_SCAN_DISABLE;
  g_battery_adc.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
  g_battery_adc.Init.LowPowerAutoWait = DISABLE;
  g_battery_adc.Init.ContinuousConvMode = DISABLE;
  g_battery_adc.Init.NbrOfConversion = 1;
  g_battery_adc.Init.DiscontinuousConvMode = DISABLE;
  g_battery_adc.Init.ExternalTrigConv = ADC_SOFTWARE_START;
  g_battery_adc.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
  g_battery_adc.Init.DMAContinuousRequests = DISABLE;
  g_battery_adc.Init.Overrun = ADC_OVR_DATA_OVERWRITTEN;
  g_battery_adc.Init.OversamplingMode = DISABLE;
  if (HAL_ADC_Init(&g_battery_adc) != HAL_OK) {
    return false;
  }

  // Give the ADC internal voltage regulator time to stabilize before
  // calibration. HAL_ADC_Init already waits, but its delay is derived from
  // SystemCoreClock; this explicit delay is robust regardless of that value.
  systick_delay_ms(1);

  ADC_ChannelConfTypeDef ch = {0};
  ch.Channel = BATTERY_MEAS_ADC_CHANNEL;
  ch.Rank = ADC_REGULAR_RANK_1;
  ch.SamplingTime = ADC_SAMPLETIME_391CYCLES;
  ch.SingleDiff = ADC_SINGLE_ENDED;
  ch.OffsetNumber = ADC_OFFSET_NONE;
  ch.Offset = 0;
  if (HAL_ADC_ConfigChannel(&g_battery_adc, &ch) != HAL_OK) {
    return false;
  }

  if (HAL_ADCEx_Calibration_Start(&g_battery_adc, ADC_CALIB_OFFSET,
                                  ADC_SINGLE_ENDED) != HAL_OK) {
    return false;
  }

  // Enable the internal VREFINT channel so each measurement can derive the
  // actual VDDA (VREF+) and scale readings accordingly, instead of assuming a
  // fixed 3.3 V - important because the supply rail can sag well below 3.3 V.
  LL_ADC_SetCommonPathInternalCh(
      __LL_ADC_COMMON_INSTANCE(g_battery_adc.Instance),
      LL_ADC_PATH_INTERNAL_VREFINT);
  systick_delay_ms(1);  // VREFINT startup time

  // Cache the factory VREFINT calibration. It lives in the OTP/system-memory
  // region (0x0BFA07A5), which is only mapped in MPU_MODE_OTP - so read it here
  // (switching the MPU briefly) rather than dereferencing it during a
  // measurement, where the active MPU mode would fault on that address.
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);
  g_vrefint_cal = *VREFINT_CAL_ADDR;
  mpu_restore(mpu_mode);

  // Enable the measurement path for the whole run (see header note).
  HAL_GPIO_WritePin(BATTERY_MEAS_ENABLE_PORT, BATTERY_MEAS_ENABLE_PIN,
                    BATTERY_MEAS_ENABLE_ON);

  return true;
}

bool pmic_init(void) {
  PWR_ON_CLK_EN();

  // Drive the output data register high first, so the pin latches power the
  // moment it is switched to push-pull output mode (avoids a glitch that could
  // briefly release the latch).
  HAL_GPIO_WritePin(PWR_ON_PORT, PWR_ON_PIN, GPIO_PIN_SET);

  GPIO_InitTypeDef GPIO_InitStructure = {0};
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure.Pin = PWR_ON_PIN;
  HAL_GPIO_Init(PWR_ON_PORT, &GPIO_InitStructure);

  g_battery_adc_ready = battery_meas_init();

  return true;
}

void pmic_deinit(void) {
  // Intentionally leave the latch engaged so the device stays powered.
}

bool pmic_enter_shipmode(void) {
  // Release the latch to cut the power supply and turn the device off.
  HAL_GPIO_WritePin(PWR_ON_PORT, PWR_ON_PIN, GPIO_PIN_RESET);
  return true;
}

uint8_t pmic_restart_cause(void) { return 0; }

bool pmic_suspend(void) { return true; }
bool pmic_resume(void) { return true; }
bool pmic_is_suspended(void) { return false; }

// Runs a single conversion on the given channel and returns the raw value.
static bool adc_read_channel(uint32_t channel, uint32_t sampling_time,
                             uint32_t* out_raw) {
  ADC_ChannelConfTypeDef ch = {0};
  ch.Channel = channel;
  ch.Rank = ADC_REGULAR_RANK_1;
  ch.SamplingTime = sampling_time;
  ch.SingleDiff = ADC_SINGLE_ENDED;
  ch.OffsetNumber = ADC_OFFSET_NONE;
  ch.Offset = 0;
  if (HAL_ADC_ConfigChannel(&g_battery_adc, &ch) != HAL_OK) {
    return false;
  }
  bool ok = false;
  if (HAL_ADC_Start(&g_battery_adc) == HAL_OK) {
    if (HAL_ADC_PollForConversion(&g_battery_adc, 10) == HAL_OK) {
      *out_raw = HAL_ADC_GetValue(&g_battery_adc);
      ok = true;
    }
  }
  HAL_ADC_Stop(&g_battery_adc);
  return ok;
}

bool pmic_measure_sync(pmic_report_t* report) {
  if (report == NULL) {
    return false;
  }
  memset(report, 0, sizeof(*report));

  if (!g_battery_adc_ready) {
    return false;
  }

  // Read the battery input, then VREFINT, so we can compute the true VDDA
  // (VREF+) and scale without assuming 3.3 V.
  uint32_t bat_raw = 0;
  uint32_t vref_raw = 0;
  if (!adc_read_channel(BATTERY_MEAS_ADC_CHANNEL, ADC_SAMPLETIME_391CYCLES,
                        &bat_raw) ||
      !adc_read_channel(ADC_CHANNEL_VREFINT, ADC_SAMPLETIME_814CYCLES,
                        &vref_raw)) {
    return false;
  }
  if (vref_raw == 0 || g_vrefint_cal == 0) {
    return false;
  }

  // Actual analog supply voltage from VREFINT using the cached factory
  // calibration: VDDA = VREFINT_CAL_VREF * VREFINT_CAL / VREFINT_measured.
  // Then the ADC input voltage, then the board divider ratio for the cell.
  uint32_t vdda_mv = (VREFINT_CAL_VREF * (uint32_t)g_vrefint_cal) / vref_raw;
  uint32_t adc_mv = __LL_ADC_CALC_DATA_TO_VOLTAGE(
      g_battery_adc.Instance, vdda_mv, bat_raw, LL_ADC_RESOLUTION_14B);
  uint32_t cell_mv =
      adc_mv * BATTERY_MEAS_DIVIDER_NUM / BATTERY_MEAS_DIVIDER_DEN;

  report->vbat = (float)cell_mv / 1000.0f;
  // No dedicated system-rail sense; report the measured analog supply (VDDA).
  report->vsys = (float)vdda_mv / 1000.0f;
  return true;
}

bool pmic_measure(pmic_report_callback_t callback, void* context) {
  pmic_report_t report = {0};
  bool ok = pmic_measure_sync(&report);
  if (ok && callback != NULL) {
    callback(context, &report);
  }
  return ok;
}

bool pmic_set_charging(bool enable) {
  (void)enable;
  return false;
}

bool pmic_set_charging_limit(int i_charge) {
  (void)i_charge;
  return false;
}

int pmic_get_charging_limit(void) { return 0; }

bool pmic_set_buck_mode(pmic_buck_mode_t buck_mode) {
  (void)buck_mode;
  return false;
}

bool pmic_clear_charger_errors(void) { return false; }

#endif  // KERNEL_MODE
