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

#include <sys/bootargs.h>
#include <sys/linker_utils.h>
#include <sys/rng.h>
#include <sys/stack_utils.h>
#include <sys/system.h>

#ifdef KERNEL_MODE

// The STM32H5 boots on HSI (64 MHz, HSIDIV /2 => 32 MHz sysclk at reset).
// SystemInit() switches the system clock to the PLL and updates this value.
uint32_t SystemCoreClock = 32000000U;

// AHB/APB prescaler decode tables. These are normally provided by the CMSIS
// system_stm32h5xx.c; since this port supplies its own SystemInit instead, they
// are defined here for the HAL RCC clock-frequency helpers to link against.
const uint8_t AHBPrescTable[16] = {0U, 0U, 0U, 0U, 0U, 0U, 0U, 0U,
                                   1U, 2U, 3U, 4U, 6U, 7U, 8U, 9U};
const uint8_t APBPrescTable[8] = {0U, 0U, 0U, 0U, 1U, 2U, 3U, 4U};

// PLL1 configuration for the system clock:
//   sysclk = pll1_p_ck = (HSE / PLL1_M * PLL1_N) / PLL1_P
// On the STM32H5F5J-DK the HSE is a 48 MHz crystal: /12 = 4 MHz PLL input,
// x125 = 500 MHz VCO, /2 = 250 MHz (the VOS0 maximum).
#if HSE_VALUE == 48000000
#define PLL1_M 12U
#define PLL1_N 125U
#define PLL1_P 2U
#define PLL1_Q 2U
#define PLL1_R 2U
#define PLL1_VCIRANGE RCC_PLL1_VCIRANGE_2  // 4 MHz PLL input (4..8 MHz range)
#else
#error "Unsupported HSE_VALUE for the STM32H5 PLL configuration"
#endif

#pragma GCC optimize( \
    "no-stack-protector")  // applies to all functions in this file

#ifndef SECURE_MODE

// The following functions replace ST HAL routines that are not safe to call in
// non-secure mode (e.g. the kernel running in non-secure mode), because the RCC
// peripheral is not fully accessible. Clocks are fully configured by the secure
// monitor and the kernel can rely on SystemCoreClock being set correctly.

uint32_t HAL_RCC_GetHCLKFreq(void) { return SystemCoreClock; }

uint32_t HAL_RCC_GetSysClockFreq(void) { return SystemCoreClock; }

uint32_t HAL_RCCEx_GetPeriphCLKFreq(uint64_t PeriphClk) {
  (void)PeriphClk;
  return SystemCoreClock;
}

#endif  // SECURE_MODE

