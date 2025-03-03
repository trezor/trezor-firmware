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

#include <sec/rng.h>
#include <sys/bootargs.h>
#include <sys/linker_utils.h>
#include <sys/stack_utils.h>
#include <sys/system.h>

#ifdef KERNEL_MODE

const uint8_t AHBPrescTable[16] = {0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U,
                                   1U, 2U, 3U, 4U, 6U, 7U, 8U, 9U};
const uint8_t APBPrescTable[8] = {0U, 0U, 0U, 0U, 1U, 2U, 3U, 4U};
const uint32_t MSIRangeTable[16] = {48000000U, 24000000U, 16000000U, 12000000U,
                                    4000000U,  2000000U,  1330000U,  1000000U,
                                    3072000U,  1536000U,  1024000U,  768000U,
                                    400000U,   200000U,   133000U,   100000U};

// PLLCLK = ((HSE / PLLM) * PLLN) / PLLR
#ifdef USE_HSE
#if HSE_VALUE == 32000000
#define PLLM_COEF 2U
#define PLLN_COEF 2U
#elif HSE_VALUE == 16000000
#define PLLM_COEF 1U
#define PLLN_COEF 2U
#elif HSE_VALUE == 8000000
#define PLLM_COEF 1U
#define PLLN_COEF 4U
#elif defined HSE_VALUE
#error Unsupported HSE frequency
#endif
#else
// no HSE available, use 16MHz HSI
#define HSI_ONLY
#define PLLM_COEF 1U
#define PLLN_COEF 2U
#endif

#define DEFAULT_FREQ 160U
#define DEFAULT_PLLM PLLM_COEF
#define DEFAULT_PLLN (5 * PLLN_COEF)  // mult by x
#define DEFAULT_PLLR 1U               // division by 1
#define DEFAULT_PLLQ 1U               // division by 1
#define DEFAULT_PLLP 5U               // division by 5

uint32_t SystemCoreClock = DEFAULT_FREQ * 1000000U;

#pragma GCC optimize( \
    "no-stack-protector")  // applies to all functions in this file

// This function replaces calls to universal, but flash-wasting
//  function HAL_RCC_OscConfig.
//
//  This is the configuration before the optimization:
//   osc_init_def.OscillatorType = RCC_OSCILLATORTYPE_LSI;
//  osc_init_def.LSIState = RCC_LSI_ON;
//   HAL_RCC_OscConfig(&osc_init_def);
void lsi_init(void) {
  // Update LSI configuration in Backup Domain control register
  // Requires to enable write access to Backup Domain of necessary

  if (HAL_IS_BIT_CLR(PWR->DBPR, PWR_DBPR_DBP)) {
    // Enable write access to Backup domain
    SET_BIT(PWR->DBPR, PWR_DBPR_DBP);

    // Wait for Backup domain Write protection disable
    while (HAL_IS_BIT_CLR(PWR->DBPR, PWR_DBPR_DBP))
      ;
  }

  uint32_t bdcr_temp = RCC->BDCR;

  if (RCC_LSI_DIV1 != (bdcr_temp & RCC_BDCR_LSIPREDIV)) {
    if (((bdcr_temp & RCC_BDCR_LSIRDY) == RCC_BDCR_LSIRDY) &&
        ((bdcr_temp & RCC_BDCR_LSION) != RCC_BDCR_LSION)) {
      // If LSIRDY is set while LSION is not enabled, LSIPREDIV can't be updated
      // The LSIPREDIV cannot be changed if the LSI is used by the IWDG or by
      // the RTC
      return;
    }

    // Turn off LSI before changing RCC_BDCR_LSIPREDIV
    if ((bdcr_temp & RCC_BDCR_LSION) == RCC_BDCR_LSION) {
      __HAL_RCC_LSI_DISABLE();

      // Wait till LSI is disabled
      while (READ_BIT(RCC->BDCR, RCC_BDCR_LSIRDY) != 0U)
        ;
    }

    // Set LSI division factor
    MODIFY_REG(RCC->BDCR, RCC_BDCR_LSIPREDIV, 0);
  }

  // Enable the Internal Low Speed oscillator (LSI)
  __HAL_RCC_LSI_ENABLE();

  // Wait till LSI is ready
  while (READ_BIT(RCC->BDCR, RCC_BDCR_LSIRDY) == 0U)
    ;
}

// This function replaces calls to universal, but flash-wasting
// function HAL_RCC_OscConfig.
//
// This is the configuration before the optimization:
//  osc_init_def.OscillatorType = RCC_OSCILLATORTYPE_LSE;
//  osc_init_def.LSEState = RCC_LSE_ON;
//  HAL_RCC_OscConfig(&osc_init_def);
void lse_init(void) {
  // Update LSE configuration in Backup Domain control register
  // Requires to enable write access to Backup Domain of necessary */

  if (HAL_IS_BIT_CLR(PWR->DBPR, PWR_DBPR_DBP)) {
    // Enable write access to Backup domain
    SET_BIT(PWR->DBPR, PWR_DBPR_DBP);

    while (HAL_IS_BIT_CLR(PWR->DBPR, PWR_DBPR_DBP))
      ;
  }

  // LSE oscillator enable
  SET_BIT(RCC->BDCR, RCC_BDCR_LSEON);

  // Wait till LSE is ready
  while (READ_BIT(RCC->BDCR, RCC_BDCR_LSERDY) == 0U)
    ;

  // Make sure LSESYSEN/LSESYSRDY are reset
  CLEAR_BIT(RCC->BDCR, RCC_BDCR_LSESYSEN);

  // Wait till LSESYSRDY is cleared
  while (READ_BIT(RCC->BDCR, RCC_BDCR_LSESYSRDY) != 0U)
    ;
}

