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

#include <irq.h>
#include <supervise.h>
#include <tamper.h>
#include STM32_HAL_H

// Fixes a typo in CMSIS Device library for STM32U5
#undef TAMP_CR3_ITAMP7NOER_Msk
#undef TAMP_CR3_ITAMP7NOER
#define TAMP_CR3_ITAMP7NOER_Msk (0x1UL << TAMP_CR3_ITAMP7NOER_Pos)
#define TAMP_CR3_ITAMP7NOER TAMP_CR3_ITAMP7NOER_Msk

// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
// Temporary solution for STM32U5A9 Discovery Board experiments
// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

void tamper_init() {
  RCC_PeriphCLKInitTypeDef clk_init_def = {0};
  RCC_OscInitTypeDef osc_init_def = {0};

  // Enable LSI clock
  osc_init_def.OscillatorType = RCC_OSCILLATORTYPE_LSI;
  osc_init_def.LSIState = RCC_LSI_ON;
  HAL_RCC_OscConfig(&osc_init_def);

  // Select RTC peripheral clock source
  clk_init_def.PeriphClockSelection = RCC_PERIPHCLK_RTC;
  clk_init_def.RTCClockSelection = RCC_RTCCLKSOURCE_LSI;
  HAL_RCCEx_PeriphCLKConfig(&clk_init_def);

  // Enable RTC peripheral (tampers are part of it)
  __HAL_RCC_RTC_ENABLE();
  __HAL_RCC_RTCAPB_CLK_ENABLE();

  // Clear all pending interrupts
  // They may be some as RTC/TAMP peripherals resides inside the
  // backup voltage domain
  TAMP->SCR = TAMP_SCR_CTAMP2F | TAMP_SCR_CITAMP1F | TAMP_SCR_CITAMP2F |
              TAMP_SCR_CITAMP3F | TAMP_SCR_CITAMP5F | TAMP_SCR_CITAMP6F |
              TAMP_SCR_CITAMP7F | TAMP_SCR_CITAMP8F | TAMP_SCR_CITAMP9F |
              TAMP_SCR_CITAMP11F | TAMP_SCR_CITAMP12F | TAMP_SCR_CITAMP13F;

  NVIC_ClearPendingIRQ(TAMP_IRQn);

  // Enable battery and power monitoring (!@# rework it)
  RCC->AHB3ENR |= RCC_AHB3ENR_PWREN;
  // HAL_PWR_EnableBkUpAccess();
  HAL_PWREx_EnableMonitoring();
  // HAL_PWR_DisableBkUpAccess();

  // Enable all internal tampers (4th and 10th are intentionally skipped)
  // Enable TAMP_IN2 external input (PA0)
  // We select all of them despite some of them are never triggered
  TAMP->CR1 =
      TAMP_CR1_TAMP2E |    // external TAMP_IN2
      TAMP_CR1_ITAMP1E |   // backup domain voltage monitoring
      TAMP_CR1_ITAMP2E |   // temperature monitoring
      TAMP_CR1_ITAMP3E |   // LSE monitoring (LSECSS)
      TAMP_CR1_ITAMP5E |   // RTC calendar overflow
      TAMP_CR1_ITAMP6E |   // JTAG/SWD access when RDP > 0
      TAMP_CR1_ITAMP7E |   // ADC4 analog watchdog monitoring 1
      TAMP_CR1_ITAMP8E |   // Monotonic counter 1 overflow
      TAMP_CR1_ITAMP9E |   // Crypto periherals fault (SAES, AES, PKA, TRNG)
      TAMP_CR1_ITAMP11E |  // IWDG reset when tamper flag is set
      TAMP_CR1_ITAMP12E |  // ADC4 analog watchdog monitoring 2
      TAMP_CR1_ITAMP13E;   // ADC4 analog watchdog monitoring 3

  // Switch all internal tampers to the "confirmed" mode
  // => all secrets all deleted when any tamper event is triggered
  TAMP->CR3 = 0;

  // Setup external tampers
  // TAMP_IN2 active low, "confirmed" mode
  TAMP->CR2 = 0;
  // TAMP_CR2_TAMP2TRG;

  // Set external tamper input filter
  TAMP->FLTCR =
      // TAMP_FLTCR_TAMPPUDIS | // disable pre-charge of TAMP_INx pins
      (3 << TAMP_FLTCR_TAMPPRCH_Pos) |  // pre-charge 8 RTCCLK cycles
      (2 << TAMP_FLTCR_TAMPFLT_Pos) |   // activated after 4 same samples
      (7 << TAMP_FLTCR_TAMPFREQ_Pos);   // sampling period RTCCLK / 256 (128Hz)

  // Enable all interrupts for all internal tampers
  TAMP->IER = TAMP_IER_TAMP2IE | TAMP_IER_ITAMP1IE | TAMP_IER_ITAMP2IE |
              TAMP_IER_ITAMP3IE | TAMP_IER_ITAMP5IE | TAMP_IER_ITAMP6IE |
              TAMP_IER_ITAMP7IE | TAMP_IER_ITAMP8IE | TAMP_IER_ITAMP9IE |
              TAMP_IER_ITAMP11IE | TAMP_IER_ITAMP12IE | TAMP_IER_ITAMP13IE;

  // Enable TAMP interrupt at NVIC controller
  NVIC_SetPriority(TAMP_IRQn, IRQ_PRI_TAMP);
  NVIC_EnableIRQ(TAMP_IRQn);

  // svc_setpriority(TAMP_IRQn, IRQ_PRI_TAMP);
  // svc_enableIRQ(TAMP_IRQn);
}

