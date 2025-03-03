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
#include <sys/bootutils.h>
#include <sys/linker_utils.h>
#include <sys/stack_utils.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/sysutils.h>

#include "startup_init.h"

#ifdef KERNEL_MODE

const uint8_t AHBPrescTable[16] = {0, 0, 0, 0, 0, 0, 0, 0,
                                   1, 2, 3, 4, 6, 7, 8, 9};
const uint8_t APBPrescTable[8] = {0, 0, 0, 0, 1, 2, 3, 4};

typedef struct {
  uint32_t freq;
  uint32_t pllq;
  uint32_t pllp;
  uint32_t pllm;
  uint32_t plln;
} clock_conf_t;

#ifdef USE_HSE
#if HSE_VALUE == 16000000
#define PLLM_COEF 2U
#elif HSE_VALUE == 8000000
#define PLLM_COEF 1U
#else
#error Unsupported HSE frequency
#endif
#else
#error HSE is required
#endif

#if defined STM32F427xx || defined STM32F429xx
#ifdef TREZOR_MODEL_T2T1
#define DEFAULT_FREQ 168U
#define DEFAULT_PLLQ 7U
#define DEFAULT_PLLP 0U  // P = 2 (two bits, 00 means PLLP = 2)
#define DEFAULT_PLLM (4U * PLLM_COEF)
#define DEFAULT_PLLN 168U
#else
#define DEFAULT_FREQ 180U
#define DEFAULT_PLLQ 15U
#define DEFAULT_PLLP 1U  // P = 4 (two bits, 01 means PLLP = 4)
#define DEFAULT_PLLM (4U * PLLM_COEF)
#define DEFAULT_PLLN 360U
#endif
#elif STM32F405xx
#define DEFAULT_FREQ 120U
#define DEFAULT_PLLQ 5U
#define DEFAULT_PLLP 0U  // P = 2 (two bits, 00 means PLLP = 2)
#define DEFAULT_PLLM (8U * PLLM_COEF)
#define DEFAULT_PLLN 240U
#else
#error Unsupported MCU
#endif

uint32_t SystemCoreClock = DEFAULT_FREQ * 1000000U;

// assuming HSE 8 MHz
clock_conf_t clock_conf[3] = {
    {
        // P = 4 (two bits, 01 means PLLP = 4)
        // clk = ((8MHz / 4) * 360) / 4 = 180 MHz
        // usb = ((8MHz / 4) * 360) / 15 = 48 MHz
        180,
        15,
        1,
        4 * PLLM_COEF,
        360,
    },
    {
        // P = 2 (two bits, 00 means PLLP = 2)
        // clk = ((8MHz / 4) * 168) / 2 = 168 MHz
        // usb = ((8MHz / 4) * 168) / 7 = 48 MHz
        168,
        7,
        0,
        4 * PLLM_COEF,
        168,
    },
    {
        // P = 2 (two bits, 00 means PLLP = 2)
        // clk = ((8MHz / 8) * 240) / 2 = 120 MHz
        // usb = ((8MHz / 8) * 240) / 5 = 48 MHz
        120,
        5,
        0,
        8 * PLLM_COEF,
        240,
    },
};

#pragma GCC optimize( \
    "no-stack-protector")  // applies to all functions in this file