void SystemInit(void) {
  // Enable full access to the FPU coprocessor (CP10/CP11).
  SCB->CPACR |= ((3UL << 20U) | (3UL << 22U));
#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
  SCB_NS->CPACR |= ((3UL << 20U) | (3UL << 22U));
#endif

  // Voltage scaling VOS0 is required for the 250 MHz maximum. Raise it before
  // increasing the flash latency and the clock frequency.
  (void)HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE0);

  // Flash wait states for 250 MHz at VOS0 (5 WS), programmed before switching
  // to the faster clock.
  MODIFY_REG(FLASH->ACR, FLASH_ACR_LATENCY, FLASH_LATENCY_5);
  while ((FLASH->ACR & FLASH_ACR_LATENCY) != FLASH_LATENCY_5) {
  }

  // HSE: 48 MHz crystal on PH0/PH1 of the STM32H5F5J-DK (crystal, not bypass).
  RCC->CR |= RCC_CR_HSEON;
  while ((RCC->CR & RCC_CR_HSERDY) == 0U) {
  }

  // PLL1 -> 250 MHz system clock from the 48 MHz HSE (see PLL1_* above).
  __HAL_RCC_PLL1_CONFIG(RCC_PLL1_SOURCE_HSE, PLL1_M, PLL1_N, PLL1_P, PLL1_Q,
                        PLL1_R);
  __HAL_RCC_PLL1_FRACN_DISABLE();
  __HAL_RCC_PLL1_VCIRANGE(PLL1_VCIRANGE);
  __HAL_RCC_PLL1_VCORANGE(RCC_PLL1_VCORANGE_WIDE);  // 500 MHz VCO (128..560 MHz)
  __HAL_RCC_PLL1_CLKOUT_ENABLE(RCC_PLL1_DIVP | RCC_PLL1_DIVQ | RCC_PLL1_DIVR);
  __HAL_RCC_PLL1_ENABLE();
  while ((RCC->CR & RCC_CR_PLL1RDY) == 0U) {
  }

  // Bus prescalers all /1: HCLK = PCLK1 = PCLK2 = PCLK3 = 250 MHz (permitted at
  // VOS0). Clearing the fields selects the division-by-1 codes.
  CLEAR_BIT(RCC->CFGR2, RCC_CFGR2_HPRE | RCC_CFGR2_PPRE1 | RCC_CFGR2_PPRE2 |
                            RCC_CFGR2_PPRE3);

  // Switch the system clock to PLL1P.
  MODIFY_REG(RCC->CFGR1, RCC_CFGR1_SW, RCC_SYSCLKSOURCE_PLLCLK);
  while (__HAL_RCC_GET_SYSCLK_SOURCE() != RCC_SYSCLKSOURCE_STATUS_PLLCLK) {
  }

  SystemCoreClock = 250000000U;

  // HSI48 for the RNG (and later USB, whose clock mux is selected in the USB
  // init path). The RNG has a clock-error detector (RNG_SR.CECS) and never
  // asserts DRDY without a kernel clock, so this must be up before rng_init().
  __HAL_RCC_HSI48_ENABLE();
  while ((RCC->CR & RCC_CR_HSI48RDY) == 0U) {
  }
  __HAL_RCC_RNG_CONFIG(RCC_RNGCLKSOURCE_HSI48);

  // Enable the SBS (System Configuration, Boot and Security) peripheral clock.
  // SBS lives on APB3; without its clock every write to an SBS register is
  // silently dropped. Several things depend on SBS writes actually landing:
  // the TrustZone peripheral security in tz_init (SBS->SECCFGR), the secret
  // hide-protection (SBS_S->HDPLCR), and the OTG_HS PHY tuning
  // (SBS_S->OTGHSPHYTUNER2).
  __HAL_RCC_SBS_CLK_ENABLE();

  // Enable the instruction cache (default 2-way mode).
  ICACHE->CR = ICACHE_CR_EN;

  // Set Interrupt Group Priority
  HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);

  // Enable GPIO clocks used during early bring-up.
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
}

#ifdef BOARDLOADER
__attribute((no_stack_protector)) void reset_handler(void) {
#else
__attribute((no_stack_protector)) void reset_handler(startup_args_t* args) {
#endif

  // Set stack pointer limit for checking stack overflow
  __set_MSPLIM((uintptr_t)&_stack_section_start + 128);

  // Now .bss, .data are not initialized yet - we need to be
  // careful with global variables. They are not initialized,
  // contain random values and will be rewritten in the succesive
  // code

#ifdef SECURE_MODE
  // Initialize system clocks
  SystemInit();
#endif

  // Clear unused part of stack
  clear_unused_stack();

#ifdef SECURE_MODE
  // Initialize random number generator
  rng_init();

  // Clear all memory except stack.
  // Keep also bootargs in bootloader and boardloader.
  memregion_t region = MEMREGION_ALL_STARTUP_RAM;

  MEMREGION_DEL_SECTION(&region, _stack_section);
#if defined BOARDLOADER || defined BOOTLOADER
  MEMREGION_DEL_SECTION(&region, _bootargs_ram);
#endif

#ifdef BOARDLOADER
  memregion_fill(&region, rng_get());
#endif
  memregion_fill(&region, 0);
#endif  // SECURE_MODE

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

#ifndef BOARDLOADER
  startup_args_import(args);
#endif

  // Enable interrupts and fault handlers
  __enable_fault_irq();

  // Run application
  extern int main(void);
  int main_result = main();

  system_exit(main_result);
}

#endif  // #ifdef KERNEL_MODE
