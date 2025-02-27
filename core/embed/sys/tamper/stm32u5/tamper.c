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

#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systick.h>
#include <sys/tamper.h>

#ifdef KERNEL_MODE

// Fixes a typo in CMSIS Device library for STM32U5
#undef TAMP_CR3_ITAMP7NOER_Msk
#undef TAMP_CR3_ITAMP7NOER
#define TAMP_CR3_ITAMP7NOER_Msk (0x1UL << TAMP_CR3_ITAMP7NOER_Pos)
#define TAMP_CR3_ITAMP7NOER TAMP_CR3_ITAMP7NOER_Msk

// This function replaces calls to universal, but flash-wasting
// functions HAL_RCC_OscConfig and HAL_RCCEx_PeriphCLKConfig.
//
// This is the configuration before the optimization:
// clk_init_def.PeriphClockSelection = RCC_PERIPHCLK_RTC;
// clk_init_def.RTCClockSelection = RCC_RTCCLKSOURCE_LSI (or
// RCC_RTCCLKSOURCE_LSE); HAL_RCCEx_PeriphCLKConfig(&clk_init_def);
static HAL_StatusTypeDef clk_init(uint32_t source) {
  bool pwrclkchanged = false;

  // Enable Power Clock
  if (__HAL_RCC_PWR_IS_CLK_DISABLED()) {
    __HAL_RCC_PWR_CLK_ENABLE();
    pwrclkchanged = true;
  }
  // Enable write access to Backup domain
  SET_BIT(PWR->DBPR, PWR_DBPR_DBP);

  // Wait for Backup domain Write protection disable
  uint32_t deadline = ticks_timeout(RCC_DBP_TIMEOUT_VALUE);

  while (HAL_IS_BIT_CLR(PWR->DBPR, PWR_DBPR_DBP)) {
    if (ticks_expired(deadline)) {
      return HAL_TIMEOUT;
    }
  }
  // Reset the Backup domain only if the RTC Clock source selection is modified
  // from default
  uint32_t bdcr_temp = READ_BIT(RCC->BDCR, RCC_BDCR_RTCSEL);

  if ((bdcr_temp != RCC_RTCCLKSOURCE_NO_CLK) && (bdcr_temp != source)) {
    // Store the content of BDCR register before the reset of Backup Domain
    bdcr_temp = READ_BIT(RCC->BDCR, ~(RCC_BDCR_RTCSEL));
    // RTC Clock selection can be changed only if the Backup Domain is reset
    __HAL_RCC_BACKUPRESET_FORCE();
    __HAL_RCC_BACKUPRESET_RELEASE();
    // Restore the Content of BDCR register
    RCC->BDCR = bdcr_temp;
  }

  // Wait for LSE reactivation if LSE was enabled prior to Backup Domain reset
  if (HAL_IS_BIT_SET(bdcr_temp, RCC_BDCR_LSEON)) {
    deadline = ticks_timeout(RCC_LSE_TIMEOUT_VALUE);

    // Wait till LSE is ready
    while (READ_BIT(RCC->BDCR, RCC_BDCR_LSERDY) == 0U) {
      if (ticks_expired(deadline)) {
        return HAL_TIMEOUT;
      }
    }
  }

  // Apply new RTC clock source selection
  __HAL_RCC_RTC_CONFIG(source);

  // Restore clock configuration if changed
  if (pwrclkchanged) {
    __HAL_RCC_PWR_CLK_DISABLE();
  }
  return HAL_OK;
}

