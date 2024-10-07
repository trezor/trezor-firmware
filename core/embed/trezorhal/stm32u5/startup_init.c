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

#include TREZOR_BOARD
#include STM32_HAL_H

#include "rng.h"

#ifdef KERNEL_MODE

const uint8_t AHBPrescTable[16] = {0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U,
                                   1U, 2U, 3U, 4U, 6U, 7U, 8U, 9U};
const uint8_t APBPrescTable[8] = {0U, 0U, 0U, 0U, 1U, 2U, 3U, 4U};
const uint32_t MSIRangeTable[16] = {48000000U, 24000000U, 16000000U, 12000000U,
                                    4000000U,  2000000U,  1330000U,  1000000U,
                                    3072000U,  1536000U,  1024000U,  768000U,
                                    400000U,   200000U,   133000U,   100000U};
typedef struct {
  uint32_t freq;
  uint32_t pllq;
  uint32_t pllp;
  uint32_t pllm;
  uint32_t plln;
} clock_conf_t;

#if defined STM32U5
#define DEFAULT_FREQ 160U
#define DEFAULT_PLLM 1
#define DEFAULT_PLLN (10 * PLLN_COEF)  // mult by 10
#define DEFAULT_PLLR 1U                // division by 1
#define DEFAULT_PLLQ 1U                // division by 1
#define DEFAULT_PLLP 5U                // division by 5
#else
#error Unsupported MCU
#endif

uint32_t SystemCoreClock = DEFAULT_FREQ * 1000000U;

// PLLCLK = ((HSE / PLLM) * PLLN) / PLLR
#ifdef HSE_16MHZ
#define PLLN_COEF 1U
#elif defined HSE_8MHZ
#define PLLN_COEF 2U
#else
// no HSE available, use 16MHz HSI
#define HSI_ONLY
#define PLLN_COEF 1U
#endif

// assuming HSE 16 MHz
clock_conf_t clock_conf[1] = {
    {
        // clk = ((16MHz / 1) * 10) / 1 = 160 MHz
        .freq = 160,
        .pllp = 1,
        .pllq = 1,
        .pllm = 1,
        .plln = 10 * PLLN_COEF,
    },
};

#pragma GCC optimize( \
    "no-stack-protector")  // applies to all functions in this file