void SystemInit(void) {
  // set flash wait states for an increasing HCLK frequency -- reference RM0090
  // section 3.5.1
  FLASH->ACR = FLASH_ACR_LATENCY_5WS;
  // wait until the new wait state config takes effect -- per section 3.5.1
  // guidance
  while ((FLASH->ACR & FLASH_ACR_LATENCY) != FLASH_ACR_LATENCY_5WS)
    ;
  // configure main PLL
  // reference RM0090 section 6.3.2
  RCC->PLLCFGR =
      (RCC_PLLCFGR_RST_VALUE & ~RCC_PLLCFGR_PLLQ & ~RCC_PLLCFGR_PLLSRC &
       ~RCC_PLLCFGR_PLLP & ~RCC_PLLCFGR_PLLN & ~RCC_PLLCFGR_PLLM) |
      (DEFAULT_PLLQ << RCC_PLLCFGR_PLLQ_Pos) |
      RCC_PLLCFGR_PLLSRC_HSE  // PLLSRC = HSE
      | (DEFAULT_PLLP << RCC_PLLCFGR_PLLP_Pos) |
      (DEFAULT_PLLN << RCC_PLLCFGR_PLLN_Pos) |
      (DEFAULT_PLLM << RCC_PLLCFGR_PLLM_Pos);
  // this will be overriden by static initialization
  SystemCoreClock = DEFAULT_FREQ * 1000000U;

  // enable spread spectrum clock for main PLL
  RCC->SSCGR = RCC_SSCGR_SSCGEN | (44 << RCC_SSCGR_INCSTEP_Pos) |
               (250 << RCC_SSCGR_MODPER_Pos);
  // enable clock security system, HSE clock, and main PLL
  RCC->CR |= RCC_CR_CSSON | RCC_CR_HSEON | RCC_CR_PLLON;
  // wait until PLL and HSE ready
  while ((RCC->CR & (RCC_CR_PLLRDY | RCC_CR_HSERDY)) !=
         (RCC_CR_PLLRDY | RCC_CR_HSERDY))
    ;
  // APB2=2, APB1=4, AHB=1, system clock = main PLL
  const uint32_t cfgr = RCC_CFGR_PPRE2_DIV2 | RCC_CFGR_PPRE1_DIV4 |
                        RCC_CFGR_HPRE_DIV1 | RCC_CFGR_SW_PLL;
  RCC->CFGR = cfgr;
  // wait until PLL is system clock and also verify that the pre-scalers were
  // set
  while (RCC->CFGR != (RCC_CFGR_SWS_PLL | cfgr))
    ;
  // turn off the HSI as it is now unused (it will be turned on again
  // automatically if a clock security failure occurs)
  RCC->CR &= ~RCC_CR_HSION;
  // wait until ths HSI is off
  while ((RCC->CR & RCC_CR_HSION) == RCC_CR_HSION)
    ;
  // init the TRNG peripheral
  rng_init();
  // set CP10 and CP11 to enable full access to the fpu coprocessor; ARMv7-M
  // Architecture Reference Manual section B3.2.20
  SCB->CPACR |= ((3U << 22) | (3U << 20));

  // Configure Flash prefetch, Instruction cache, Data cache
#if (INSTRUCTION_CACHE_ENABLE != 0U)
  __HAL_FLASH_INSTRUCTION_CACHE_ENABLE();
#endif

#if (PREFETCH_ENABLE != 0U)
  __HAL_FLASH_PREFETCH_BUFFER_ENABLE();
#endif

  // Set Interrupt Group Priority
  HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4);

  // Enable GPIO clocks
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
}

#ifdef TREZOR_MODEL_T2T1
void set_core_clock(clock_settings_t settings) {
  // Enable HSI clock
  RCC->CR |= RCC_CR_HSION;

  // Wait till HSI is ready
  while (!(RCC->CR & RCC_CR_HSIRDY))
    ;

  // Select HSI clock as main clock
  RCC->CFGR = (RCC->CFGR & ~(RCC_CFGR_SW)) | RCC_CFGR_SW_HSI;

  // Disable PLL
  RCC->CR &= ~RCC_CR_PLLON;

  // Set PLL settings
  clock_conf_t conf = clock_conf[settings];
  RCC->PLLCFGR =
      (RCC_PLLCFGR_RST_VALUE & ~RCC_PLLCFGR_PLLQ & ~RCC_PLLCFGR_PLLSRC &
       ~RCC_PLLCFGR_PLLP & ~RCC_PLLCFGR_PLLN & ~RCC_PLLCFGR_PLLM) |
      (conf.pllq << RCC_PLLCFGR_PLLQ_Pos) |
      RCC_PLLCFGR_PLLSRC_HSE  // PLLSRC = HSE
      | (conf.pllp << RCC_PLLCFGR_PLLP_Pos) |
      (conf.plln << RCC_PLLCFGR_PLLN_Pos) | (conf.pllm << RCC_PLLCFGR_PLLM_Pos);
  SystemCoreClock = conf.freq * 1000000U;

  // Enable PLL
  RCC->CR |= RCC_CR_PLLON;

  // Wait till PLL is ready
  while (!(RCC->CR & RCC_CR_PLLRDY))
    ;

  // Enable PLL as main clock
  RCC->CFGR = (RCC->CFGR & ~(RCC_CFGR_SW)) | RCC_CFGR_SW_PLL;

  systick_update_freq();

  // turn off the HSI as it is now unused (it will be turned on again
  // automatically if a clock security failure occurs)
  RCC->CR &= ~RCC_CR_HSION;
  // wait until ths HSI is off
  while ((RCC->CR & RCC_CR_HSION) == RCC_CR_HSION)
    ;
}
#endif

__attribute((no_stack_protector)) void reset_handler(void) {
#ifdef BOOTLOADER
  uint32_t r11_value;
  // Copy the value of R11 to the local variable r11_value
  __asm__ volatile("MOV %0, R11" : "=r"(r11_value));
#endif

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
#ifdef BOOTLOADER
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

  clear_otg_hs_memory();

#ifdef BOOTLOADER
  bootargs_init(r11_value);
#endif

  // Enable interrupts and fault handlers
  __enable_fault_irq();

  // Run application
  extern int main(void);
  int main_result = main();

  system_exit(main_result);
}

#endif  // KERNEL_MODE
