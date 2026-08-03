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

// The STM32H5 boots on HSI. HSI is 64 MHz and the reset value of HSIDIV is /2,
// so the sysclk is 32 MHz right after reset. This is overwritten by the full
// clock configuration once implemented (see SystemInit TODO below).
uint32_t SystemCoreClock = 32000000U;

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
  // ==========================================================================
  // PRELIMINARY STM32H5 bring-up clock configuration.
  //
  // This deliberately leaves the CPU on the reset-default HSI clock (no PLL, no
  // HSE) so the boot chain comes up on a known-good clock for initial SWD
  // bring-up. The production clock tree - HSE from the STM32H5F5J-DK crystal ->
  // PLL -> 250 MHz, PWR voltage scaling (VOS0), and the matching flash wait
  // states - must be configured against RM0517 and the DK schematic / CubeMX
  // project before relying on any timing.
  //
  // TODO(H5): implement the full HSE/PLL/PWR clock configuration.
  // ==========================================================================

  // Set CP10 and CP11 to enable full access to the FPU coprocessor.
  SCB->CPACR |= ((3UL << 20U) | (3UL << 22U));
#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
  SCB_NS->CPACR |= ((3UL << 20U) | (3UL << 22U));
#endif

  // Enable the instruction cache (default 2-way mode).
  ICACHE->CR = ICACHE_CR_EN;

  // Set Interrupt Group Priority
  HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);

  // Enable GPIO clocks used during early bring-up.
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();

  // Running on the reset-default HSI clock (see banner above).
  SystemCoreClock = 32000000U;
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