bool tamper_init(void) {
#ifdef USE_LSE
  HAL_StatusTypeDef res = clk_init(RCC_RTCCLKSOURCE_LSE);
#else
  HAL_StatusTypeDef res = clk_init(RCC_RTCCLKSOURCE_LSI);
#endif

  if (res != HAL_OK) {
    return false;
  }

  // Enable RTC peripheral (tampers are part of it)
  __HAL_RCC_RTC_ENABLE();
  __HAL_RCC_RTCAPB_CLK_ENABLE();

  // Clear all pending interrupts
  // They may be some as RTC/TAMP peripherals reside inside the
  // backup voltage domain
  TAMP->SCR = TAMP_SCR_CTAMP2F | TAMP_SCR_CITAMP1F | TAMP_SCR_CITAMP2F |
              TAMP_SCR_CITAMP3F | TAMP_SCR_CITAMP5F | TAMP_SCR_CITAMP6F |
              TAMP_SCR_CITAMP7F | TAMP_SCR_CITAMP8F | TAMP_SCR_CITAMP9F |
              TAMP_SCR_CITAMP11F | TAMP_SCR_CITAMP12F | TAMP_SCR_CITAMP13F;

  NVIC_ClearPendingIRQ(TAMP_IRQn);

  // Enable battery and power monitoring (!@# rework it)
  RCC->AHB3ENR |= RCC_AHB3ENR_PWREN;
  // HAL_PWR_EnableBkUpAccess();
  PWR->BDCR1 |= PWR_BDCR1_MONEN;
  // HAL_PWR_DisableBkUpAccess();

  // // Set external tamper input filter
  TAMP->FLTCR =
      // TAMP_FLTCR_TAMPPUDIS | // disable pre-charge of TAMP_INx pins
      (3 << TAMP_FLTCR_TAMPPRCH_Pos) |  // pre-charge 8 RTCCLK cycles
      (2 << TAMP_FLTCR_TAMPFLT_Pos) |   // activated after 4 same samples
      (7 << TAMP_FLTCR_TAMPFREQ_Pos);   // sampling period RTCCLK / 256 (128Hz)

  // Enable all internal tampers (4th and 10th are intentionally skipped)
  // We select all of them despite some of them are never triggered
  TAMP->CR1 |=
      (TAMP_CR1_ITAMP1E |   // backup domain voltage monitoring
       TAMP_CR1_ITAMP2E |   // temperature monitoring
       TAMP_CR1_ITAMP3E |   // LSE monitoring (LSECSS)
       TAMP_CR1_ITAMP5E |   // RTC calendar overflow
       TAMP_CR1_ITAMP6E |   // JTAG/SWD access when RDP > 0
       TAMP_CR1_ITAMP7E |   // ADC4 analog watchdog monitoring 1
       TAMP_CR1_ITAMP8E |   // Monotonic counter 1 overflow
       TAMP_CR1_ITAMP9E |   // Crypto peripherals fault (SAES, AES, PKA, TRNG)
       TAMP_CR1_ITAMP11E |  // IWDG reset when tamper flag is set
       TAMP_CR1_ITAMP12E |  // ADC4 analog watchdog monitoring 2
       TAMP_CR1_ITAMP13E);  // ADC4 analog watchdog monitoring 3

  // Switch all tampers to the "confirmed" mode
  // => all secrets all deleted when any tamper event is triggered
  TAMP->CR3 = 0;

#ifdef TAMPER_INPUT_2
  // TAMP_IN2 level high
  TAMP->CR2 |= TAMP_CR2_TAMP2TRG;
#endif

  // Enable all interrupts for all internal tampers
  TAMP->IER = TAMP_IER_TAMP2IE | TAMP_IER_ITAMP1IE | TAMP_IER_ITAMP2IE |
              TAMP_IER_ITAMP3IE | TAMP_IER_ITAMP5IE | TAMP_IER_ITAMP6IE |
              TAMP_IER_ITAMP7IE | TAMP_IER_ITAMP8IE | TAMP_IER_ITAMP9IE |
              TAMP_IER_ITAMP11IE | TAMP_IER_ITAMP12IE | TAMP_IER_ITAMP13IE;

  // Enable TAMP interrupt at NVIC controller
  NVIC_SetPriority(TAMP_IRQn, IRQ_PRI_HIGHEST);
  NVIC_EnableIRQ(TAMP_IRQn);

  return true;
}

uint8_t tamper_external_read(void) {
  uint8_t val = 0;

#ifdef TAMPER_INPUT_2
  GPIO_InitTypeDef gpio = {0};
  gpio.Mode = GPIO_MODE_INPUT;
  gpio.Pull = GPIO_PULLUP;
  gpio.Pin = GPIO_PIN_0;
  gpio.Speed = GPIO_SPEED_LOW;
  HAL_GPIO_Init(GPIOA, &gpio);

  systick_delay_us(1);

  val |= GPIO_PIN_SET == HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0) ? 2 : 0;

  HAL_GPIO_DeInit(GPIOA, GPIO_PIN_0);
#endif

  return val;
}

void tamper_external_enable(void) {
  // Enable external tampers
#ifdef TAMPER_INPUT_2
  TAMP->CR1 |= TAMP_CR1_TAMP2E;
#endif
}

// Interrupt handle for all tamper events
// It displays an error message
void TAMP_IRQHandler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);

  // Disable external tamper, as its level detected
  // and it would trigger again. We don't need it until reset.
#ifdef TAMPER_INPUT_2
  TAMP->CR1 &= ~TAMP_CR1_TAMP2E;
#endif

  uint32_t sr = TAMP->SR;
  TAMP->SCR = sr;

#ifdef BOARDLOADER
  error_shutdown_ex("INTERNAL TAMPER", NULL, NULL);
#else
  const char* reason = "UNKNOWN";
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
  error_shutdown_ex("INTERNAL TAMPER", reason, NULL);
#endif
}

#endif  // KERNEL_MODE
