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
#include <sys/tamper.h>

#ifdef KERNEL_MODE

// Fixes a typo in CMSIS Device library for STM32U5
#undef TAMP_CR3_ITAMP7NOER_Msk
#undef TAMP_CR3_ITAMP7NOER
#define TAMP_CR3_ITAMP7NOER_Msk (0x1UL << TAMP_CR3_ITAMP7NOER_Pos)
#define TAMP_CR3_ITAMP7NOER TAMP_CR3_ITAMP7NOER_Msk

/*
 * This function replaces calls to universal, but flash-wasting
 * functions HAL_RCC_OscConfig and HAL_RCCEx_PeriphCLKConfig.
 *
 * This is the configuration before the optimization:
 *  osc_init_def.OscillatorType = RCC_OSCILLATORTYPE_LSI;
 *  osc_init_def.LSIState = RCC_LSI_ON;
 *  HAL_RCC_OscConfig(&osc_init_def);
 *
 *  clk_init_def.PeriphClockSelection = RCC_PERIPHCLK_RTC;
 *  clk_init_def.RTCClockSelection = RCC_RTCCLKSOURCE_LSI;
 *  HAL_RCCEx_PeriphCLKConfig(&clk_init_def);
 */
HAL_StatusTypeDef lsi_init(void) {
  uint32_t tickstart = 0U;

  FlagStatus pwrclkchanged = RESET;

  /* Update LSI configuration in Backup Domain control register    */
  /* Requires to enable write access to Backup Domain of necessary */
  if (__HAL_RCC_PWR_IS_CLK_DISABLED()) {
    __HAL_RCC_PWR_CLK_ENABLE();
    pwrclkchanged = SET;
  }

  if (HAL_IS_BIT_CLR(PWR->DBPR, PWR_DBPR_DBP)) {
    /* Enable write access to Backup domain */
    SET_BIT(PWR->DBPR, PWR_DBPR_DBP);

    /* Wait for Backup domain Write protection disable */
    tickstart = HAL_GetTick();

    while (HAL_IS_BIT_CLR(PWR->DBPR, PWR_DBPR_DBP)) {
      if ((HAL_GetTick() - tickstart) > RCC_DBP_TIMEOUT_VALUE) {
        /* Restore clock configuration if changed */
        if (pwrclkchanged == SET) {
          __HAL_RCC_PWR_CLK_DISABLE();
        }
        return HAL_TIMEOUT;
      }
    }
  }

  uint32_t bdcr_temp = RCC->BDCR;

  if (RCC_LSI_DIV1 != (bdcr_temp & RCC_BDCR_LSIPREDIV)) {
    if (((bdcr_temp & RCC_BDCR_LSIRDY) == RCC_BDCR_LSIRDY) &&
        ((bdcr_temp & RCC_BDCR_LSION) != RCC_BDCR_LSION)) {
      /* If LSIRDY is set while LSION is not enabled, LSIPREDIV can't be updated
       */
      /* The LSIPREDIV cannot be changed if the LSI is used by the IWDG or by
       * the RTC */
      /* Restore clock configuration if changed */
      if (pwrclkchanged == SET) {
        __HAL_RCC_PWR_CLK_DISABLE();
      }
      return HAL_ERROR;
    }

    /* Turn off LSI before changing RCC_BDCR_LSIPREDIV */
    if ((bdcr_temp & RCC_BDCR_LSION) == RCC_BDCR_LSION) {
      __HAL_RCC_LSI_DISABLE();

      tickstart = HAL_GetTick();

      /* Wait till LSI is disabled */
      while (READ_BIT(RCC->BDCR, RCC_BDCR_LSIRDY) != 0U)
        ;
    }

    /* Set LSI division factor */
    MODIFY_REG(RCC->BDCR, RCC_BDCR_LSIPREDIV, 0);
  }

  /* Enable the Internal Low Speed oscillator (LSI) */
  __HAL_RCC_LSI_ENABLE();

  /* Wait till LSI is ready */
  while (READ_BIT(RCC->BDCR, RCC_BDCR_LSIRDY) == 0U)
    ;

  /* Check for RTC Parameters used to output RTCCLK */
  assert_param(IS_RCC_RTCCLKSOURCE(pPeriphClkInit->RTCClockSelection));
  /* Enable Power Clock */
  if (__HAL_RCC_PWR_IS_CLK_DISABLED()) {
    __HAL_RCC_PWR_CLK_ENABLE();
    pwrclkchanged = SET;
  }
  /* Enable write access to Backup domain */
  SET_BIT(PWR->DBPR, PWR_DBPR_DBP);

  /* Wait for Backup domain Write protection disable */
  tickstart = HAL_GetTick();

  while (HAL_IS_BIT_CLR(PWR->DBPR, PWR_DBPR_DBP)) {
    if ((HAL_GetTick() - tickstart) > RCC_DBP_TIMEOUT_VALUE) {
      return HAL_TIMEOUT;
    }
  }
  /* Reset the Backup domain only if the RTC Clock source selection is modified
   * from default */
  bdcr_temp = READ_BIT(RCC->BDCR, RCC_BDCR_RTCSEL);

  if ((bdcr_temp != RCC_RTCCLKSOURCE_NO_CLK) &&
      (bdcr_temp != RCC_RTCCLKSOURCE_LSI)) {
    /* Store the content of BDCR register before the reset of Backup Domain */
    bdcr_temp = READ_BIT(RCC->BDCR, ~(RCC_BDCR_RTCSEL));
    /* RTC Clock selection can be changed only if the Backup Domain is reset */
    __HAL_RCC_BACKUPRESET_FORCE();
    __HAL_RCC_BACKUPRESET_RELEASE();
    /* Restore the Content of BDCR register */
    RCC->BDCR = bdcr_temp;
  }

  /* Wait for LSE reactivation if LSE was enable prior to Backup Domain reset */
  if (HAL_IS_BIT_SET(bdcr_temp, RCC_BDCR_LSEON)) {
    /* Get Start Tick*/
    tickstart = HAL_GetTick();

    /* Wait till LSE is ready */
    while (READ_BIT(RCC->BDCR, RCC_BDCR_LSERDY) == 0U) {
      if ((HAL_GetTick() - tickstart) > RCC_LSE_TIMEOUT_VALUE) {
        return HAL_TIMEOUT;
      }
    }
  }

  /* Apply new RTC clock source selection */
  __HAL_RCC_RTC_CONFIG(RCC_PERIPHCLK_RTC);

  /* Restore clock configuration if changed */
  if (pwrclkchanged == SET) {
    __HAL_RCC_PWR_CLK_DISABLE();
  }
  return HAL_OK;
}

void tamper_init(void) {
  // Enable LSI clock
  lsi_init();

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
  PWR->BDCR1 |= PWR_BDCR1_MONEN;
  // HAL_PWR_DisableBkUpAccess();

  // Enable all internal tampers (4th and 10th are intentionally skipped)
  // We select all of them despite some of them are never triggered
  TAMP->CR1 =
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
  NVIC_SetPriority(TAMP_IRQn, IRQ_PRI_HIGHEST);
  NVIC_EnableIRQ(TAMP_IRQn);
}

// Interrupt handle for all tamper events
// It displays an error message
void TAMP_IRQHandler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);

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