void SystemInit(void) {
  // set flash wait states for an increasing HCLK frequency

  FLASH->ACR = FLASH_ACR_LATENCY_5WS;
  // wait until the new wait state config takes effect -- per section 3.5.1
  // guidance
  while ((FLASH->ACR & FLASH_ACR_LATENCY) != FLASH_ACR_LATENCY_5WS)
    ;

  /* Reset the RCC clock configuration to the default reset state ------------*/
  /* Set MSION bit */
  RCC->CR = RCC_CR_MSISON;

  /* Reset CFGR register */
  RCC->CFGR1 = 0U;
  RCC->CFGR2 = 0U;
  RCC->CFGR3 = 0U;

  /* Reset HSEON, CSSON , HSION, PLLxON bits */
  RCC->CR &= ~(RCC_CR_HSEON | RCC_CR_CSSON | RCC_CR_PLL1ON | RCC_CR_PLL2ON |
               RCC_CR_PLL3ON | RCC_CR_HSI48ON);

  /* Reset PLLCFGR register */
  RCC->PLL1CFGR = 0U;

  /* Reset HSEBYP bit */
  RCC->CR &= ~(RCC_CR_HSEBYP);

  /* Disable all interrupts */
  RCC->CIER = 0U;

  __HAL_RCC_PWR_CLK_ENABLE();

  MODIFY_REG(PWR->VOSR, (PWR_VOSR_VOS | PWR_VOSR_BOOSTEN),
             PWR_REGULATOR_VOLTAGE_SCALE1);
  while (HAL_IS_BIT_CLR(PWR->VOSR, PWR_VOSR_VOSRDY))
    ;
  while (HAL_IS_BIT_CLR(PWR->SVMSR, PWR_SVMSR_ACTVOSRDY))
    ;

#ifndef HSI_ONLY
  __HAL_RCC_HSE_CONFIG(RCC_HSE_ON);
  while (READ_BIT(RCC->CR, RCC_CR_HSERDY) == 0U)
    ;
  __HAL_RCC_PLL_CONFIG(RCC_PLLSOURCE_HSE, RCC_PLLMBOOST_DIV1, DEFAULT_PLLM,
                       DEFAULT_PLLN, DEFAULT_PLLP, DEFAULT_PLLQ, DEFAULT_PLLR);
#else
  RCC->CR |= RCC_CR_HSION;
  // wait until the HSI is on
  while ((RCC->CR & RCC_CR_HSION) != RCC_CR_HSION)
    ;

  __HAL_RCC_PLL_CONFIG(RCC_PLLSOURCE_HSI, RCC_PLLMBOOST_DIV1, DEFAULT_PLLM,
                       DEFAULT_PLLN, DEFAULT_PLLP, DEFAULT_PLLQ, DEFAULT_PLLR);
#endif

  __HAL_RCC_PLL_FRACN_DISABLE();

  __HAL_RCC_PLL_VCIRANGE(RCC_PLLVCIRANGE_1);

  __HAL_RCC_PLLCLKOUT_ENABLE(RCC_PLL1_DIVR);

  __HAL_RCC_PLL_ENABLE();
  while (READ_BIT(RCC->CR, RCC_CR_PLL1RDY) == 0U)
    ;

  __HAL_RCC_HSI48_ENABLE();
  while (READ_BIT(RCC->CR, RCC_CR_HSI48RDY) == 0U)
    ;

  /** Initializes the CPU, AHB and APB buses clocks
   */
  FLASH->ACR = FLASH_ACR_LATENCY_4WS;
  // wait until the new wait state config takes effect -- per section 3.5.1
  // guidance
  while ((FLASH->ACR & FLASH_ACR_LATENCY) != FLASH_ACR_LATENCY_4WS)
    ;
  MODIFY_REG(RCC->CFGR3, RCC_CFGR3_PPRE3, RCC_HCLK_DIV1);
  MODIFY_REG(RCC->CFGR2, RCC_CFGR2_PPRE2, ((RCC_HCLK_DIV1) << 4));
  MODIFY_REG(RCC->CFGR2, RCC_CFGR2_PPRE1, RCC_HCLK_DIV1);
  MODIFY_REG(RCC->CFGR2, RCC_CFGR2_HPRE, RCC_SYSCLK_DIV1);

  MODIFY_REG(RCC->CFGR1, RCC_CFGR1_SW, RCC_SYSCLKSOURCE_PLLCLK);

  /*
   * Disable the internal Pull-Up in Dead Battery pins of UCPD peripheral
   */
  HAL_PWREx_DisableUCPDDeadBattery();

#ifdef USE_SMPS
  /*
   * Switch to SMPS regulator instead of LDO
   */
  SET_BIT(PWR->CR3, PWR_CR3_REGSEL);
  /* Wait until system switch on new regulator */
  while (HAL_IS_BIT_CLR(PWR->SVMSR, PWR_SVMSR_REGS))
    ;
#endif

  // enable power supply for GPIOG 2 to 15
  PWR->SVMCR |= PWR_SVMCR_IO2SV;

  __HAL_RCC_PWR_CLK_DISABLE();

  // this will be overriden by static initialization
  SystemCoreClock = DEFAULT_FREQ * 1000000U;

#ifndef HSI_ONLY
  // enable clock security system
  RCC->CR |= RCC_CR_CSSON;

  // turn off the HSI as it is now unused (it will be turned on again
  // automatically if a clock security failure occurs)
  RCC->CR &= ~RCC_CR_HSION;
  // wait until the HSI is off
  while ((RCC->CR & RCC_CR_HSION) == RCC_CR_HSION)
    ;
#endif

  // TODO turn off MSI?

  // init the TRNG peripheral
  rng_init();

  // set CP10 and CP11 to enable full access to the fpu coprocessor;
  SCB->CPACR |=
      ((3UL << 20U) | (3UL << 22U)); /* set CP10 and CP11 Full Access */

#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
  SCB_NS->CPACR |=
      ((3UL << 20U) | (3UL << 22U)); /* set CP10 and CP11 Full Access */
#endif

  // enable instruction cache in default 2-way mode
  ICACHE->CR = ICACHE_CR_EN;

  /* Configure Flash prefetch */
#if (PREFETCH_ENABLE != 0U)
  __HAL_FLASH_PREFETCH_BUFFER_ENABLE();
#endif /* PREFETCH_ENABLE */

  /* Set Interrupt Group Priority */
  HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);

  /* Update the SystemCoreClock global variable */
  /// SystemCoreClock = HAL_RCC_GetSysClockFreq() >> AHBPrescTable[(RCC->CFGR2 &
  /// RCC_CFGR2_HPRE) >> RCC_CFGR2_HPRE_Pos];

  // Enable GPIO clocks
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
}

#endif  // #ifdef KERNEL_MODE