// Interrupt handle for all tamper events
// It displays an error message
void TAMP_IRQHandler(void) {
  const char* reason = "UNKNOWN";

  uint32_t sr = TAMP->SR;

  if (sr & TAMP_SR_TAMP1F) {
    reason = "INPUT1";
  } else if (sr & TAMP_SR_TAMP2F) {
    reason = "INPUT2";
  } else if (sr & TAMP_SR_ITAMP1F) {
    reason = "VOLTAGE";
  } else if (sr & TAMP_SR_ITAMP2F) {
    reason = "TEMPERATURE";
  } else if (sr & TAMP_SR_ITAMP3F) {
    reason = "LSE CLOCK";
  } else if (sr & TAMP_SR_ITAMP5F) {
    reason = "RTC OVERFLOW";
  } else if (sr & TAMP_SR_ITAMP6F) {
    reason = "SWD ACCESS";
  } else if (sr & TAMP_SR_ITAMP7F) {
    reason = "ANALOG WDG1";
  } else if (sr & TAMP_SR_ITAMP8F) {
    reason = "MONO COUNTER";
  } else if (sr & TAMP_SR_ITAMP9F) {
    reason = "CRYPTO ERROR";
  } else if (sr & TAMP_SR_ITAMP11F) {
    reason = "IWDG";
  } else if (sr & TAMP_SR_ITAMP12F) {
    reason = "ANALOG WDG2";
  } else if (sr & TAMP_SR_ITAMP13F) {
    reason = "ANALOG WDG3";
  }

  error_shutdown("INTERNAL TAMPER", reason);
}

// Triggers ITAMP5 by overflowing RTC date/time
static void tamper_test_rtc_overflow(void) {
  RTC_HandleTypeDef hrtc;
  RTC_DateTypeDef date = {0};
  RTC_TimeTypeDef time = {0};

  // Initialize RTC and select BCD format for date & time
  hrtc.Instance = RTC;
  hrtc.Init.HourFormat = RTC_HOURFORMAT_24;
  hrtc.Init.AsynchPrediv = 127;
  hrtc.Init.SynchPrediv = 255;
  hrtc.Init.OutPut = RTC_OUTPUT_DISABLE;
  hrtc.Init.OutPutRemap = RTC_OUTPUT_REMAP_NONE;
  hrtc.Init.OutPutPolarity = RTC_OUTPUT_POLARITY_HIGH;
  hrtc.Init.OutPutType = RTC_OUTPUT_TYPE_OPENDRAIN;
  hrtc.Init.OutPutPullUp = RTC_OUTPUT_PULLUP_NONE;
  hrtc.Init.BinMode = RTC_BINARY_NONE;
  HAL_RTC_Init(&hrtc);

  // set date 99/12/31
  date.Year = 0x99;
  date.Month = 0x12;
  date.Date = 0x31;
  date.WeekDay = 0x00;
  HAL_RTC_SetDate(&hrtc, &date, RTC_FORMAT_BCD);

  // set time 23:59:50
  time.Hours = 0x23;
  time.Minutes = 0x59;
  time.Seconds = 0x50;
  HAL_RTC_SetTime(&hrtc, &time, RTC_FORMAT_BCD);
}

// Triggers ITAMP8  by overflowing monotonic counter
static void tamper_test_counter_overflow(void) {
  for (uint32_t i = 0; i < UINT32_MAX; i++) {
    TAMP->COUNTR = 0;
  }
  TAMP->COUNTR = 0;
}

void tamper_test(uint32_t tamper_bit) {
  if (tamper_bit & TAMP_CR1_ITAMP5E) {
    tamper_test_rtc_overflow();
  } else if (tamper_bit & TAMP_CR1_ITAMP8E) {
    tamper_test_counter_overflow();
  }
}
