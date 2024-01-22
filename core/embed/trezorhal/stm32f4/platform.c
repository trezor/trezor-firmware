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

#include STM32_HAL_H

#include "platform.h"
#include "rng.h"

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

#if defined STM32F427xx || defined STM32F429xx
#ifdef TREZOR_MODEL_T
#define DEFAULT_FREQ 168U
#define DEFAULT_PLLQ 7U
#define DEFAULT_PLLP 0U  // P = 2 (two bits, 00 means PLLP = 2)
#define DEFAULT_PLLM 4U
#define DEFAULT_PLLN 168U
#else
#define DEFAULT_FREQ 180U
#define DEFAULT_PLLQ 15U
#define DEFAULT_PLLP 1U  // P = 4 (two bits, 01 means PLLP = 4)
#define DEFAULT_PLLM 4U
#define DEFAULT_PLLN 360U
#endif
#elif STM32F405xx
#define DEFAULT_FREQ 120U
#define DEFAULT_PLLQ 5U
#define DEFAULT_PLLP 0U  // P = 2 (two bits, 00 means PLLP = 2)
#define DEFAULT_PLLM 8U
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
        4,
        360,
    },
    {
        // P = 2 (two bits, 00 means PLLP = 2)
        // clk = ((8MHz / 4) * 168) / 2 = 168 MHz
        // usb = ((8MHz / 4) * 168) / 7 = 48 MHz
        168,
        7,
        0,
        4,
        168,
    },
    {
        // P = 2 (two bits, 00 means PLLP = 2)
        // clk = ((8MHz / 8) * 240) / 2 = 120 MHz
        // usb = ((8MHz / 8) * 240) / 5 = 48 MHz
        120,
        5,
        0,
        8,
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
}

#ifdef TREZOR_MODEL_T
void set_core_clock(clock_settings_t settings) {
  /* Enable HSI clock */
  RCC->CR |= RCC_CR_HSION;

  /* Wait till HSI is ready */
  while (!(RCC->CR & RCC_CR_HSIRDY))
    ;

  /* Select HSI clock as main clock */
  RCC->CFGR = (RCC->CFGR & ~(RCC_CFGR_SW)) | RCC_CFGR_SW_HSI;

  /* Disable PLL */
  RCC->CR &= ~RCC_CR_PLLON;

  /* Set PLL settings */
  clock_conf_t conf = clock_conf[settings];
  RCC->PLLCFGR =
      (RCC_PLLCFGR_RST_VALUE & ~RCC_PLLCFGR_PLLQ & ~RCC_PLLCFGR_PLLSRC &
       ~RCC_PLLCFGR_PLLP & ~RCC_PLLCFGR_PLLN & ~RCC_PLLCFGR_PLLM) |
      (conf.pllq << RCC_PLLCFGR_PLLQ_Pos) |
      RCC_PLLCFGR_PLLSRC_HSE  // PLLSRC = HSE
      | (conf.pllp << RCC_PLLCFGR_PLLP_Pos) |
      (conf.plln << RCC_PLLCFGR_PLLN_Pos) | (conf.pllm << RCC_PLLCFGR_PLLM_Pos);
  SystemCoreClock = conf.freq * 1000000U;

  /* Enable PLL */
  RCC->CR |= RCC_CR_PLLON;

  /* Wait till PLL is ready */
  while (!(RCC->CR & RCC_CR_PLLRDY))
    ;

  /* Enable PLL as main clock */
  RCC->CFGR = (RCC->CFGR & ~(RCC_CFGR_SW)) | RCC_CFGR_SW_PLL;

  HAL_InitTick(TICK_INT_PRIORITY);

  // turn off the HSI as it is now unused (it will be turned on again
  // automatically if a clock security failure occurs)
  RCC->CR &= ~RCC_CR_HSION;
  // wait until ths HSI is off
  while ((RCC->CR & RCC_CR_HSION) == RCC_CR_HSION)
    ;
}
#endif

void drop_privileges(void) {
  // jump to unprivileged mode
  // http://infocenter.arm.com/help/topic/com.arm.doc.dui0552a/CHDBIBGJ.html
  __asm__ volatile("msr control, %0" ::"r"(0x1));
  __asm__ volatile("isb");
}

// from util.s
extern void shutdown_privileged(void);

void PVD_IRQHandler(void) {
  TIM1->CCR1 = 0;  // turn off display backlight
  shutdown_privileged();
}