void SystemInit(void) {
  // set flash wait states for an increasing HCLK frequency

  FLASH->ACR = FLASH_ACR_LATENCY_5WS;
  // wait until the new wait state config takes effect -- per section 3.5.1
  // guidance
  while ((FLASH->ACR & FLASH_ACR_LATENCY) != FLASH_ACR_LATENCY_5WS)
    ;

  // Reset the RCC clock configuration to the default reset state
  // Set MSION bit
  RCC->CR = RCC_CR_MSISON;

  // Reset CFGR register
  RCC->CFGR1 = 0U;
  RCC->CFGR2 = 0U;
  RCC->CFGR3 = 0U;

  // Reset HSEON, CSSON , HSION, PLLxON bits
  RCC->CR &= ~(RCC_CR_HSEON | RCC_CR_CSSON | RCC_CR_PLL1ON | RCC_CR_PLL2ON |
               RCC_CR_PLL3ON | RCC_CR_HSI48ON);

  // Reset PLLCFGR register
  RCC->PLL1CFGR = 0U;

  // Reset HSEBYP bit
  RCC->CR &= ~(RCC_CR_HSEBYP);

  // Disable all interrupts
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

  // Initializes the CPU, AHB and APB buses clocks
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

  // Disable the internal Pull-Up in Dead Battery pins of UCPD peripheral
  HAL_PWREx_DisableUCPDDeadBattery();

#ifdef USE_SMPS
  // Switch to SMPS regulator instead of LDO
  SET_BIT(PWR->CR3, PWR_CR3_REGSEL);
  // Wait until system switch on new regulator
  while (HAL_IS_BIT_CLR(PWR->SVMSR, PWR_SVMSR_REGS))
    ;
#endif

  // enable power supply for GPIOG 2 to 15
  PWR->SVMCR |= PWR_SVMCR_IO2SV;

#ifdef USE_LSE
  lse_init();
#else
  lsi_init();
#endif

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

  // set CP10 and CP11 to enable full access to the fpu coprocessor;
  SCB->CPACR |=
      ((3UL << 20U) | (3UL << 22U)); /* set CP10 and CP11 Full Access */

#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
  SCB_NS->CPACR |=
      ((3UL << 20U) | (3UL << 22U)); /* set CP10 and CP11 Full Access */
#endif

  // enable instruction cache in default 2-way mode
  ICACHE->CR = ICACHE_CR_EN;

  // Configure Flash prefetch
#if (PREFETCH_ENABLE != 0U)
  __HAL_FLASH_PREFETCH_BUFFER_ENABLE();
#endif

  // Set Interrupt Group Priority
  HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);

  // Update the SystemCoreClock global variable
  /// SystemCoreClock = HAL_RCC_GetSysClockFreq() >> AHBPrescTable[(RCC->CFGR2 &
  /// RCC_CFGR2_HPRE) >> RCC_CFGR2_HPRE_Pos];

  // Enable GPIO clocks
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
}

__attribute((no_stack_protector)) void reset_handler(void) {
  // Set stack pointer limit for checking stack overflow
  __set_MSPLIM((uintptr_t)&_stack_section_start + 128);

  // Now .bss, .data are not initialized yet - we need to be
  // careful with global variables. They are not initialized,
  // contain random values and will be rewritten in the succesive
  // code

  // Initialize system clocks
  SystemInit();

  // Clear unused part of stack
  clear_unused_stack();

  // Initialize random number generator
  rng_init();

  // Clear all memory except stack.
  // Keep also bootargs in bootloader and boardloader.
  memregion_t region = MEMREGION_ALL_ACCESSIBLE_RAM;

  MEMREGION_DEL_SECTION(&region, _stack_section);
#if defined BOARDLOADER || defined BOOTLOADER
  MEMREGION_DEL_SECTION(&region, _bootargs_ram);
#endif

#ifdef BOARDLOADER
  memregion_fill(&region, rng_get());
#endif
  memregion_fill(&region, 0);

  // Initialize .bss, .data, ...
  init_linker_sections();

  // Initialize stack protector guard value
  extern uint32_t __stack_chk_guard;
  __stack_chk_guard = rng_get();

  // Now everything is perfectly initialized and we can do anything
  // in C code

#ifdef BOOTLOADER
  bootargs_init(0);
#endif

  // Enable interrupts and fault handlers
  __enable_fault_irq();

  // Run application
  extern int main(void);
  int main_result = main();

  system_exit(main_result);
}

#endif  // #ifdef KERNEL_MODE
